"""Tests for points_updating.lib.report module."""

import unittest
from datetime import date

import numpy as np

from cda_core.lib.models.dance import Dance
from cda_core.lib.points import Points
from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.points_calculator import ResultAward
from points_updating.lib.report import build_report, render_report
from points_updating.lib.rules import award_table, cascade


def _make_award(
    dance: Dance,
    lead: DancerRef,
    follow: DancerRef,
    place: int,
    num_rounds: int,
    comp_date: date,
    comp_name: str = "Test Classic",
    is_split_level: bool = False,
) -> ResultAward:
    result = CompetitionResult(
        dance=dance,
        lead=lead,
        follow=follow,
        place=place,
        num_rounds=num_rounds,
        competition_name=comp_name,
        competition_date=comp_date,
        event_dances=(dance,),
    )
    delta = cascade.build_cascade_delta(dance, award_table.compute_award(num_rounds, place))
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
        self.assertIn("placed 2 of 2 round(s)", text)

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


if __name__ == "__main__":
    unittest.main()
