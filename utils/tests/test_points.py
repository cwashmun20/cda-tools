"""Tests for utils.lib.points module."""

import unittest
import numpy as np
from utils.lib.points import Points


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

    def test_add_zero_delta_is_noop(self):
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[1][5] = 4
        open_pts = np.zeros((3, 4), dtype=int)
        open_pts[0][0] = 2
        pts = Points(syllabus.copy(), open_pts.copy())

        pts.add(np.zeros((4, 19), dtype=int), np.zeros((3, 4), dtype=int))

        self.assertTrue(np.array_equal(pts.syllabus_data, syllabus))
        self.assertTrue(np.array_equal(pts.open_data, open_pts))

    def test_add_accumulates_onto_existing_values(self):
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[1][5] = 4  # pre-existing Bronze Smooth Waltz points
        pts = Points(syllabus, np.zeros((3, 4), dtype=int))

        syllabus_delta = np.zeros((4, 19), dtype=int)
        syllabus_delta[1][5] = 3
        syllabus_delta[0][5] = 7
        open_delta = np.zeros((3, 4), dtype=int)
        open_delta[0][1] = 2
        pts.add(syllabus_delta, open_delta)

        self.assertEqual(pts.syllabus_data[1][5], 7)  # 4 + 3, accumulated not overwritten
        self.assertEqual(pts.syllabus_data[0][5], 7)
        self.assertEqual(pts.open_data[0][1], 2)

    def test_add_leaves_negative_cell_untouched_instead_of_corrupting_it(self):
        """A negative cell is the DB's "already pointed out via cross-style
        pairing" marker, not a literal negative point count. Adding a real
        award on top of it (e.g. -1 + 7 = 6) would corrupt that marker into
        a misleadingly low value, so the cell is left as-is instead - it's
        already functionally equivalent to 7 for every consumer that
        matters, so there's no real total to compute for it.
        """
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[1][5] = -1  # already pointed out via cross-style pairing
        pts = Points(syllabus, np.zeros((3, 4), dtype=int))

        syllabus_delta = np.zeros((4, 19), dtype=int)
        syllabus_delta[1][5] = 7  # a real award earned in the same cell
        pts.add(syllabus_delta, np.zeros((3, 4), dtype=int))

        self.assertEqual(pts.syllabus_data[1][5], -1)

    def test_add_negative_open_cell_also_left_untouched(self):
        syllabus = np.zeros((4, 19), dtype=int)
        open_pts = np.zeros((3, 4), dtype=int)
        open_pts[0][0] = -1
        pts = Points(syllabus, open_pts)

        open_delta = np.zeros((3, 4), dtype=int)
        open_delta[0][0] = 3
        pts.add(np.zeros((4, 19), dtype=int), open_delta)

        self.assertEqual(pts.open_data[0][0], -1)

    def test_add_other_cells_still_accumulate_normally_alongside_a_negative_one(self):
        """A negative marker in one cell shouldn't block accumulation in
        every other (non-negative) cell during the same add() call."""
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[1][5] = -1
        syllabus[1][6] = 4
        pts = Points(syllabus, np.zeros((3, 4), dtype=int))

        syllabus_delta = np.zeros((4, 19), dtype=int)
        syllabus_delta[1][5] = 7
        syllabus_delta[1][6] = 3
        pts.add(syllabus_delta, np.zeros((3, 4), dtype=int))

        self.assertEqual(pts.syllabus_data[1][5], -1)
        self.assertEqual(pts.syllabus_data[1][6], 7)

    def test_add_does_not_mutate_delta_arrays(self):
        syllabus_delta = np.zeros((4, 19), dtype=int)
        syllabus_delta[0][0] = 5
        open_delta = np.zeros((3, 4), dtype=int)
        open_delta[0][0] = 3
        syllabus_delta_snapshot = syllabus_delta.copy()
        open_delta_snapshot = open_delta.copy()

        self.points.add(syllabus_delta, open_delta)

        self.assertTrue(np.array_equal(syllabus_delta, syllabus_delta_snapshot))
        self.assertTrue(np.array_equal(open_delta, open_delta_snapshot))


if __name__ == "__main__":
    unittest.main()
