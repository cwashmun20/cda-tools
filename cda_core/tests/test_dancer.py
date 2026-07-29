"""Tests for cda_core.lib.models.dancer module."""

import unittest
import datetime
import numpy as np
from cda_core.lib.api.client import DancerRecord
from cda_core.lib.models.dance import Dance
from cda_core.lib.models.dancer import Dancer


class TestDancerGetPoints(unittest.TestCase):
    """Tests for Dancer.get_points()."""

    def _make_dancer(self):
        record = DancerRecord(
            cda_id=1,
            first="Test",
            last="Dancer",
            first_comp_date=datetime.date(2020, 1, 1),
            created_date="2020-01-01",
            syllabus_pts=np.zeros((4, 19), dtype=int),
            open_pts=np.zeros((3, 4), dtype=int),
        )
        return Dancer.from_data(datetime.date(2026, 1, 1), record)

    def test_syllabus_level_returns_int(self):
        dancer = self._make_dancer()
        points = dancer.get_points(Dance("Bronze", "Smooth", "Waltz"))
        self.assertEqual(points, 0)

    def test_open_level_returns_int(self):
        dancer = self._make_dancer()
        points = dancer.get_points(Dance("Championship", "Standard", "Waltz"))
        self.assertEqual(points, 0)

    def test_nightclub_style_raises_value_error(self):
        dancer = self._make_dancer()
        with self.assertRaises(ValueError):
            dancer.get_points(Dance("Beginner", "Nightclub", "Salsa"))

    def test_rookie_vet_level_raises_value_error(self):
        """RkLead/RkFollow are FLC-eligible styles but not a syllabus or open
        level - get_points() should reject this explicitly rather than
        silently returning None."""
        dancer = self._make_dancer()
        with self.assertRaises(ValueError):
            dancer.get_points(Dance("Rookie Leader", "Smooth", "Waltz"))


if __name__ == "__main__":
    unittest.main()
