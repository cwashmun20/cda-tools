"""Tests for points_updating.lib.parsing.o2cm module.

The primary fixture (results_page.html) is real, captured data from the
Claremont Intercollegiate Showdown 2025 (event=isc25) - O2CM's single
consolidated results page for the whole competition.
"""

import unittest
from datetime import date
from pathlib import Path

import requests

from points_updating.lib.parsing.http_client import ThrottledClient
from points_updating.lib.parsing.o2cm import (
    _build_results,
    _extract_level,
    _extract_nightclub_dance_name,
    _parse_placement_row,
    _parse_results_page,
    _resolve_style_and_dances,
    _split_name,
    fetch_competition_name,
    fetch_results_page,
    parse_competition,
)
from utils.lib.constants import Style
from utils.lib.models.dance import Dance

_FIXTURES = Path(__file__).parent / "fixtures" / "o2cm"
_EVENT_URL = "https://results.o2cm.com/event3.asp"
_RESULTS_KEY = (
    "POST",
    _EVENT_URL,
    (
        ("event", "isc25"),
        ("selAge", ""),
        ("selDiv", ""),
        ("selEnt", ""),
        ("selSkl", ""),
        ("selSty", ""),
        ("submit", "OK"),
    ),
)


def _load_fixture(name: str) -> str:
    with open(_FIXTURES / name, encoding="utf-8") as f:
        return f.read()


class _FakeSession:
    """Maps a (method, url, sorted params/data) key to a canned HTML response."""

    def __init__(self, responses: dict):
        self._responses = responses

    def request(self, method, url, params=None, data=None, **kwargs):
        key = (method, url, tuple(sorted((params or data or {}).items())))
        if key not in self._responses:
            raise AssertionError(f"Unexpected request: {key}")
        response = requests.Response()
        response.status_code = 200
        response._content = self._responses[key].encode("utf-8")
        response.encoding = "utf-8"
        return response


def _make_client(responses: dict) -> ThrottledClient:
    return ThrottledClient(min_delay_seconds=0, session=_FakeSession(responses))


class TestFetchResultsPage(unittest.TestCase):
    def test_returns_raw_html(self):
        fixture = _load_fixture("results_page.html")
        client = _make_client({_RESULTS_KEY: fixture})

        html = fetch_results_page("isc25", client)

        self.assertEqual(html, fixture)


class TestFetchCompetitionName(unittest.TestCase):
    def test_returns_name_from_results_page(self):
        client = _make_client({_RESULTS_KEY: _load_fixture("results_page.html")})

        name = fetch_competition_name("isc25", client)

        self.assertEqual(name, "Claremont Intercollegiate Showdown 2025")


class TestExtractLevel(unittest.TestCase):
    def test_bronze(self):
        self.assertEqual(_extract_level("Amateur  Bronze Am. Waltz  (W)"), "Bronze")

    def test_championship(self):
        self.assertEqual(_extract_level("Amateur  Championship Smooth  (WTFV)"), "Champ")

    def test_rookie_followers_takes_priority_over_skill_word(self):
        self.assertEqual(_extract_level("Rookie Followers  Bronze Am. Waltz  (W)"), "Rookie Follow")

    def test_unrecognized_level_raises(self):
        with self.assertRaises(ValueError):
            _extract_level("Amateur  Mystery Am. Waltz  (W)")

    def test_double_open_resolves_to_champ(self):
        # Real heat (UCSB Beach Ball): "Open" doubles as both O2CM's
        # required-but-meaningless age-category placeholder and this
        # comp's own name for their single combined open-level event.
        self.assertEqual(_extract_level("Amateur Open Open Standard (WTVFQ)"), "Champ")

    def test_single_open_placeholder_is_ignored(self):
        # Same comp's syllabus events still carry the meaningless "Open"
        # age-category placeholder exactly once - it must not shadow the
        # real level elsewhere in the name.
        self.assertEqual(_extract_level("Amateur Open Bronze Am. Waltz (W)"), "Bronze")

    def test_no_open_at_all_is_unaffected(self):
        # A normal comp with no age-category quirk (e.g. Claremont) must
        # parse exactly as before.
        self.assertEqual(_extract_level("Amateur  Bronze Am. Waltz  (W)"), "Bronze")


class TestResolveStyleAndDances(unittest.TestCase):
    def test_bare_style_word_for_multi_dance_heat(self):
        style, dances = _resolve_style_and_dances("Amateur Silver Smooth (WT)", "Silver")
        self.assertEqual(style, Style.SMOOTH)
        self.assertEqual(
            dances, [Dance("Silver", "Smooth", "Waltz"), Dance("Silver", "Smooth", "Tango")]
        )

    def test_am_prefix_resolves_via_letter_membership(self):
        style, dances = _resolve_style_and_dances("Amateur Bronze Am. Waltz (W)", "Bronze")
        self.assertEqual(style, Style.SMOOTH)
        self.assertEqual(dances, [Dance("Bronze", "Smooth", "Waltz")])

    def test_amer_prefix_resolves_via_letter_membership(self):
        # "Amer." (not just "Am.") is another real American-style marker -
        # confirmed against a real heat name; "Am." isn't a substring of
        # "Amer." (the period doesn't immediately follow "Am"), so this
        # needs its own check rather than falling out of the "Am." one.
        style, dances = _resolve_style_and_dances("Amateur Bronze Amer. Waltz (W)", "Bronze")
        self.assertEqual(style, Style.SMOOTH)
        self.assertEqual(dances, [Dance("Bronze", "Smooth", "Waltz")])

    def test_am_prefix_rhythm_dance_resolves_via_letter_membership(self):
        style, dances = _resolve_style_and_dances("Amateur Bronze Am. Cha Cha (C)", "Bronze")
        self.assertEqual(style, Style.RHYTHM)

    def test_intl_prefix_resolves_via_letter_membership(self):
        style, _ = _resolve_style_and_dances("Amateur Bronze Intl. Cha Cha (C)", "Bronze")
        self.assertEqual(style, Style.LATIN)

    def test_ambiguous_letter_disambiguated_by_membership(self):
        # "Swing" alone is ambiguous, but "S" is only a Rhythm letter (East
        # Coast Swing) within the Am. group's [Smooth, Rhythm] candidates -
        # Smooth's letters (W/T/F/V) don't include it.
        style, dances = _resolve_style_and_dances("Amateur Bronze Am. Swing (S)", "Bronze")
        self.assertEqual(style, Style.RHYTHM)
        self.assertEqual(dances, [Dance("Bronze", "Rhythm", "East Coast Swing")])

    def test_unrecognized_letter_raises(self):
        with self.assertRaises(ValueError):
            _resolve_style_and_dances("Amateur Bronze Am. Mystery (Z)", "Bronze")

    def test_nightclub_dance_name_read_from_heat_text(self):
        style, dances = _resolve_style_and_dances("Amateur Beginner Merengue (M)", "Beginner")
        self.assertEqual(style, Style.NIGHTCLUB)
        self.assertEqual(dances, [Dance("Beginner", "Nightclub", "Merengue")])

    def test_missing_code_raises(self):
        with self.assertRaises(ValueError):
            _resolve_style_and_dances("Amateur Bronze Am. Waltz", "Bronze")

    def test_trailing_underscore_placeholder_is_dropped(self):
        # Real heat: "Amateur Pre-Champ Rhythm (CRSB_)" - the trailing "_"
        # isn't a real dance slot.
        style, dances = _resolve_style_and_dances("Amateur Pre-Champ Rhythm (CRSB_)", "Prechamp")
        self.assertEqual(style, Style.RHYTHM)
        self.assertEqual(
            dances,
            [
                Dance("Prechamp", "Rhythm", "Cha Cha"),
                Dance("Prechamp", "Rhythm", "Rumba"),
                Dance("Prechamp", "Rhythm", "East Coast Swing"),
                Dance("Prechamp", "Rhythm", "Bolero"),
            ],
        )


class TestExtractNightclubDanceName(unittest.TestCase):
    def test_single_word_name(self):
        self.assertEqual(_extract_nightclub_dance_name("Amateur Beginner Merengue"), "Merengue")

    def test_multi_word_name_not_cut_short(self):
        self.assertEqual(
            _extract_nightclub_dance_name("Amateur Beginner Night Club 2-Step"),
            "Nightclub Two-Step",
        )

    def test_unrecognized_name_raises(self):
        with self.assertRaises(ValueError):
            _extract_nightclub_dance_name("Amateur Beginner Mystery Dance")


class TestSplitName(unittest.TestCase):
    def test_two_word_name(self):
        ref = _split_name("Spencer Schultz")
        self.assertEqual(ref.first, "Spencer")
        self.assertEqual(ref.last, "Schultz")

    def test_three_word_name_splits_on_last_space(self):
        ref = _split_name("Yue Tong Lee")
        self.assertEqual(ref.first, "Yue Tong")
        self.assertEqual(ref.last, "Lee")


class TestParsePlacementRow(unittest.TestCase):
    def test_row_with_state(self):
        place, lead, follow = _parse_placement_row("1) 141 Eugene Xie & Yue Tong Lee -  CA")
        self.assertEqual(place, 1)
        self.assertEqual(lead.full_name, "Eugene Xie")
        self.assertEqual(follow.full_name, "Yue Tong Lee")

    def test_row_with_no_state_at_all(self):
        place, lead, follow = _parse_placement_row("5) 241 Sean Gray & Sierra Hickerson")
        self.assertEqual(place, 5)
        self.assertEqual(lead.full_name, "Sean Gray")
        self.assertEqual(follow.full_name, "Sierra Hickerson")

    def test_tied_place(self):
        place, _, _ = _parse_placement_row("8) 143 Gregory Peregrin & Caitlyn Smith - CA")
        self.assertEqual(place, 8)

    def test_malformed_row_raises(self):
        with self.assertRaises(ValueError):
            _parse_placement_row("not a placement row")


class TestBuildResults(unittest.TestCase):
    def test_team_match_skipped_without_raising(self):
        # Real heat name: teams (not couples) have no individual CDA level
        # of their own, so this would otherwise fail level extraction.
        results = _build_results(
            "Am Team Match Open Intl. Multi-Dance (VCSWJ)",
            final_rows=["1) 100 Some Team"],
            num_rounds=1,
            competition_name="Test Classic",
            competition_date=date(2026, 1, 1),
        )

        self.assertEqual(results, [])


class TestParseResultsPage(unittest.TestCase):
    """Tests _parse_results_page() directly against the real, captured
    consolidated results page.
    """

    def setUp(self):
        self.html = _load_fixture("results_page.html")
        self.results = _parse_results_page(
            self.html, "Claremont Intercollegiate Showdown 2025", date(2025, 11, 14)
        )

    def _matching(self, level, style, dance_name):
        return [
            r
            for r in self.results
            if r.dance.level == level and r.dance.style == style and r.dance.dance == dance_name
        ]

    def test_single_dance_multi_round(self):
        matches = self._matching("Bronze", Style.SMOOTH, "Waltz")

        self.assertEqual(len(matches), 6)
        expected_dance = Dance("Bronze", "Smooth", "Waltz")
        by_place = {r.place: r for r in matches}
        self.assertEqual(set(by_place), set(range(1, 7)))
        self.assertEqual(by_place[1].lead.full_name, "Eugene Xie")
        self.assertEqual(by_place[1].follow.full_name, "Yue Tong Lee")
        self.assertEqual(by_place[6].lead.full_name, "Matthew Cummings")
        for result in matches:
            self.assertEqual(result.dance, expected_dance)
            self.assertEqual(result.num_rounds, 4)
            self.assertEqual(result.event_dances, (expected_dance,))

    def test_multi_dance_single_round_uses_bare_style_word(self):
        waltz = Dance("Champ", "Smooth", "Waltz")
        tango = Dance("Champ", "Smooth", "Tango")
        foxtrot = Dance("Champ", "Smooth", "Foxtrot")
        vwaltz = Dance("Champ", "Smooth", "Viennese Waltz")
        matches = self._matching("Champ", Style.SMOOTH, "Waltz") + self._matching(
            "Champ", Style.SMOOTH, "Tango"
        )

        self.assertEqual(len(matches), 4)  # 2 couples x 2 (of the 4) dances checked
        for result in matches:
            self.assertEqual(result.num_rounds, 1)
            self.assertEqual(result.event_dances, (waltz, tango, foxtrot, vwaltz))
        by_name_and_dance = {(r.lead.full_name, r.dance): r.place for r in matches}
        self.assertEqual(by_name_and_dance[("Brody Silva", waltz)], 1)
        self.assertEqual(by_name_and_dance[("Edward Rogers", waltz)], 2)

    def test_dance_table_title_ambiguous_letter(self):
        # "Amateur Bronze Am. Swing (S)" - confirmed real heat where the
        # bare letter code alone must disambiguate Rhythm from Smooth.
        matches = self._matching("Bronze", Style.RHYTHM, "East Coast Swing")

        self.assertEqual(len(matches), 7)
        for result in matches:
            self.assertEqual(result.num_rounds, 3)

    def test_nightclub_event(self):
        matches = self._matching("Beginner", Style.NIGHTCLUB, "Merengue")

        self.assertEqual(len(matches), 7)
        by_place = {r.place: r for r in matches}
        self.assertEqual(by_place[1].lead.full_name, "Nailah Cannon")
        for result in matches:
            self.assertEqual(result.num_rounds, 3)

    def test_v_waltz_abbreviation_and_final_group_tie(self):
        # "Amateur Gold Intl. V. Waltz (V)" - exercises the "V. Waltz"
        # alias and a genuine tie (two couples both placed 2nd) within the
        # Final group itself.
        matches = self._matching("Gold", Style.STANDARD, "Viennese Waltz")

        self.assertEqual(len(matches), 7)
        places = sorted(r.place for r in matches)
        self.assertEqual(places, [1, 2, 2, 4, 5, 6, 7])

    def test_tba_placeholder_partner_skipped(self):
        # "Rookie Leaders Bronze Intl. Cha Cha (C)" has 6 entries, one with
        # a "TBA01 TBA" placeholder partner (no real partner assigned) -
        # confirmed real data, must be excluded rather than crash parsing.
        matches = self._matching("Rookie Lead", Style.LATIN, "Cha Cha")

        self.assertEqual(len(matches), 5)
        self.assertNotIn("Trinity Yu", [r.lead.full_name for r in matches])


class TestParseCompetition(unittest.TestCase):
    def test_parses_the_whole_competition(self):
        client = _make_client({_RESULTS_KEY: _load_fixture("results_page.html")})

        results = parse_competition(
            "isc25", "Claremont Intercollegiate Showdown 2025", date(2025, 11, 14), client
        )

        self.assertGreater(len(results), 900)
        bronze_waltz = [r for r in results if r.dance == Dance("Bronze", "Smooth", "Waltz")]
        self.assertEqual(len(bronze_waltz), 6)


if __name__ == "__main__":
    unittest.main()
