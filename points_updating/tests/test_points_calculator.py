"""Tests for points_updating.lib.points_calculator module."""

import datetime
import unittest

import numpy as np

from cda_core.lib.api.client import DancerRecord
from cda_core.lib.models.dance import Dance
from cda_core.lib.models.dancer import Dancer
from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.points_calculator import PointsCalculator
from points_updating.lib.rules import cascade


def _make_dancer(first, last, syllabus_pts=None, open_pts=None):
    """Helper to create a real Dancer with controlled points - same shape as
    cda_core/tests/test_proficiency_calculator.py's dancer-building helper.
    """
    if syllabus_pts is None:
        syllabus_pts = np.zeros((4, 19), dtype=int)
    if open_pts is None:
        open_pts = np.zeros((3, 4), dtype=int)
    record = DancerRecord(
        cda_id=1,
        first=first,
        last=last,
        first_comp_date=datetime.date(2020, 1, 1),  # >1 year ago - not a newcomer
        created_date="2020-01-01",
        syllabus_pts=syllabus_pts,
        open_pts=open_pts,
    )
    return Dancer.from_data(datetime.date(2026, 1, 1), record)


def _make_result(dance: Dance, place: int, num_rounds: int) -> CompetitionResult:
    return CompetitionResult(
        dance=dance,
        lead=DancerRef(first="Lead", last="Dancer"),
        follow=DancerRef(first="Follow", last="Dancer"),
        place=place,
        num_rounds=num_rounds,
        competition_name="Test Classic",
        competition_date=datetime.date(2025, 10, 4),
        event_dances=(dance,),
    )


class TestPointsCalculator(unittest.TestCase):
    """Tests for PointsCalculator.compute."""

    def test_matched_proficiency_scores_unmodified_award(self):
        """Lead and follow proficiency levels match, so combined_level is
        None and the award table's value applies unmodified."""
        lead = _make_dancer("Lead", "Dancer")
        follow = _make_dancer("Follow", "Dancer")
        dance = Dance("Bronze", "Smooth", "Waltz")
        result = _make_result(dance, place=1, num_rounds=3)  # quarter-or-more 1st -> (3, 6, 7)

        award = PointsCalculator.compute(result, lead, follow)

        self.assertFalse(award.is_split_level)
        expected_delta = cascade.build_cascade_delta(dance, (3, 6, 7))
        self.assertTrue(np.array_equal(award.delta.syllabus, expected_delta.syllabus))
        self.assertTrue(np.array_equal(award.delta.open, expected_delta.open))

    def test_split_level_exception_triples_award(self):
        """Lead and follow proficiency differ by >=2 levels and they danced
        at the level combined_level designates, tripling the award. Same
        setup as test_eligibility_checker.py's test_split_level_exception: lead
        pointed out to Gold (3), follow at the Bronze floor (1) - the gap's
        combined_level (max-1 = 2) equals the Silver event being danced."""
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][5] = syllabus[1][5] = syllabus[2][5] = 7  # Smooth Waltz -> Gold (3)
        lead = _make_dancer("Lead", "Dancer", syllabus)
        follow = _make_dancer("Follow", "Dancer")  # zero points -> Bronze floor (1)
        dance = Dance("Silver", "Smooth", "Waltz")
        result = _make_result(dance, place=2, num_rounds=2)  # semifinal 2nd -> (2, 4, 7)

        award = PointsCalculator.compute(result, lead, follow)

        self.assertTrue(award.is_split_level)
        expected_delta = cascade.build_cascade_delta(dance, (6, 12, 21))  # 3x (2, 4, 7)
        self.assertTrue(np.array_equal(award.delta.syllabus, expected_delta.syllabus))
        self.assertTrue(np.array_equal(award.delta.open, expected_delta.open))

    def test_split_level_not_triggered_when_combined_mismatches_event(self):
        """Lead and follow proficiency differ by >=2 levels, but they danced
        at a different level than combined_level designates, so the award
        isn't tripled. Same setup as test_eligibility_checker.py's
        test_split_level_exception_not_triggered_when_combined_mismatches_event:
        same gap as above, but registered for Bronze instead of the Silver
        level combined_level (2) designates."""
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][5] = syllabus[1][5] = syllabus[2][5] = 7  # lead -> Gold (3)
        lead = _make_dancer("Lead", "Dancer", syllabus)
        follow = _make_dancer("Follow", "Dancer")  # Bronze (1)
        dance = Dance("Bronze", "Smooth", "Waltz")
        result = _make_result(dance, place=1, num_rounds=2)  # semifinal 1st -> (3, 6, 7)

        award = PointsCalculator.compute(result, lead, follow)

        self.assertFalse(award.is_split_level)
        expected_delta = cascade.build_cascade_delta(dance, (3, 6, 7))
        self.assertTrue(np.array_equal(award.delta.syllabus, expected_delta.syllabus))
        self.assertTrue(np.array_equal(award.delta.open, expected_delta.open))

    def test_nightclub_dance_raises(self):
        lead = _make_dancer("Lead", "Dancer")
        follow = _make_dancer("Follow", "Dancer")
        dance = Dance("Beginner", "Nightclub", "Salsa")
        result = _make_result(dance, place=1, num_rounds=2)

        with self.assertRaises(ValueError):
            PointsCalculator.compute(result, lead, follow)


if __name__ == "__main__":
    unittest.main()
