"""Tests for points_updating.lib.rules.cascade module."""

import unittest

import numpy as np

from points_updating.lib.rules import award_table, cascade
from utils.lib.models.dance import Dance


class TestBuildCascadeDelta(unittest.TestCase):
    """Tests for build_cascade_delta."""

    def test_worked_example_gold_smooth_tango_semifinal_second(self):
        """CDA website worked example: 2nd in Gold Smooth Tango via a
        semi-final awards 2 pts Gold Tango, 4 pts Silver Smooth Tango, and
        7 pts each to Bronze and Newcomer Smooth Tango - and nothing else.
        """
        award = award_table.compute_award(num_rounds=2, place=2)
        delta = cascade.build_cascade_delta((Dance("Gold", "Smooth", "Tango"),), award)

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
        delta = cascade.build_cascade_delta((Dance("Newcomer", "Standard", "Waltz"),), award)

        expected_syllabus = np.zeros((4, 19), dtype=int)
        expected_syllabus[0][0] = 3  # Newcomer Standard Waltz

        self.assertTrue(np.array_equal(delta.syllabus, expected_syllabus))
        self.assertTrue(np.array_equal(delta.open, np.zeros((3, 4), dtype=int)))

    def test_open_level_cascade_at_novice(self):
        """An open-danced event cascades into the entire style's syllabus
        columns, not a single dance, once it reaches syllabus levels.
        """
        award = award_table.compute_award(num_rounds=3, place=1)
        delta = cascade.build_cascade_delta((Dance("Novice", "Smooth", "Waltz"),), award)

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
        delta = cascade.build_cascade_delta((Dance("Championship", "Standard", "Waltz"),), award)

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

    def test_syllabus_multi_dance_combo_fans_same_award_into_every_dance(self):
        """A syllabus multi-dance combo's one overall placement earns the
        same award in each contained dance's own column - not split or
        divided across them, the full award independently in each.
        """
        award = award_table.compute_award(num_rounds=2, place=3)
        waltz = Dance("Silver", "Standard", "Waltz")
        quickstep = Dance("Silver", "Standard", "Quickstep")
        delta = cascade.build_cascade_delta((waltz, quickstep), award)

        expected_syllabus = np.zeros((4, 19), dtype=int)
        # Silver Standard Waltz (col 0) and Quickstep (col 4) both get the
        # full (1, 2, 7) cascade independently.
        expected_syllabus[2][0] = expected_syllabus[2][4] = 1
        expected_syllabus[1][0] = expected_syllabus[1][4] = 2
        expected_syllabus[0][0] = expected_syllabus[0][4] = 7

        self.assertTrue(np.array_equal(delta.syllabus, expected_syllabus))
        self.assertTrue(np.array_equal(delta.open, np.zeros((3, 4), dtype=int)))

    def test_open_multi_dance_combo_still_cascades_once_per_style(self):
        """An open multi-dance combo's cascade is unaffected by how many
        dances the combo covers - it already spans the whole style
        regardless, using only the representative (first) dance.
        """
        award = award_table.compute_award(num_rounds=3, place=1)
        waltz = Dance("Novice", "Smooth", "Waltz")
        tango = Dance("Novice", "Smooth", "Tango")
        single_dance_delta = cascade.build_cascade_delta((waltz,), award)
        multi_dance_delta = cascade.build_cascade_delta((waltz, tango), award)

        self.assertTrue(np.array_equal(single_dance_delta.open, multi_dance_delta.open))
        self.assertTrue(np.array_equal(single_dance_delta.syllabus, multi_dance_delta.syllabus))


if __name__ == "__main__":
    unittest.main()
