"""Tests for flc_entry_checking.lib.rules.proficiency module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'cda_core', 'lib'))

import unittest
import datetime
import numpy as np
from api.client import DancerRecord
from models.dancer import Dancer
from models.dance import Dance
from rules.proficiency import ProficiencyCalculator


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
            cda_id=None, first="New", last="Comer",
            first_comp_date=None, created_date="2026-01-01",
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


if __name__ == '__main__':
    unittest.main()