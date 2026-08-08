"""Integration test: Ballroom Comp Express results parsing all the way
through to a rendered report.

Uses a full real Ballroom Comp Express competition (Solar Flare DanceSport
Challenge) run through parse_competition() ->
UpdateEngine.process_competition() -> build_report()/render_report(),
proving parsing and the calculation engine - built and tested
independently - actually fit together.
"""

import unittest
from datetime import date
from pathlib import Path

import numpy as np
import requests

from points_updating.lib.parsing.ballroom_comp_express import parse_competition
from points_updating.lib.parsing.http_client import ThrottledClient
from points_updating.lib.report import build_report, render_report
from points_updating.lib.rules import award_table, cascade
from points_updating.lib.update_engine import UpdateEngine
from utils.lib.api.client import DancerRecord

_FIXTURES = Path(__file__).parent / "parsing" / "fixtures" / "ballroom_comp_express"
_RESULTS_URL = "https://ballroomcompexpress.com/results.php"


def _load_fixture(name: str) -> str:
    with open(_FIXTURES / name, encoding="utf-8") as f:
        return f.read()


class _FakeSession:
    """Maps a (url, sorted params) key to a canned HTML response body."""

    def __init__(self, responses: dict):
        self._responses = responses

    def request(self, method, url, params=None, **kwargs):
        key = (url, tuple(sorted((params or {}).items())))
        if key not in self._responses:
            raise AssertionError(f"Unexpected request: {key}")
        response = requests.Response()
        response.status_code = 200
        response._content = self._responses[key].encode("utf-8")
        response.encoding = "utf-8"
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
    def test_ballroom_comp_express_competition_flows_through_to_rendered_report(self):
        client = ThrottledClient(
            min_delay_seconds=0,
            session=_FakeSession(
                {
                    (_RESULTS_URL, (("cid", 178),)): _load_fixture("event_list.html"),
                    (_RESULTS_URL, (("cid", 178), ("eid", 852))): _load_fixture(
                        "event_newcomer_single_dance.html"
                    ),
                    (_RESULTS_URL, (("cid", 178), ("eid", 100))): _load_fixture(
                        "event_closed_gold.html"
                    ),
                    (_RESULTS_URL, (("cid", 178), ("eid", 102))): _load_fixture(
                        "event_open_gold.html"
                    ),
                    (_RESULTS_URL, (("cid", 178), ("eid", 1055))): _load_fixture(
                        "event_n_class_pre_bronze.html"
                    ),
                    (_RESULTS_URL, (("cid", 178), ("eid", 1036))): _load_fixture(
                        "event_rookie_vet.html"
                    ),
                    (_RESULTS_URL, (("cid", 178), ("eid", 105))): _load_fixture(
                        "event_b_class.html"
                    ),
                    (_RESULTS_URL, (("cid", 178), ("eid", 289))): _load_fixture(
                        "event_a_class_multi_dance.html"
                    ),
                    (_RESULTS_URL, (("cid", 178), ("eid", 748))): _load_fixture(
                        "event_no_results.html"
                    ),
                }
            ),
        )
        comp_date = date(2025, 10, 25)

        results = parse_competition(178, "Solar Flare DanceSport Challenge", comp_date, client)
        engine = UpdateEngine(lookup=_new_dancer_lookup)
        awards = engine.process_competition(results)
        starting_totals = engine.starting_totals()
        final_totals = {name: dancer.points for name, dancer in engine.final_totals().items()}
        report = build_report(awards, starting_totals, final_totals)
        text = render_report(report)

        # The Newcomer single-dance event's real winner shows up with a
        # real award for the correct dance.
        self.assertIn("Urian Leyva", text)
        self.assertIn("Solar Flare DanceSport Challenge", text)

        # Rookie/Vet and N Class/Pre-Bronze events parse successfully (both
        # are Couple-type events) but score no points - skipped by the
        # parser itself, never reaching the ledger at all.
        self.assertEqual(len(results), 28)

        # Cross-check one concrete award against the calculation engine's
        # own already-tested award-table/cascade logic, proving a real
        # parsed CompetitionResult feeds the calculator correctly - not
        # re-deriving the point table itself, which is already covered
        # elsewhere.
        urian_award = next(
            a
            for a in awards
            if a.result.lead.full_name == "Urian Leyva" and a.result.dance.dance == "Waltz"
        )
        self.assertEqual(urian_award.result.place, 1)
        expected_delta = cascade.build_cascade_delta(
            urian_award.result.dance, award_table.compute_award(urian_award.result.num_rounds, 1)
        )
        self.assertTrue(np.array_equal(urian_award.delta.syllabus, expected_delta.syllabus))
        self.assertTrue(np.array_equal(urian_award.delta.open, expected_delta.open))


if __name__ == "__main__":
    unittest.main()
