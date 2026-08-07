"""Tests for points_updating.lib.parsing.ballroom_comp_express module.

Fixtures are real, captured data from Solar Flare DanceSport Challenge
(cid=178) - the one competition on our circuit that currently uses
Ballroom Comp Express. Solar Flare organizes events by age division
(Adult/Youth/Junior/Senior), not a "Collegiate" category, and mixes plain
CDA level words (Newcomer, Bronze, Silver, Gold) with an NDCA-style
letter-class system (N/E/D/C/B/A/S Class) - both are exercised here.
"""

import unittest
from datetime import date
from pathlib import Path

import requests

from points_updating.lib.parsing.ballroom_comp_express import (
    _extract_level,
    _extract_style_and_remainder,
    _lead_follow,
    _parse_event,
    _unescape_js_string,
    extract_embedded_json,
    fetch_competition_name,
    fetch_event_list,
    fetch_event_page,
    parse_competition,
)
from points_updating.lib.parsing.http_client import ThrottledClient
from utils.lib.constants import Style
from utils.lib.models.dance import Dance

_FIXTURES = Path(__file__).parent / "fixtures" / "ballroom_comp_express"
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


def _make_client(responses: dict) -> ThrottledClient:
    return ThrottledClient(min_delay_seconds=0, session=_FakeSession(responses))


class TestFetchEventList(unittest.TestCase):
    def test_returns_id_name_pairs(self):
        client = _make_client({(_RESULTS_URL, (("cid", 178),)): _load_fixture("event_list.html")})

        events = fetch_event_list(178, client)

        self.assertIn((852, "Amateur Adult Newcomer American Smooth Waltz"), events)
        self.assertEqual(len(events), 7)

    def test_team_match_links_are_not_returned(self):
        # Team Match events link via tmid=, not eid=, so they're naturally
        # excluded by the eid-only regex rather than needing special-casing.
        client = _make_client({(_RESULTS_URL, (("cid", 178),)): _load_fixture("event_list.html")})

        events = fetch_event_list(178, client)

        self.assertFalse(any("Team Match" in name for _, name in events))


class TestFetchCompetitionName(unittest.TestCase):
    def test_returns_name_from_index_page(self):
        client = _make_client({(_RESULTS_URL, (("cid", 178),)): _load_fixture("event_list.html")})

        name = fetch_competition_name(178, client)

        self.assertEqual(name, "Solar Flare DanceSport Challenge")


class TestFetchEventPage(unittest.TestCase):
    def test_returns_raw_html(self):
        fixture = _load_fixture("event_newcomer_single_dance.html")
        client = _make_client({(_RESULTS_URL, (("cid", 178), ("eid", 852))): fixture})

        html = fetch_event_page(178, 852, client)

        self.assertEqual(html, fixture)


class TestExtractEmbeddedJson(unittest.TestCase):
    def test_extracts_all_three_variables(self):
        event = extract_embedded_json(_load_fixture("event_newcomer_single_dance.html"))

        self.assertEqual(event["eventinfo"]["eventid"], 852)
        self.assertIn("roundorder", event["results"])
        self.assertIn("102", event["dancers"])

    def test_unescapes_escaped_forward_slash_in_displayname(self):
        event = extract_embedded_json(_load_fixture("event_open_gold.html"))

        self.assertEqual(
            event["eventinfo"]["displayname"],
            "Amateur Adult C Class (Open Gold) International Standard W/F/Q",
        )

    def test_missing_variable_raises(self):
        with self.assertRaises(ValueError):
            extract_embedded_json("<html><script>var results = JSON.parse('{}');</script></html>")


class TestUnescapeJsString(unittest.TestCase):
    def test_unescapes_quote_and_slash_and_backslash(self):
        self.assertEqual(_unescape_js_string('a\\"b\\/c\\\\d'), 'a"b/c\\d')

    def test_leaves_non_ascii_untouched(self):
        self.assertEqual(_unescape_js_string("Timothée"), "Timothée")


class TestExtractLevel(unittest.TestCase):
    def test_plain_newcomer(self):
        self.assertEqual(_extract_level("Amateur Adult Newcomer American Smooth Waltz"), "Newcomer")

    def test_closed_gold_with_parens(self):
        self.assertEqual(
            _extract_level("Amateur Adult C Class (Closed Gold) International Standard Waltz"),
            "Gold",
        )

    def test_open_gold_with_parens_maps_to_novice(self):
        self.assertEqual(
            _extract_level("Amateur Adult C Class (Open Gold) International Standard W/F/Q"),
            "Novice",
        )

    def test_bare_gold_with_no_modifier_defaults_to_closed(self):
        self.assertEqual(
            _extract_level("Amateur Adult C Class Gold International Standard Tango"), "Gold"
        )

    def test_e_class_maps_to_bronze(self):
        self.assertEqual(
            _extract_level("Amateur Adult E Class (Bronze) International Standard Waltz"), "Bronze"
        )

    def test_d_class_maps_to_silver(self):
        self.assertEqual(
            _extract_level("Amateur Adult D Class Silver International Standard Quickstep"),
            "Silver",
        )

    def test_b_class_maps_to_prechamp(self):
        self.assertEqual(
            _extract_level("Amateur Adult B Class Open International Standard W/T/F/Q"), "Prechamp"
        )

    def test_a_class_maps_to_champ(self):
        self.assertEqual(
            _extract_level("Amateur Adult A Class Open American Smooth W/T/F/V"), "Champ"
        )

    def test_s_class_maps_to_champ(self):
        self.assertEqual(
            _extract_level("Amateur Senior I S Class Open International Standard W/T/V/F/Q"),
            "Champ",
        )

    def test_n_class_pre_bronze_has_no_cda_equivalent(self):
        self.assertIsNone(
            _extract_level("Amateur Adult N Class Pre-Bronze International Standard Waltz")
        )

    def test_n_class_pre_bronze_with_parens_has_no_cda_equivalent(self):
        self.assertIsNone(
            _extract_level("Amateur Adult N Class (Pre-Bronze) International Standard Tango")
        )

    def test_pre_bronze_is_not_mistaken_for_bronze(self):
        level = _extract_level("Amateur Adult N Class Pre-Bronze International Standard Waltz")
        self.assertNotEqual(level, "Bronze")

    def test_n_class_newcomer_prefers_newcomer_over_ambiguous_n_class(self):
        self.assertEqual(
            _extract_level("Amateur Adult N Class Newcomer International Standard Waltz"),
            "Newcomer",
        )

    def test_unrecognized_level_raises(self):
        with self.assertRaises(ValueError):
            _extract_level("Amateur Alumni All Levels International Standard Waltz")


class TestExtractStyleAndRemainder(unittest.TestCase):
    def test_american_smooth_and_remainder_is_bare_dance_name(self):
        style, remainder = _extract_style_and_remainder(
            "Amateur Adult Newcomer American Smooth Waltz"
        )
        self.assertEqual(style, Style.SMOOTH)
        self.assertEqual(remainder, "Waltz")

    def test_international_standard(self):
        style, _ = _extract_style_and_remainder(
            "Amateur Adult C Class (Closed Gold) International Standard Waltz"
        )
        self.assertEqual(style, Style.STANDARD)

    def test_international_latin(self):
        style, _ = _extract_style_and_remainder("Amateur Adult Bronze International Latin Cha Cha")
        self.assertEqual(style, Style.LATIN)

    def test_american_rhythm(self):
        style, _ = _extract_style_and_remainder("Amateur Adult Bronze American Rhythm Cha Cha")
        self.assertEqual(style, Style.RHYTHM)

    def test_unrecognized_style_raises(self):
        with self.assertRaises(ValueError):
            _extract_style_and_remainder("Amateur Open Open  Hustle")


class TestLeadFollow(unittest.TestCase):
    def test_leader_and_follower_fields_map_directly(self):
        lead, follow = _lead_follow(
            {
                "leaderfname": "Alexander",
                "leaderlname": "Martin",
                "followerfname": "Heidi ",
                "followerlname": "Phelon",
            }
        )
        self.assertEqual(lead.full_name, "Alexander Martin")
        self.assertEqual(follow.full_name, "Heidi Phelon")


class TestParseEvent(unittest.TestCase):
    """Tests _parse_event() directly against real, captured Solar Flare
    event JSON.
    """

    def test_newcomer_single_dance_uses_final_round_and_rounds_down_ties(self):
        event = extract_embedded_json(_load_fixture("event_newcomer_single_dance.html"))

        results = _parse_event(event, "Solar Flare DanceSport Challenge", date(2025, 3, 1))

        self.assertEqual(len(results), 7)
        expected_dance = Dance("Newcomer", "Smooth", "Waltz")
        by_lead = {r.lead.full_name: r.place for r in results}
        # 102 and 142 are a real true tie at place 1.5 in the raw data,
        # rounded down to 1 for both.
        self.assertEqual(by_lead["Urian Leyva"], 1)
        self.assertEqual(by_lead["Nicholas Hutcheson"], 1)
        self.assertEqual(by_lead["Darius Gharavi"], 3)
        self.assertEqual(by_lead["Silas Kirby"], 6)
        self.assertEqual(by_lead["Gabriel Macias"], 7)
        for result in results:
            self.assertEqual(result.dance, expected_dance)
            self.assertEqual(result.num_rounds, 2)
            self.assertEqual(result.event_dances, (expected_dance,))

    def test_closed_gold_maps_to_gold(self):
        event = extract_embedded_json(_load_fixture("event_closed_gold.html"))

        results = _parse_event(event, "Solar Flare DanceSport Challenge", date(2025, 3, 1))

        self.assertEqual(len(results), 2)
        expected_dance = Dance("Gold", "Standard", "Waltz")
        by_place = {r.place: r for r in results}
        self.assertEqual(by_place[1].lead.full_name, "Yannik Cadin")
        self.assertEqual(by_place[2].lead.full_name, "Brian Corpus")
        for result in results:
            self.assertEqual(result.dance, expected_dance)
            self.assertEqual(result.num_rounds, 1)

    def test_open_gold_maps_to_novice_multi_dance(self):
        event = extract_embedded_json(_load_fixture("event_open_gold.html"))

        results = _parse_event(event, "Solar Flare DanceSport Challenge", date(2025, 3, 1))

        self.assertEqual(len(results), 3)  # 1 partnership x 3 dances
        waltz = Dance("Novice", "Standard", "Waltz")
        foxtrot = Dance("Novice", "Standard", "Foxtrot")
        quickstep = Dance("Novice", "Standard", "Quickstep")
        self.assertEqual(set(r.dance for r in results), {waltz, foxtrot, quickstep})
        for result in results:
            self.assertEqual(result.place, 1)
            self.assertEqual(result.lead.full_name, "Brian Corpus")
            self.assertEqual(result.event_dances, (waltz, foxtrot, quickstep))

    def test_b_class_maps_to_prechamp(self):
        event = extract_embedded_json(_load_fixture("event_b_class.html"))

        results = _parse_event(event, "Solar Flare DanceSport Challenge", date(2025, 3, 1))

        self.assertEqual(len(results), 4)  # 1 partnership x 4 dances
        self.assertTrue(all(r.dance.level == "Prechamp" for r in results))
        self.assertTrue(all(r.dance.style == Style.STANDARD for r in results))

    def test_a_class_maps_to_champ_multi_dance(self):
        event = extract_embedded_json(_load_fixture("event_a_class_multi_dance.html"))

        results = _parse_event(event, "Solar Flare DanceSport Challenge", date(2025, 3, 1))

        self.assertEqual(len(results), 12)  # 3 partnerships x 4 dances
        self.assertTrue(all(r.dance.level == "Champ" for r in results))
        self.assertTrue(all(r.dance.style == Style.SMOOTH for r in results))
        by_name_and_dance = {(r.lead.full_name, r.dance.dance): r.place for r in results}
        self.assertEqual(by_name_and_dance[("Tristan Moe", "Waltz")], 1)
        self.assertEqual(by_name_and_dance[("Alex Yang", "Waltz")], 2)
        self.assertEqual(by_name_and_dance[("Weston Beebe", "Waltz")], 3)

    def test_rookie_vet_skipped_without_raising(self):
        event = extract_embedded_json(_load_fixture("event_rookie_vet.html"))

        results = _parse_event(event, "Solar Flare DanceSport Challenge", date(2025, 3, 1))

        self.assertEqual(results, [])

    def test_n_class_pre_bronze_skipped_without_raising(self):
        event = extract_embedded_json(_load_fixture("event_n_class_pre_bronze.html"))

        results = _parse_event(event, "Solar Flare DanceSport Challenge", date(2025, 3, 1))

        self.assertEqual(results, [])

    def test_non_couple_type_raises(self):
        event = {"eventinfo": {"eventtype": 5, "displayname": "Formation Team"}}

        with self.assertRaises(NotImplementedError):
            _parse_event(event, "Test Classic", date(2025, 3, 1))


class TestParseCompetition(unittest.TestCase):
    """Tests parse_competition()'s fetch-list-then-fetch-each-event
    orchestration against the full, real Solar Flare event list, exercising
    every skip path (Rookie/Vet, N Class/Pre-Bronze, and the tmid= Team
    Match link that never even reaches fetch_event_list()'s output) plus
    every level-mapping path together.
    """

    def test_parses_every_couple_event_and_skips_ineligible_ones(self):
        client = _make_client(
            {
                (_RESULTS_URL, (("cid", 178),)): _load_fixture("event_list.html"),
                (_RESULTS_URL, (("cid", 178), ("eid", 852))): _load_fixture(
                    "event_newcomer_single_dance.html"
                ),
                (_RESULTS_URL, (("cid", 178), ("eid", 100))): _load_fixture(
                    "event_closed_gold.html"
                ),
                (_RESULTS_URL, (("cid", 178), ("eid", 102))): _load_fixture("event_open_gold.html"),
                (_RESULTS_URL, (("cid", 178), ("eid", 1055))): _load_fixture(
                    "event_n_class_pre_bronze.html"
                ),
                (_RESULTS_URL, (("cid", 178), ("eid", 1036))): _load_fixture(
                    "event_rookie_vet.html"
                ),
                (_RESULTS_URL, (("cid", 178), ("eid", 105))): _load_fixture("event_b_class.html"),
                (_RESULTS_URL, (("cid", 178), ("eid", 289))): _load_fixture(
                    "event_a_class_multi_dance.html"
                ),
            }
        )

        results = parse_competition(
            178, "Solar Flare DanceSport Challenge", date(2025, 3, 1), client
        )

        # 7 (Newcomer) + 2 (Closed Gold) + 3 (Open Gold) + 0 (N Class) +
        # 0 (Rookie/Vet) + 4 (B Class) + 12 (A Class) = 28.
        self.assertEqual(len(results), 28)


if __name__ == "__main__":
    unittest.main()
