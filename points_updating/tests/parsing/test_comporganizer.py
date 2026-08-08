"""Tests for points_updating.lib.parsing.comporganizer module."""

import json
import unittest
from datetime import date
from pathlib import Path

import requests

from points_updating.lib.parsing.comporganizer import (
    _dance_and_style,
    _extract_level,
    _lead_follow,
    _parse_event,
    fetch_competition_name,
    fetch_event_list,
    fetch_event_results,
    parse_competition,
    resolve_comp_year_id,
)
from points_updating.lib.parsing.http_client import ThrottledClient
from utils.lib.constants import Style
from utils.lib.models.dance import Dance

_FIXTURES = Path(__file__).parent / "fixtures" / "comporganizer"


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


def _make_client(responses: dict) -> ThrottledClient:
    return ThrottledClient(min_delay_seconds=0, session=_FakeSession(responses))


class TestResolveCompYearId(unittest.TestCase):
    def test_resolves_from_callback_comps_response(self):
        client = _make_client(
            {
                (
                    "https://comporganizer.com/feed/callback-comps/",
                    (("cbid", "688970749df5c"),),
                ): _load_fixture("callback_comps.json")
            }
        )

        comp_year_id = resolve_comp_year_id("688970749df5c", client)

        self.assertEqual(comp_year_id, 9629)


class TestFetchCompetitionName(unittest.TestCase):
    def test_resolves_from_callback_comps_response(self):
        client = _make_client(
            {
                (
                    "https://comporganizer.com/feed/callback-comps/",
                    (("cbid", "688970749df5c"),),
                ): _load_fixture("callback_comps.json")
            }
        )

        name = fetch_competition_name("688970749df5c", client)

        self.assertEqual(name, "Cal Poly Mustang Ball")


class TestFetchEventList(unittest.TestCase):
    def test_returns_id_name_pairs(self):
        client = _make_client(
            {
                (
                    "https://ndcapremier.com/feed/results/",
                    (("cyi", 9629), ("list", "events")),
                ): _load_fixture("event_list.json")
            }
        )

        events = fetch_event_list(9629, client)

        self.assertIn((38, "Closed Bronze Int'l Waltz"), events)
        self.assertIn((93, "Closed Gold Int'l Waltz & QS"), events)
        self.assertEqual(len(events), 4)


class TestFetchEventResults(unittest.TestCase):
    def test_returns_raw_event_json(self):
        fixture = _load_fixture("event_single_dance.json")
        client = _make_client(
            {("https://ndcapremier.com/feed/results/", (("cyi", 9629), ("event", 38))): fixture}
        )

        result = fetch_event_results(9629, 38, client)

        self.assertEqual(result, fixture)


class TestExtractLevel(unittest.TestCase):
    def test_strips_closed_prefix(self):
        self.assertEqual(_extract_level("Closed Bronze Int'l Waltz"), "Bronze")

    def test_closed_gold(self):
        self.assertEqual(_extract_level("Closed Gold Int'l Waltz"), "Gold")

    def test_open_gold_raises(self):
        with self.assertRaises(ValueError):
            _extract_level("Open Gold Int'l Waltz")

    def test_open_bronze_raises(self):
        with self.assertRaises(ValueError):
            _extract_level("Open Bronze Int'l Waltz")

    def test_no_prefix(self):
        self.assertEqual(_extract_level("Newcomer Int'l Waltz"), "Newcomer")

    def test_rv_rookie_follow_not_shadowed_by_shorter_match(self):
        self.assertEqual(_extract_level("R/V Rookie Follow Int'l Waltz"), "Rookie Follow")

    def test_unrecognized_level_raises(self):
        with self.assertRaises(ValueError):
            _extract_level("Mystery Level Int'l Waltz")


class TestDanceAndStyle(unittest.TestCase):
    def test_international_waltz_resolves_to_standard(self):
        style, bare_name = _dance_and_style("Int'l Waltz")
        self.assertEqual(style, Style.STANDARD)
        self.assertEqual(bare_name, "Waltz")

    def test_international_cha_cha_resolves_to_latin(self):
        style, bare_name = _dance_and_style("Int'l Cha Cha")
        self.assertEqual(style, Style.LATIN)
        self.assertEqual(bare_name, "Cha Cha")

    def test_american_waltz_resolves_to_smooth(self):
        style, bare_name = _dance_and_style("Am. Waltz")
        self.assertEqual(style, Style.SMOOTH)

    def test_american_cha_cha_resolves_to_rhythm(self):
        style, bare_name = _dance_and_style("Am. Cha Cha")
        self.assertEqual(style, Style.RHYTHM)

    def test_amer_prefix_resolves_to_smooth(self):
        """CompOrganizer also uses "Amer." (not just "Am.") for American
        style on some events - confirmed via a live sweep of every Mustang
        Ball event's dance names."""
        style, bare_name = _dance_and_style("Amer. Waltz")
        self.assertEqual(style, Style.SMOOTH)
        self.assertEqual(bare_name, "Waltz")

    def test_amer_prefix_resolves_to_rhythm(self):
        style, bare_name = _dance_and_style("Amer. Cha Cha")
        self.assertEqual(style, Style.RHYTHM)

    def test_amer_ec_swing_resolves_to_rhythm(self):
        style, bare_name = _dance_and_style("Amer. EC Swing")
        self.assertEqual(style, Style.RHYTHM)
        self.assertEqual(bare_name, "EC Swing")

    def test_no_prefix_resolves_to_nightclub(self):
        style, bare_name = _dance_and_style("Salsa")
        self.assertEqual(style, Style.NIGHTCLUB)
        self.assertEqual(bare_name, "Salsa")

    def test_unrecognized_name_raises(self):
        with self.assertRaises(ValueError):
            _dance_and_style("Mystery Waltz")


class TestLeadFollow(unittest.TestCase):
    def test_first_participant_is_lead_second_is_follow(self):
        lead, follow = _lead_follow(
            [{"Name": ["Kaiyu", "Ren"]}, {"Name": ["Kristina", "Andreyeva"]}]
        )
        self.assertEqual(lead.full_name, "Kaiyu Ren")
        self.assertEqual(follow.full_name, "Kristina Andreyeva")


class TestParseEvent(unittest.TestCase):
    """Tests _parse_event() directly against real, captured event JSON."""

    def test_single_dance_event(self):
        event = _load_fixture("event_single_dance.json")["Result"]["Event"]

        results = _parse_event(event, "Cal Poly Mustang Ball", date(2026, 2, 7))

        self.assertEqual(len(results), 3)
        expected_dance = Dance("Bronze", "Standard", "Waltz")
        by_place = {r.place: r for r in results}
        self.assertEqual(set(by_place), {1, 2, 3})
        self.assertEqual(by_place[1].lead.full_name, "Eugene Xie")
        self.assertEqual(by_place[1].follow.full_name, "Yue Tong Lee")
        self.assertEqual(by_place[2].lead.full_name, "Edison Lee")
        self.assertEqual(by_place[3].lead.full_name, "Fiona Treacy")
        for result in results:
            self.assertEqual(result.dance, expected_dance)
            self.assertEqual(result.num_rounds, 2)
            self.assertEqual(result.competition_name, "Cal Poly Mustang Ball")
            self.assertEqual(result.competition_date, date(2026, 2, 7))
            self.assertEqual(result.event_dances, (expected_dance,))

    def test_multi_dance_event_shares_combined_placement_across_dances(self):
        event = _load_fixture("event_multi_dance.json")["Result"]["Event"]

        results = _parse_event(event, "Cal Poly Mustang Ball", date(2026, 2, 7))

        self.assertEqual(len(results), 6)  # 2 dances x 3 competitors
        waltz = Dance("Gold", "Standard", "Waltz")
        quickstep = Dance("Gold", "Standard", "Quickstep")
        self.assertEqual(set(r.dance for r in results), {waltz, quickstep})
        for result in results:
            self.assertEqual(result.event_dances, (waltz, quickstep))
            self.assertEqual(result.num_rounds, 2)

        # Each couple's placement is the same combined result in both dances,
        # not a per-dance placement.
        by_name_and_dance = {(r.lead.full_name, r.dance): r.place for r in results}
        self.assertEqual(by_name_and_dance[("Kaiyu Ren", waltz)], 5)
        self.assertEqual(by_name_and_dance[("Kaiyu Ren", quickstep)], 5)
        self.assertEqual(by_name_and_dance[("Eli Hamre", waltz)], 3)
        self.assertEqual(by_name_and_dance[("Eli Hamre", quickstep)], 3)
        self.assertEqual(by_name_and_dance[("Anton Polishko", waltz)], 6)
        self.assertEqual(by_name_and_dance[("Anton Polishko", quickstep)], 6)

    def test_non_couple_type_raises(self):
        event = {"Type": "JandJ", "Name": "Some Event", "Rounds": []}

        with self.assertRaises(NotImplementedError):
            _parse_event(event, "Test Classic", date(2026, 2, 7))

    def test_nightclub_event_has_no_intl_or_am_prefix(self):
        event = _load_fixture("event_nightclub.json")["Result"]["Event"]

        results = _parse_event(event, "Cal Poly Mustang Ball", date(2026, 2, 7))

        self.assertEqual(len(results), 6)
        expected_dance = Dance("Beginner", "Nightclub", "Salsa")
        for result in results:
            self.assertEqual(result.dance, expected_dance)
            self.assertEqual(result.num_rounds, 3)

    def test_lone_entrant_uses_dance_result_not_null_summary(self):
        # A round with only one couple entered gets no combined Summary
        # Result at all (null) - confirmed against a real event - even
        # though the couple trivially placed 1st. Placement must come from
        # the dance's own Result field instead for a single-dance event.
        event = _load_fixture("event_lone_entrant.json")["Result"]["Event"]

        results = _parse_event(event, "Cal Poly Mustang Ball", date(2026, 2, 7))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].place, 1)
        self.assertEqual(results[0].lead.full_name, "Gregory Peregrin")
        self.assertEqual(results[0].follow.full_name, "Cadie Sparks")
        self.assertEqual(results[0].dance, Dance("Rookie Lead", "Standard", "Viennese Waltz"))

    def test_single_dance_fractional_tie_rounds_down(self):
        # A true, unresolved tie between couples 1 and 2 for 6th/7th,
        # matching CompOrganizer's own real fractional Result format.
        event = {
            "Type": "Couple",
            "Name": "Closed Bronze Int'l Waltz",
            "Rounds": [
                {
                    "Dances": [
                        {
                            "Dance_Name": "Int'l Waltz",
                            "Competitors": [
                                {
                                    "ID": 1,
                                    "Result": 6.5,
                                    "Participants": [
                                        {"Name": ["Alex", "Lee"]},
                                        {"Name": ["Jamie", "Kim"]},
                                    ],
                                },
                                {
                                    "ID": 2,
                                    "Result": 6.5,
                                    "Participants": [
                                        {"Name": ["Sam", "Park"]},
                                        {"Name": ["Robin", "Cho"]},
                                    ],
                                },
                            ],
                        }
                    ],
                    "Summary": {"Competitors": []},
                }
            ],
        }

        results = _parse_event(event, "Test Classic", date(2026, 2, 7))

        self.assertEqual({r.place for r in results}, {6})

    def test_multi_dance_fractional_tie_rounds_down(self):
        participants = [{"Name": ["Alex", "Lee"]}, {"Name": ["Jamie", "Kim"]}]
        event = {
            "Type": "Couple",
            "Name": "Closed Gold Int'l Waltz & QS",
            "Rounds": [
                {
                    "Dances": [
                        {
                            "Dance_Name": "Int'l Waltz",
                            "Competitors": [{"ID": 1, "Result": 3, "Participants": participants}],
                        },
                        {
                            "Dance_Name": "Int'l Quickstep",
                            "Competitors": [{"ID": 1, "Result": 3, "Participants": participants}],
                        },
                    ],
                    "Summary": {"Competitors": [{"ID": 1, "Result": [3.5, 3.5]}]},
                }
            ],
        }

        results = _parse_event(event, "Test Classic", date(2026, 2, 7))

        self.assertEqual(len(results), 2)
        self.assertEqual({r.place for r in results}, {3})


class TestParseCompetition(unittest.TestCase):
    """Tests parse_competition()'s fetch-list-then-fetch-each-event
    orchestration, including skipping non-Couple events, using small
    synthetic responses focused on control flow (detailed per-event
    parsing correctness is covered by TestParseEvent against real fixtures).
    """

    def test_skips_non_couple_events_without_raising(self):
        results_url = "https://ndcapremier.com/feed/results/"
        single_dance_event = _load_fixture("event_single_dance.json")
        team_match_event = {
            "Status": 1,
            "Result": {"Event": {"Type": "Team", "Name": "Team Match", "Rounds": []}},
        }
        client = _make_client(
            {
                (
                    "https://comporganizer.com/feed/callback-comps/",
                    (("cbid", "abc123"),),
                ): _load_fixture("callback_comps.json"),
                (results_url, (("cyi", 9629), ("list", "events"))): {
                    "Status": 1,
                    "Result": {
                        "Events": [
                            {"ID": 38, "Name": "Closed Bronze Int'l Waltz"},
                            {"ID": 999, "Name": "Team Match"},
                        ]
                    },
                },
                (results_url, (("cyi", 9629), ("event", 38))): single_dance_event,
                (results_url, (("cyi", 9629), ("event", 999))): team_match_event,
            }
        )

        results = parse_competition("abc123", "Cal Poly Mustang Ball", date(2026, 2, 7), client)

        self.assertEqual(len(results), 3)  # only the Couple event's 3 results


if __name__ == "__main__":
    unittest.main()
