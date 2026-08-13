"""Tests for points_updating.lib.report module."""

import unittest
from datetime import date
from typing import Optional

import numpy as np

from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.points_calculator import ResultAward
from points_updating.lib.report import (
    UpdateReport,
    _level_breakdown,
    _ordinal,
    build_report,
    render_report,
)
from points_updating.lib.rules import award_table, cascade
from utils.lib.models.dance import Dance
from utils.lib.points import Points


def _make_award(
    dance: Dance,
    lead: DancerRef,
    follow: DancerRef,
    place: int,
    num_rounds: int,
    comp_date: date,
    comp_name: str = "Test Classic",
    is_split_level: bool = False,
    event_dances: Optional[tuple[Dance, ...]] = None,
) -> ResultAward:
    resolved_event_dances = event_dances if event_dances is not None else (dance,)
    result = CompetitionResult(
        dance=dance,
        lead=lead,
        follow=follow,
        place=place,
        num_rounds=num_rounds,
        competition_name=comp_name,
        competition_date=comp_date,
        event_dances=resolved_event_dances,
    )
    delta = cascade.build_cascade_delta(
        resolved_event_dances, award_table.compute_award(num_rounds, place)
    )
    return ResultAward(result=result, is_split_level=is_split_level, delta=delta)


def _zero_points() -> Points:
    return Points(np.zeros((4, 19), dtype=int), np.zeros((3, 4), dtype=int))


class TestBuildReport(unittest.TestCase):
    """Tests for build_report."""

    def test_groups_award_under_both_lead_and_follow(self):
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        award = _make_award(
            Dance("Bronze", "Smooth", "Waltz"),
            lead,
            follow,
            place=1,
            num_rounds=3,
            comp_date=date(2025, 10, 4),
        )
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}

        report = build_report([award], starting, final)

        names = {dr.dancer_name for dr in report.dancer_reports}
        self.assertEqual(names, {"Lead Dancer", "Follow Dancer"})
        for dancer_report in report.dancer_reports:
            self.assertEqual(dancer_report.awards, [award])

    def test_includes_zero_point_awards(self):
        """A placement that scores 0 points (below the award table's rows)
        still appears - the report should be able to answer "why didn't I
        earn points here", not just show nonzero changes."""
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        award = _make_award(
            Dance("Bronze", "Smooth", "Waltz"),
            lead,
            follow,
            place=7,
            num_rounds=2,
            comp_date=date(2025, 10, 4),
        )
        self.assertEqual(int(award.delta.syllabus.sum() + award.delta.open.sum()), 0)
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}

        report = build_report([award], starting, final)

        self.assertEqual(len(report.dancer_reports[0].awards), 1)

    def test_sorts_each_dancers_awards_chronologically(self):
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        dance = Dance("Bronze", "Smooth", "Waltz")
        later = _make_award(
            dance, lead, follow, place=1, num_rounds=3, comp_date=date(2025, 11, 15)
        )
        earlier = _make_award(
            dance, lead, follow, place=1, num_rounds=3, comp_date=date(2025, 10, 4)
        )
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}

        # Passed out of order - build_report must sort per dancer itself.
        report = build_report([later, earlier], starting, final)

        for dancer_report in report.dancer_reports:
            dates = [award.result.competition_date for award in dancer_report.awards]
            self.assertEqual(dates, sorted(dates))


class TestRenderReport(unittest.TestCase):
    """Tests for render_report."""

    def test_rendered_text_contains_expected_content(self):
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        award = _make_award(
            Dance("Silver", "Smooth", "Waltz"),
            lead,
            follow,
            place=2,
            num_rounds=2,
            comp_date=date(2025, 10, 4),
            comp_name="Fall Classic",
            is_split_level=True,
        )
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        report = build_report([award], starting, final)

        text = render_report(report)

        self.assertIn("Lead Dancer", text)
        self.assertIn("Follow Dancer", text)
        self.assertIn("Fall Classic", text)
        self.assertIn("2025-10-04", text)
        self.assertIn("SPLIT-LEVEL EXCEPTION", text)
        self.assertIn("Placed 2nd from 2 round(s)", text)
        # 2nd place, Semi-Final, Silver: 2 (Silver) // 4 (Bronze) // 7 (Newcomer).
        self.assertIn("Silver +2, Bronze +4, Newcomer +7", text)

    def test_starting_and_final_totals_render_stacked_and_grouped(self):
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        award = _make_award(
            Dance("Bronze", "Smooth", "Waltz"),
            lead,
            follow,
            place=1,
            num_rounds=3,
            comp_date=date(2025, 10, 4),
        )
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        report = build_report([award], starting, final)

        text = render_report(report)

        self.assertIn("Starting:", text)
        self.assertIn("Final:", text)
        # Both totals tables must appear before any award line, and Starting
        # must come before Final - grouped together for easy comparison.
        starting_idx = text.index("Starting:")
        final_idx = text.index("Final:")
        award_idx = text.index("Placed")
        self.assertLess(starting_idx, final_idx)
        self.assertLess(final_idx, award_idx)

    def test_competition_listed_once_with_awards_indented_underneath(self):
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        waltz_award = _make_award(
            Dance("Bronze", "Smooth", "Waltz"),
            lead,
            follow,
            place=1,
            num_rounds=2,
            comp_date=date(2025, 10, 4),
            comp_name="Fall Classic",
        )
        tango_award = _make_award(
            Dance("Bronze", "Smooth", "Tango"),
            lead,
            follow,
            place=2,
            num_rounds=2,
            comp_date=date(2025, 10, 4),
            comp_name="Fall Classic",
        )
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        report = build_report([waltz_award, tango_award], starting, final)

        # Isolate one dancer's section - both lead and follow otherwise
        # each get their own "Fall Classic" header (one per dancer, not
        # one per award), which would make a whole-report count of 2 a
        # false positive for the thing this test is actually checking:
        # the header not repeating once per award *within* one section.
        lead_report = next(dr for dr in report.dancer_reports if dr.dancer_name == "Lead Dancer")
        text = render_report(UpdateReport(dancer_reports=[lead_report]))

        self.assertEqual(text.count("Fall Classic"), 1)
        self.assertIn("2025-10-04 Fall Classic:\n  Bronze Am. Waltz", text)
        self.assertIn("\n  Bronze Am. Tango", text)

    def test_two_competitions_on_the_same_date_get_separate_headers(self):
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        dance = Dance("Bronze", "Smooth", "Waltz")
        first_comp = _make_award(
            dance,
            lead,
            follow,
            place=1,
            num_rounds=2,
            comp_date=date(2025, 10, 4),
            comp_name="Morning Classic",
        )
        second_comp = _make_award(
            dance,
            lead,
            follow,
            place=1,
            num_rounds=2,
            comp_date=date(2025, 10, 4),
            comp_name="Evening Classic",
        )
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        report = build_report([first_comp, second_comp], starting, final)

        text = render_report(report)

        self.assertIn("2025-10-04 Morning Classic:", text)
        self.assertIn("2025-10-04 Evening Classic:", text)

    def test_multi_dance_award_line_shows_every_dance_in_the_combo(self):
        """An open-level multi-dance combo now collapses to a single award
        line (one CompetitionResult, keyed off the first dance) - that line
        should still show every dance danced, not just the representative
        one, via event_dances.
        """
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        waltz = Dance("Novice", "Standard", "Waltz")
        foxtrot = Dance("Novice", "Standard", "Foxtrot")
        quickstep = Dance("Novice", "Standard", "Quickstep")
        award = _make_award(
            waltz,
            lead,
            follow,
            place=1,
            num_rounds=2,
            comp_date=date(2025, 10, 4),
            event_dances=(waltz, foxtrot, quickstep),
        )
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        report = build_report([award], starting, final)

        text = render_report(report)

        self.assertIn("Novice Intl. Waltz/Foxtrot/Quickstep", text)

    def test_syllabus_multi_dance_combo_shows_one_combined_award_line(self):
        """A syllabus multi-dance combo now also collapses to a single
        CompetitionResult (the same overall placement's award fans out to
        every dance's own column via cascade.py) - the report shows one
        line for the whole combo, same as an open combo, not one line per
        dance.
        """
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        waltz = Dance("Silver", "Standard", "Waltz")
        quickstep = Dance("Silver", "Standard", "Quickstep")
        award = _make_award(
            waltz,
            lead,
            follow,
            place=3,
            num_rounds=3,
            comp_date=date(2025, 10, 4),
            event_dances=(waltz, quickstep),
        )
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        report = build_report([award], starting, final)

        text = render_report(report)

        self.assertIn("Silver Intl. Waltz/Quickstep", text)
        self.assertEqual(text.count("Placed"), 2)  # once per dancer's section, not per dance

    def test_single_dance_award_line_is_unchanged(self):
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        award = _make_award(
            Dance("Bronze", "Smooth", "Waltz"),
            lead,
            follow,
            place=1,
            num_rounds=3,
            comp_date=date(2025, 10, 4),
        )
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        report = build_report([award], starting, final)

        text = render_report(report)

        self.assertIn("Bronze Am. Waltz", text)
        self.assertNotIn("/", text)

    def test_non_split_level_award_has_no_split_level_marker(self):
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        award = _make_award(
            Dance("Bronze", "Smooth", "Waltz"),
            lead,
            follow,
            place=1,
            num_rounds=3,
            comp_date=date(2025, 10, 4),
        )
        starting = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        final = {"Lead Dancer": _zero_points(), "Follow Dancer": _zero_points()}
        report = build_report([award], starting, final)

        text = render_report(report)

        self.assertNotIn("SPLIT-LEVEL", text)


class TestOrdinal(unittest.TestCase):
    def test_first_second_third(self):
        self.assertEqual(_ordinal(1), "1st")
        self.assertEqual(_ordinal(2), "2nd")
        self.assertEqual(_ordinal(3), "3rd")

    def test_fourth_and_up_default_to_th(self):
        self.assertEqual(_ordinal(4), "4th")
        self.assertEqual(_ordinal(7), "7th")

    def test_eleventh_twelfth_thirteenth_are_th_not_st_nd_rd(self):
        self.assertEqual(_ordinal(11), "11th")
        self.assertEqual(_ordinal(12), "12th")
        self.assertEqual(_ordinal(13), "13th")

    def test_twenty_first_is_st(self):
        self.assertEqual(_ordinal(21), "21st")


class TestLevelBreakdown(unittest.TestCase):
    """Tests for _level_breakdown."""

    def test_syllabus_event_breaks_down_by_cascaded_level(self):
        dance = Dance("Silver", "Smooth", "Waltz")
        delta = cascade.build_cascade_delta((dance,), award_table.compute_award(2, 2))

        breakdown = _level_breakdown(delta)

        self.assertEqual(breakdown, [("Silver", 2), ("Bronze", 4), ("Newcomer", 7)])

    def test_open_event_does_not_overcount_multi_dance_cascade_row(self):
        """An open-level cascade adds the same point value to every dance
        in a syllabus level's row, not just one - summing the row would
        overcount by the number of dances in that style.
        """
        dance = Dance("Novice", "Smooth", "Waltz")
        delta = cascade.build_cascade_delta((dance,), award_table.compute_award(2, 1))

        breakdown = _level_breakdown(delta)

        # 1st, Semi-Final, Novice (open): 3 (Novice) // 6 (Gold) // 7 (Silver+Bronze+Newcomer).
        self.assertEqual(
            breakdown, [("Novice", 3), ("Gold", 6), ("Silver", 7), ("Bronze", 7), ("Newcomer", 7)]
        )

    def test_zero_award_has_empty_breakdown(self):
        dance = Dance("Bronze", "Smooth", "Waltz")
        delta = cascade.build_cascade_delta((dance,), award_table.compute_award(2, 7))

        self.assertEqual(_level_breakdown(delta), [])


if __name__ == "__main__":
    unittest.main()
