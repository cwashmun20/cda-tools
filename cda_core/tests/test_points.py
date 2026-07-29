"""Tests for cda_core.lib.points module."""

import unittest
import numpy as np
from cda_core.lib.points import Points


class TestPoints(unittest.TestCase):
    """Tests for the Points class."""

    def setUp(self):
        self.syllabus_pts = np.zeros((4, 19), dtype=int)
        self.open_pts = np.zeros((3, 4), dtype=int)
        self.points = Points(self.syllabus_pts, self.open_pts)

    def test_constructor(self):
        self.assertIsInstance(self.points, Points)
        self.assertTrue(np.array_equal(self.points.syllabus_data, self.syllabus_pts))
        self.assertTrue(np.array_equal(self.points.open_data, self.open_pts))

    def test_standard(self):
        s, o = self.points.standard()
        self.assertEqual(s.shape, (4, 5))
        self.assertEqual(o.shape, (3, 1))

    def test_smooth(self):
        s, o = self.points.smooth()
        self.assertEqual(s.shape, (4, 4))
        self.assertEqual(o.shape, (3, 1))

    def test_latin(self):
        s, o = self.points.latin()
        self.assertEqual(s.shape, (4, 5))
        self.assertEqual(o.shape, (3, 1))

    def test_rhythm(self):
        s, o = self.points.rhythm()
        self.assertEqual(s.shape, (4, 5))
        self.assertEqual(o.shape, (3, 1))

    def test_linear_data_length(self):
        ld = self.points.linear_data()
        # 4 levels * 19 dances + 3 open levels * 4 styles = 76 + 12 = 88
        self.assertEqual(len(ld), 88)

    def test_linear_data_order(self):
        # Set a value in Newcomer Standard Waltz (index 0)
        self.syllabus_pts[0][0] = 5
        pts = Points(self.syllabus_pts, self.open_pts)
        ld = pts.linear_data()
        self.assertEqual(ld[0], 5)

    def test_repr_contains_levels(self):
        r = repr(self.points)
        self.assertIn("Newcomer", r)
        self.assertIn("Bronze", r)
        self.assertIn("Silver", r)
        self.assertIn("Gold", r)
        self.assertIn("Novice", r)
        self.assertIn("Prechamp", r)
        self.assertIn("Champ", r)

    def test_repr_contains_headers(self):
        r = repr(self.points)
        self.assertIn("Standard", r)
        self.assertIn("Smooth", r)
        self.assertIn("Latin", r)
        self.assertIn("Rhythm", r)

    def test_points_with_values(self):
        syllabus = np.ones((4, 19), dtype=int) * 3
        open_pts = np.ones((3, 4), dtype=int) * 2
        pts = Points(syllabus, open_pts)
        self.assertEqual(pts.syllabus_data[0][0], 3)
        self.assertEqual(pts.open_data[0][0], 2)


if __name__ == "__main__":
    unittest.main()
