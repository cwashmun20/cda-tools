"""Tests for cda_core.lib.rules.proficiency module."""

import unittest
import datetime
import numpy as np
from cda_core.lib.api.client import DancerRecord
from cda_core.lib.models.dancer import Dancer
from cda_core.lib.models.dance import Dance
from cda_core.lib.rules.proficiency import ProficiencyCalculator


class TestProficiencyCalculator(unittest.TestCase):
    """Tests for the ProficiencyCalculator class."""

    def _make_dancer(self, syllabus_pts=None, open_pts=None):
        """Helper to create a Dancer with controlled points for testing."""
        if syllabus_pts is None:
            syllabus_pts = np.zeros((4, 19), dtype=int)
        if open_pts is None:
            open_pts = np.zeros((3, 4), dtype=int)
        record = DancerRecord(
            cda_id=1,
            first="Test",
            last="Dancer",
            first_comp_date=datetime.date(2020, 1, 1),  # >1 year ago
            created_date="2020-01-01",
            syllabus_pts=syllabus_pts,
            open_pts=open_pts,
        )
        return Dancer.from_data(datetime.date(2026, 1, 1), record)

    def test_has_pointed_out_zero_points(self):
        dancer = self._make_dancer()
        dance = Dance("Bronze", "Smooth", "Waltz")
        self.assertFalse(ProficiencyCalculator.has_pointed_out(dancer, dance))

    def test_has_pointed_out_at_seven(self):
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[1][5] = 7  # Bronze Smooth Waltz
        dancer = self._make_dancer(syllabus)
        dance = Dance("Bronze", "Smooth", "Waltz")
        self.assertTrue(ProficiencyCalculator.has_pointed_out(dancer, dance))

    def test_has_pointed_out_above_seven(self):
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][0] = 10  # Newcomer Standard Waltz
        dancer = self._make_dancer(syllabus)
        dance = Dance("Newcomer", "Standard", "Waltz")
        self.assertTrue(ProficiencyCalculator.has_pointed_out(dancer, dance))

    def test_has_pointed_out_negative(self):
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][0] = -1
        dancer = self._make_dancer(syllabus)
        dance = Dance("Newcomer", "Standard", "Waltz")
        self.assertTrue(ProficiencyCalculator.has_pointed_out(dancer, dance))

    def test_has_pointed_out_below_seven(self):
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[2][10] = 6  # Silver Latin Rumba
        dancer = self._make_dancer(syllabus)
        dance = Dance("Silver", "Latin", "Rumba")
        self.assertFalse(ProficiencyCalculator.has_pointed_out(dancer, dance))

    def test_compute_point_out_level_no_points(self):
        dancer = self._make_dancer()
        level = ProficiencyCalculator.compute_point_out_level(dancer, "Standard", "Waltz")
        self.assertEqual(level, 0)

    def test_compute_point_out_level_one_level(self):
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][0] = 7  # Newcomer Standard Waltz pointed out
        dancer = self._make_dancer(syllabus)
        level = ProficiencyCalculator.compute_point_out_level(dancer, "Standard", "Waltz")
        self.assertEqual(level, 1)

    def test_compute_point_out_level_two_levels(self):
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][0] = 7  # Newcomer pointed out
        syllabus[1][0] = 7  # Bronze pointed out
        dancer = self._make_dancer(syllabus)
        level = ProficiencyCalculator.compute_point_out_level(dancer, "Standard", "Waltz")
        self.assertEqual(level, 2)

    def test_newcomer_proficiency_new_dancer(self):
        """A new dancer with no points should have proficiency 0 (Newcomer)."""
        record = DancerRecord(
            cda_id=None,
            first="New",
            last="Comer",
            first_comp_date=None,
            created_date="2026-01-01",
            syllabus_pts=np.zeros((4, 19), dtype=int),
            open_pts=np.zeros((3, 4), dtype=int),
        )
        dancer = Dancer.from_data(datetime.date(2026, 6, 1), record)
        level = ProficiencyCalculator.compute_proficiency_level(dancer, "Smooth", "Waltz")
        self.assertEqual(level, 0)

    def test_experienced_dancer_min_bronze(self):
        """A dancer competing >1 year has minimum proficiency 1 (Bronze)."""
        dancer = self._make_dancer()
        level = ProficiencyCalculator.compute_proficiency_level(dancer, "Smooth", "Waltz")
        self.assertEqual(level, 1)  # Not newcomer since first comp >1 year ago

    def test_within_style_proficiency(self):
        """Pointing out of one dance in a style raises proficiency in others
        in that style (never more than 2 levels lower than the pointed-out dance)."""
        syllabus = np.zeros((4, 19), dtype=int)
        # Standard Tango (col 1) pointed out at Newcomer/Bronze/Silver/Gold.
        syllabus[0][1] = syllabus[1][1] = syllabus[2][1] = syllabus[3][1] = 7
        dancer = self._make_dancer(syllabus)
        # Standard Waltz (col 0) itself has zero points.
        level = ProficiencyCalculator.compute_proficiency_level(dancer, "Standard", "Waltz")
        self.assertEqual(level, 2)  # Tango point-out level (4) - 2 = Silver

    def test_within_style_does_not_affect_other_styles(self):
        """Within-style proficiency only looks at dances in the same style."""
        syllabus = np.zeros((4, 19), dtype=int)
        # Standard Tango (col 1) fully pointed out.
        syllabus[0][1] = syllabus[1][1] = syllabus[2][1] = syllabus[3][1] = 7
        dancer = self._make_dancer(syllabus)
        # Rhythm Rumba is a different style entirely - unaffected.
        level = ProficiencyCalculator.compute_proficiency_level(dancer, "Rhythm", "Rumba")
        self.assertEqual(level, 1)  # Just the experienced-dancer floor

    def test_cross_style_same_name_pair(self):
        """Pointing out of Standard Waltz raises Smooth Waltz proficiency (same-name pair)."""
        syllabus = np.zeros((4, 19), dtype=int)
        # Standard Waltz (col 0) pointed out at Newcomer/Bronze/Silver/Gold.
        syllabus[0][0] = syllabus[1][0] = syllabus[2][0] = syllabus[3][0] = 7
        dancer = self._make_dancer(syllabus)
        # Smooth Waltz (col 5) itself has zero points.
        level = ProficiencyCalculator.compute_proficiency_level(dancer, "Smooth", "Waltz")
        self.assertEqual(level, 2)  # Standard Waltz point-out level (4) - 2 = Silver

    def test_cross_style_jive_swing_pair(self):
        """Jive (Latin) and Swing (Rhythm) are cross-style paired despite the name mismatch."""
        syllabus = np.zeros((4, 19), dtype=int)
        # Rhythm Swing (col 16 = 14 + DANCE_NAMES['Rhythm'].index('Swing')=2) fully pointed out.
        syllabus[0][16] = syllabus[1][16] = syllabus[2][16] = syllabus[3][16] = 7
        dancer = self._make_dancer(syllabus)
        level = ProficiencyCalculator.compute_proficiency_level(dancer, "Latin", "Jive")
        self.assertEqual(level, 2)  # Rhythm Swing point-out level (4) - 2 = Silver

    def test_quickstep_has_no_cross_style_pair(self):
        """Quickstep has no American-style counterpart, so mastery elsewhere in
        Smooth doesn't raise Standard Quickstep proficiency."""
        syllabus = np.zeros((4, 19), dtype=int)
        # Smooth Waltz (col 5) fully pointed out - should have zero bearing on Quickstep.
        syllabus[0][5] = syllabus[1][5] = syllabus[2][5] = syllabus[3][5] = 7
        dancer = self._make_dancer(syllabus)
        level = ProficiencyCalculator.compute_proficiency_level(dancer, "Standard", "Quickstep")
        self.assertEqual(level, 1)  # Just the experienced-dancer floor - no cross-style credit

    def test_split_level_combined_level_equal(self):
        """Equal proficiency levels don't qualify for the Split-Level Exception."""
        self.assertIsNone(ProficiencyCalculator.compute_split_level_combined_level(2, 2))

    def test_split_level_combined_level_differ_by_one(self):
        """A one-level difference doesn't qualify either - needs >= 2."""
        self.assertIsNone(ProficiencyCalculator.compute_split_level_combined_level(3, 2))

    def test_split_level_combined_level_differ_by_two_lead_higher(self):
        self.assertEqual(ProficiencyCalculator.compute_split_level_combined_level(4, 2), 3)

    def test_split_level_combined_level_differ_by_two_follow_higher(self):
        """Symmetric regardless of which partner is higher."""
        self.assertEqual(ProficiencyCalculator.compute_split_level_combined_level(2, 4), 3)

    def test_split_level_combined_level_large_gap(self):
        self.assertEqual(ProficiencyCalculator.compute_split_level_combined_level(6, 0), 5)


if __name__ == "__main__":
    unittest.main()
