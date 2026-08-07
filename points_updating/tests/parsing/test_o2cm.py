"""Tests for points_updating.lib.parsing.o2cm module.

Fixtures are real, captured data from the Claremont Intercollegiate
Showdown 2025 (event=isc25).
"""

import unittest
from datetime import date
from pathlib import Path

import requests

from points_updating.lib.parsing.http_client import ThrottledClient
from points_updating.lib.parsing.o2cm import (
    _extract_level,
    _parse_heat,
    _resolve_style_and_dances,
    _split_couple_names,
    _split_name,
    fetch_competition_name,
    fetch_heat_list,
    fetch_heat_page,
    parse_competition,
)
from utils.lib.constants import Style
from utils.lib.models.dance import Dance

_FIXTURES = Path(__file__).parent / "fixtures" / "o2cm"
_EVENT_URL = "https://results.o2cm.com/event3.asp"
_SCORESHEET_URL = "https://results.o2cm.com/scoresheet3.asp"
_HEAT_LIST_KEY = (
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


class TestFetchHeatList(unittest.TestCase):
    def test_returns_heat_id_name_pairs(self):
        client = _make_client({_HEAT_LIST_KEY: _load_fixture("heat_list.html")})

        heats = fetch_heat_list("isc25", client)

        self.assertIn(("40322838", "Amateur  Bronze Am. Waltz  (W)"), heats)
        self.assertEqual(len(heats), 3)


class TestFetchHeatPage(unittest.TestCase):
    def test_returns_raw_html(self):
        fixture = _load_fixture("heat_bronze_waltz_final.html")
        client = _make_client(
            {
                (
                    "GET",
                    _SCORESHEET_URL,
                    (("event", "isc25"), ("heatid", "40322838")),
                ): fixture
            }
        )

        html = fetch_heat_page("isc25", "40322838", client)

        self.assertEqual(html, fixture)


class TestFetchCompetitionName(unittest.TestCase):
    def test_returns_name_from_landing_page(self):
        client = _make_client(
            {("GET", _EVENT_URL, (("event", "isc25"),)): _load_fixture("landing_page.html")}
        )

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


class TestResolveStyleAndDances(unittest.TestCase):
    def test_bare_style_word_for_multi_dance_heat(self):
        style, dances = _resolve_style_and_dances(
            "Amateur Silver Smooth (WT)", ["Waltz", "Tango"], "Silver"
        )
        self.assertEqual(style, Style.SMOOTH)
        self.assertEqual(
            dances, [Dance("Silver", "Smooth", "Waltz"), Dance("Silver", "Smooth", "Tango")]
        )

    def test_am_prefix_resolves_via_trial(self):
        style, dances = _resolve_style_and_dances(
            "Amateur Bronze Am. Waltz (W)", ["Waltz"], "Bronze"
        )
        self.assertEqual(style, Style.SMOOTH)
        self.assertEqual(dances, [Dance("Bronze", "Smooth", "Waltz")])

    def test_am_prefix_rhythm_dance_resolves_via_trial(self):
        style, dances = _resolve_style_and_dances(
            "Amateur Bronze Am. Cha Cha (C)", ["Cha Cha"], "Bronze"
        )
        self.assertEqual(style, Style.RHYTHM)

    def test_intl_prefix_resolves_via_trial(self):
        style, _ = _resolve_style_and_dances(
            "Amateur Bronze Intl. Cha Cha (C)", ["Cha Cha"], "Bronze"
        )
        self.assertEqual(style, Style.LATIN)


class TestSplitName(unittest.TestCase):
    def test_two_word_name(self):
        ref = _split_name("Spencer Schultz")
        self.assertEqual(ref.first, "Spencer")
        self.assertEqual(ref.last, "Schultz")

    def test_three_word_name_splits_on_last_space(self):
        ref = _split_name("Yue Tong Lee")
        self.assertEqual(ref.first, "Yue Tong")
        self.assertEqual(ref.last, "Lee")


class TestSplitCoupleNames(unittest.TestCase):
    def test_drops_trailing_state(self):
        lead, follow = _split_couple_names("Spencer Schultz, Lena Wessel -  CA")
        self.assertEqual(lead.full_name, "Spencer Schultz")
        self.assertEqual(follow.full_name, "Lena Wessel")

    def test_handles_empty_state(self):
        lead, follow = _split_couple_names("Eugene Xie, Yue Tong Lee -  ")
        self.assertEqual(lead.full_name, "Eugene Xie")
        self.assertEqual(follow.full_name, "Yue Tong Lee")


class TestParseHeat(unittest.TestCase):
    """Tests _parse_heat() directly against real, captured heat pages."""

    def test_single_dance_multi_round(self):
        html = _load_fixture("heat_bronze_waltz_final.html")

        results = _parse_heat(
            html,
            "Amateur  Bronze Am. Waltz  (W)",
            "Claremont Intercollegiate Showdown 2025",
            date(2025, 2, 8),
        )

        self.assertEqual(len(results), 6)
        expected_dance = Dance("Bronze", "Smooth", "Waltz")
        by_place = {r.place: r for r in results}
        self.assertEqual(set(by_place), set(range(1, 7)))
        self.assertEqual(by_place[1].lead.full_name, "Eugene Xie")
        self.assertEqual(by_place[1].follow.full_name, "Yue Tong Lee")
        self.assertEqual(by_place[6].lead.full_name, "Matthew Cummings")
        for result in results:
            self.assertEqual(result.dance, expected_dance)
            self.assertEqual(result.num_rounds, 4)
            self.assertEqual(result.event_dances, (expected_dance,))

    def test_multi_dance_single_round_uses_summary(self):
        html = _load_fixture("heat_championship_smooth_final.html")

        results = _parse_heat(
            html,
            "Amateur  Championship Smooth  (WTFV)",
            "Claremont Intercollegiate Showdown 2025",
            date(2025, 2, 8),
        )

        self.assertEqual(len(results), 8)  # 2 couples x 4 dances
        waltz = Dance("Championship", "Smooth", "Waltz")
        tango = Dance("Championship", "Smooth", "Tango")
        foxtrot = Dance("Championship", "Smooth", "Foxtrot")
        vwaltz = Dance("Championship", "Smooth", "Viennese Waltz")
        self.assertEqual(set(r.dance for r in results), {waltz, tango, foxtrot, vwaltz})
        for result in results:
            self.assertEqual(result.num_rounds, 1)
            self.assertEqual(result.event_dances, (waltz, tango, foxtrot, vwaltz))

        by_name_and_dance = {(r.lead.full_name, r.dance): r.place for r in results}
        self.assertEqual(by_name_and_dance[("Brody Silva", waltz)], 1)
        self.assertEqual(by_name_and_dance[("Brody Silva", tango)], 1)
        self.assertEqual(by_name_and_dance[("Edward Rogers", waltz)], 2)

    def test_multi_dance_multi_round(self):
        html = _load_fixture("heat_silver_smooth_final.html")

        results = _parse_heat(
            html,
            "Amateur  Silver Smooth  (WT)",
            "Claremont Intercollegiate Showdown 2025",
            date(2025, 2, 8),
        )

        self.assertEqual(len(results), 12)  # 6 couples x 2 dances
        waltz = Dance("Silver", "Smooth", "Waltz")
        tango = Dance("Silver", "Smooth", "Tango")
        for result in results:
            self.assertEqual(result.num_rounds, 3)
        by_name_and_dance = {(r.lead.full_name, r.dance): r.place for r in results}
        self.assertEqual(by_name_and_dance[("James Trongdee", waltz)], 1)
        self.assertEqual(by_name_and_dance[("James Trongdee", tango)], 1)
        self.assertEqual(by_name_and_dance[("Yannik Cadin", waltz)], 6)


class TestParseCompetition(unittest.TestCase):
    def test_parses_every_heat(self):
        client = _make_client(
            {
                _HEAT_LIST_KEY: _load_fixture("heat_list.html"),
                (
                    "GET",
                    _SCORESHEET_URL,
                    (("event", "isc25"), ("heatid", "40322838")),
                ): _load_fixture("heat_bronze_waltz_final.html"),
                (
                    "GET",
                    _SCORESHEET_URL,
                    (("event", "isc25"), ("heatid", "40323030")),
                ): _load_fixture("heat_silver_smooth_final.html"),
                (
                    "GET",
                    _SCORESHEET_URL,
                    (("event", "isc25"), ("heatid", "40328730")),
                ): _load_fixture("heat_championship_smooth_final.html"),
            }
        )

        results = parse_competition(
            "isc25", "Claremont Intercollegiate Showdown 2025", date(2025, 2, 8), client
        )

        # 6 (Bronze Waltz) + 12 (Silver Smooth WT) + 8 (Championship Smooth WTFV) = 26.
        self.assertEqual(len(results), 26)


if __name__ == "__main__":
    unittest.main()
