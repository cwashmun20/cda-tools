"""Integration test: CompOrganizer results parsing all the way through to
a rendered report.

Uses a full real CompOrganizer competition (Cal Poly Mustang Ball) run
through parse_competition() -> UpdateEngine.process_competition() ->
build_report()/render_report(), proving parsing and the calculation
engine - built and tested independently - actually fit together.
"""

import json
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import requests

from points_updating.lib.parsing.comporganizer import parse_competition
from points_updating.lib.parsing.http_client import ThrottledClient
from points_updating.lib.report import build_report, render_report
from points_updating.lib.rules import award_table, cascade
from points_updating.lib.update_engine import UpdateEngine
from utils.lib.api.client import DancerRecord

_FIXTURES = Path(__file__).parent / "parsing" / "fixtures" / "comporganizer"
_RESULTS_URL = "https://ndcapremier.com/feed/results/"


def _load_fixture(name: str) -> dict:
    with open(_FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


class _FakeSession:
    """Maps a (url, sorted params) key to a canned JSON response."""

    def __init__(self, responses: dict):
        self._responses = responses

    def request(self, method, url, params=None, **kwargs):
        key = (url, tuple(sorted((params or {}).items())))
        if key not in self._responses:
            raise AssertionError(f"Unexpected request: {key}")
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(self._responses[key]).encode("utf-8")
        return response


def _new_dancer_lookup(first: str, last: str) -> DancerRecord:
    """Every dancer starts fresh at zero points - keeps expected point
    totals easy to reason about without a real database."""
    return DancerRecord(
        cda_id=None,
        first=first,
        last=last,
        first_comp_date=None,
        created_date="2026-01-01",
        syllabus_pts=np.zeros((4, 19), dtype=int),
        open_pts=np.zeros((3, 4), dtype=int),
    )


class TestParsingToEngineIntegration(unittest.TestCase):
    def test_comporganizer_competition_flows_through_to_rendered_report(self):
        client = ThrottledClient(
            min_delay_seconds=0,
            session=_FakeSession(
                {
                    (
                        "https://comporganizer.com/feed/callback-comps/",
                        (("cbid", "688970749df5c"),),
                    ): _load_fixture("callback_comps.json"),
                    (_RESULTS_URL, (("cyi", 9629), ("list", "events"))): _load_fixture(
                        "event_list.json"
                    ),
                    (_RESULTS_URL, (("cyi", 9629), ("event", 38))): _load_fixture(
                        "event_single_dance.json"
                    ),
                    (_RESULTS_URL, (("cyi", 9629), ("event", 93))): _load_fixture(
                        "event_multi_dance.json"
                    ),
                    (_RESULTS_URL, (("cyi", 9629), ("event", 3))): _load_fixture(
                        "event_newcomer.json"
                    ),
                    (_RESULTS_URL, (("cyi", 9629), ("event", 120))): _load_fixture(
                        "event_rookie_follow.json"
                    ),
                }
            ),
        )
        comp_date = date(2026, 2, 7)

        results = parse_competition("688970749df5c", "Cal Poly Mustang Ball", comp_date, client)
        engine = UpdateEngine(lookup=_new_dancer_lookup)
        awards = engine.process_competition(results)
        starting_totals = engine.starting_totals()
        final_totals = {name: dancer.points for name, dancer in engine.final_totals().items()}
        report = build_report(awards, starting_totals, final_totals)
        text = render_report(report)

        # The Bronze single-dance event's real winner shows up with a real
        # award for the correct dance.
        self.assertIn("Eugene Xie", text)
        self.assertIn("Cal Poly Mustang Ball", text)

        # The Rookie/Vet event (event 120) parses successfully (it's a
        # Couple-type event) but is filtered out downstream by the engine,
        # not the parser - its dancers never reach the ledger at all.
        self.assertEqual(engine.final_totals().get("Alexander Tahan"), None)
        self.assertNotIn("Alexander Tahan", text)

        # Cross-check one concrete award against the calculation engine's
        # own already-tested award-table/cascade logic, proving a real
        # parsed CompetitionResult feeds the calculator correctly - not
        # re-deriving the point table itself, which is already covered
        # elsewhere.
        eugene_award = next(
            a
            for a in awards
            if a.result.lead.full_name == "Eugene Xie" and a.result.dance.dance == "Waltz"
        )
        self.assertEqual(eugene_award.result.place, 1)
        expected_delta = cascade.build_cascade_delta(
            eugene_award.result.dance, award_table.compute_award(eugene_award.result.num_rounds, 1)
        )
        self.assertTrue(np.array_equal(eugene_award.delta.syllabus, expected_delta.syllabus))
        self.assertTrue(np.array_equal(eugene_award.delta.open, expected_delta.open))


if __name__ == "__main__":
    unittest.main()
