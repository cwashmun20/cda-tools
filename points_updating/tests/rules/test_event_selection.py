"""Tests for points_updating.lib.rules.event_selection module."""

import unittest
from datetime import date

from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.rules import event_selection
from utils.lib import constants
from utils.lib.constants import Style
from utils.lib.models.dance import Dance

_LEAD = DancerRef(first="Jane", last="Doe")
_FOLLOW = DancerRef(first="John", last="Smith")
_OTHER_LEAD = DancerRef(first="Alex", last="Zhu")
_OTHER_FOLLOW = DancerRef(first="Sam", last="Reyes")
_COMP_NAME = "Test Classic"
_COMP_DATE = date(2025, 10, 4)


def _make_result(
    level: str,
    style: str,
    dance_name: str,
    place: int,
    event_dance_names: tuple[str, ...],
    lead: DancerRef = _LEAD,
    follow: DancerRef = _FOLLOW,
) -> CompetitionResult:
    event_dances = tuple(Dance(level, style, name) for name in event_dance_names)
    return CompetitionResult(
        dance=Dance(level, style, dance_name),
        lead=lead,
        follow=follow,
        place=place,
        num_rounds=3,
        competition_name=_COMP_NAME,
        competition_date=_COMP_DATE,
        event_dances=event_dances,
    )


def _build_multi_event_group(
    level: str, style: str, event_specs: tuple[str, ...]
) -> dict[str, list[CompetitionResult]]:
    """Builds one CompetitionResult per dance across every event in
    event_specs (each spec a string of abbreviation letters, e.g. "WTF"),
    keyed by spec so callers can pick out an expected winning event's
    results.
    """
    abbrev_map = constants.ABBREVIATION_MAPS[Style(style)]
    groups = {}
    for spec in event_specs:
        event_dance_names = tuple(abbrev_map[letter] for letter in spec)
        groups[spec] = [
            _make_result(level, style, dance_name, place=1, event_dance_names=event_dance_names)
            for dance_name in event_dance_names
        ]
    return groups


class TestSelectScoringResults(unittest.TestCase):
    """Tests for select_points_event_results."""

    def _assert_selected_exactly(self, selected, expected):
        self.assertEqual(len(selected), len(expected))
        for result in expected:
            self.assertIn(result, selected)

    def test_couple_who_only_finaled_in_smaller_event_scores_nothing(self):
        """A couple who finaled in the single-dance event but NOT the
        multi-dance one must not fall back to the single-dance placement -
        the multi-dance event is still the points event for this level+
        style (another couple finaled there), so this couple simply has no
        points-event result at all.
        """
        wtf_results = [
            _make_result(
                "Novice", "Smooth", name, place=1, event_dance_names=("Waltz", "Tango", "Foxtrot")
            )
            for name in ("Waltz", "Tango", "Foxtrot")
        ]
        other_couple_v_result = _make_result(
            "Novice",
            "Smooth",
            "Viennese Waltz",
            place=1,
            event_dance_names=("Viennese Waltz",),
            lead=_OTHER_LEAD,
            follow=_OTHER_FOLLOW,
        )

        selected = event_selection.select_points_event_results(
            wtf_results + [other_couple_v_result]
        )

        self._assert_selected_exactly(selected, wtf_results)
        self.assertNotIn(other_couple_v_result, selected)

    def test_larger_event_wins_over_smaller_event(self):
        wtf_results = [
            _make_result(
                "Novice", "Smooth", name, place=1, event_dance_names=("Waltz", "Tango", "Foxtrot")
            )
            for name in ("Waltz", "Tango", "Foxtrot")
        ]
        v_result = _make_result(
            "Novice", "Smooth", "Viennese Waltz", place=1, event_dance_names=("Viennese Waltz",)
        )

        selected = event_selection.select_points_event_results(wtf_results + [v_result])

        self._assert_selected_exactly(selected, wtf_results)

    def test_tie_broken_by_waltz_presence(self):
        waltz_event = [
            _make_result("Novice", "Smooth", name, place=1, event_dance_names=("Waltz", "Tango"))
            for name in ("Waltz", "Tango")
        ]
        other_event = [
            _make_result(
                "Novice", "Smooth", name, place=1, event_dance_names=("Foxtrot", "Viennese Waltz")
            )
            for name in ("Foxtrot", "Viennese Waltz")
        ]

        selected = event_selection.select_points_event_results(waltz_event + other_event)

        self._assert_selected_exactly(selected, waltz_event)

    def test_single_event_passes_through_unchanged(self):
        results = [
            _make_result("Novice", "Smooth", name, place=1, event_dance_names=("Waltz", "Tango"))
            for name in ("Waltz", "Tango")
        ]

        selected = event_selection.select_points_event_results(results)

        self._assert_selected_exactly(selected, results)

    def test_syllabus_results_never_filtered(self):
        results = [
            _make_result("Gold", "Smooth", name, place=1, event_dance_names=("Waltz", "Tango"))
            for name in ("Waltz", "Tango")
        ] + [
            _make_result("Gold", "Smooth", "Foxtrot", place=1, event_dance_names=("Foxtrot",)),
        ]

        selected = event_selection.select_points_event_results(results)

        self._assert_selected_exactly(selected, results)

    def test_practical_open_level_combinations(self):
        """Real-world open-level event splits seen in practice, across
        every points-eligible style and open level, including groups of
        three events and the single-event case where every dance in a style
        runs as one combined event.
        """
        cases = [
            ("Novice", "Smooth", ("WTF", "V")),
            ("Prechamp", "Smooth", ("WTFV",)),
            ("Championship", "Smooth", ("WTFV",)),
            ("Novice", "Standard", ("WFQ", "T", "V")),
            ("Prechamp", "Standard", ("WTFQ", "V")),
            ("Championship", "Standard", ("WTVFQ",)),
            ("Novice", "Rhythm", ("CRS", "B", "M")),
            ("Prechamp", "Rhythm", ("CRSB", "M")),
            ("Championship", "Rhythm", ("CRSBM",)),
            ("Novice", "Latin", ("CSR", "P", "J")),
            ("Prechamp", "Latin", ("CSRJ", "P")),
            ("Championship", "Latin", ("CSRPJ",)),
        ]

        for level, style, event_specs in cases:
            with self.subTest(level=level, style=style, event_specs=event_specs):
                groups = _build_multi_event_group(level, style, event_specs)
                all_results = [result for group in groups.values() for result in group]
                winning_spec = max(event_specs, key=len)

                selected = event_selection.select_points_event_results(all_results)

                self._assert_selected_exactly(selected, groups[winning_spec])


if __name__ == "__main__":
    unittest.main()
