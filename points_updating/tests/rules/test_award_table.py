"""Tests for points_updating.lib.rules.award_table module."""

import unittest

from points_updating.lib.rules import award_table


class TestComputeAward(unittest.TestCase):
    """Tests for compute_award."""

    def test_final_only_always_zero(self):
        for place in range(1, 9):
            with self.subTest(place=place):
                self.assertEqual(award_table.compute_award(1, place), (0, 0, 0))

    def test_semi_final_table(self):
        expected = {
            1: (3, 6, 7),
            2: (2, 4, 7),
            3: (1, 2, 7),
            4: (0, 0, 7),
            5: (0, 0, 7),
            6: (0, 0, 7),
        }
        for place, award in expected.items():
            with self.subTest(place=place):
                self.assertEqual(award_table.compute_award(2, place), award)

    def test_quarter_final_or_more_table(self):
        expected = {
            1: (3, 6, 7),
            2: (2, 4, 7),
            3: (1, 2, 7),
            4: (1, 2, 7),
            5: (1, 2, 7),
            6: (1, 2, 7),
        }
        for num_rounds in (3, 4, 5):
            for place, award in expected.items():
                with self.subTest(num_rounds=num_rounds, place=place):
                    self.assertEqual(award_table.compute_award(num_rounds, place), award)

    def test_place_seven_or_worse_always_zero(self):
        for num_rounds in (2, 3, 4):
            for place in (7, 8, 12):
                with self.subTest(num_rounds=num_rounds, place=place):
                    self.assertEqual(award_table.compute_award(num_rounds, place), (0, 0, 0))

    def test_num_rounds_less_than_one_raises(self):
        with self.assertRaises(ValueError):
            award_table.compute_award(0, 1)


if __name__ == "__main__":
    unittest.main()
