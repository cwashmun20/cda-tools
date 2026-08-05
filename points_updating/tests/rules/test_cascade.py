"""Tests for points_updating.lib.rules.cascade module."""

import unittest

import numpy as np

from cda_core.lib.models.dance import Dance
from points_updating.lib.rules import award_table, cascade


class TestBuildCascadeDelta(unittest.TestCase):
    """Tests for build_cascade_delta."""

    def test_worked_example_gold_smooth_tango_semifinal_second(self):
        """CDA website worked example: 2nd in Gold Smooth Tango via a
        semi-final awards 2 pts Gold Tango, 4 pts Silver Smooth Tango, and
        7 pts each to Bronze and Newcomer Smooth Tango - and nothing else.
        """
        award = award_table.compute_award(num_rounds=2, place=2)
        delta = cascade.build_cascade_delta(Dance("Gold", "Smooth", "Tango"), award)

        expected_syllabus = np.zeros((4, 19), dtype=int)
        expected_syllabus[3][6] = 2  # Gold Smooth Tango
        expected_syllabus[2][6] = 4  # Silver Smooth Tango
        expected_syllabus[1][6] = 7  # Bronze Smooth Tango
        expected_syllabus[0][6] = 7  # Newcomer Smooth Tango

        self.assertTrue(np.array_equal(delta.syllabus, expected_syllabus))
        self.assertTrue(np.array_equal(delta.open, np.zeros((3, 4), dtype=int)))

    def test_newcomer_danced_event_has_no_lower_cells(self):
        """A Newcomer-danced event has no level below it to cascade into."""
        award = award_table.compute_award(num_rounds=3, place=1)
        delta = cascade.build_cascade_delta(Dance("Newcomer", "Standard", "Waltz"), award)

        expected_syllabus = np.zeros((4, 19), dtype=int)
        expected_syllabus[0][0] = 3  # Newcomer Standard Waltz

        self.assertTrue(np.array_equal(delta.syllabus, expected_syllabus))
        self.assertTrue(np.array_equal(delta.open, np.zeros((3, 4), dtype=int)))

    def test_open_level_cascade_at_novice(self):
        """An open-danced event cascades into the entire style's syllabus
        columns, not a single dance, once it reaches syllabus levels.
        """
        award = award_table.compute_award(num_rounds=3, place=1)
        delta = cascade.build_cascade_delta(Dance("Novice", "Smooth", "Waltz"), award)

        expected_open = np.zeros((3, 4), dtype=int)
        expected_open[0][1] = 3  # Novice Smooth

        expected_syllabus = np.zeros((4, 19), dtype=int)
        expected_syllabus[3][5:9] = 6  # Gold, entire Smooth column range
        expected_syllabus[2][5:9] = 7  # Silver, entire Smooth column range
        expected_syllabus[1][5:9] = 7  # Bronze, entire Smooth column range
        expected_syllabus[0][5:9] = 7  # Newcomer, entire Smooth column range

        self.assertTrue(np.array_equal(delta.open, expected_open))
        self.assertTrue(np.array_equal(delta.syllabus, expected_syllabus))

    def test_open_level_cascade_at_champ(self):
        """A Champ-danced event cascades through Prechamp and Novice (open),
        then through every syllabus level of the same style.
        """
        award = award_table.compute_award(num_rounds=3, place=1)
        delta = cascade.build_cascade_delta(Dance("Championship", "Standard", "Waltz"), award)

        expected_open = np.zeros((3, 4), dtype=int)
        expected_open[2][0] = 3  # Champ Standard
        expected_open[1][0] = 6  # Prechamp Standard
        expected_open[0][0] = 7  # Novice Standard

        expected_syllabus = np.zeros((4, 19), dtype=int)
        expected_syllabus[3][0:5] = 7  # Gold, entire Standard column range
        expected_syllabus[2][0:5] = 7  # Silver, entire Standard column range
        expected_syllabus[1][0:5] = 7  # Bronze, entire Standard column range
        expected_syllabus[0][0:5] = 7  # Newcomer, entire Standard column range

        self.assertTrue(np.array_equal(delta.open, expected_open))
        self.assertTrue(np.array_equal(delta.syllabus, expected_syllabus))


if __name__ == "__main__":
    unittest.main()
