"""Tests for utils.lib.proficiency_calculator module."""

import unittest
import datetime
import numpy as np
from utils.lib import constants
from utils.lib.api.client import DancerRecord
from utils.lib.constants import Style
from utils.lib.models.dancer import Dancer
from utils.lib.models.dance import Dance
from utils.lib.proficiency_calculator import ProficiencyCalculator


class TestProficiencyCalculator(unittest.TestCase):
    """Tests for the ProficiencyCalculator class."""

    def _champ_level_points(self, style: Style) -> tuple[np.ndarray, np.ndarray]:
        """Returns (syllabus_pts, open_pts) with every dance in style fully
        pointed out through Prechamp - i.e. a proficiency floor of Champ in
        that style, without being pointed out of Champ itself (there's no
        level above it to point further into).
        """
        syllabus_pts = np.zeros((4, 19), dtype=int)
        start = constants.SYLLABUS_COLUMN_OFFSETS[style]
        end = start + len(constants.DANCE_NAMES[style])
        syllabus_pts[:, start:end] = 7

        open_pts = np.zeros((3, 4), dtype=int)
        col = constants.STYLES.index(style)
        open_pts[0][col] = 7  # Novice pointed out
        open_pts[1][col] = 7  # Prechamp pointed out
        return syllabus_pts, open_pts

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

    def test_any_other_style_open_proficiency_creates_four_level_floor(self):
        """A dancer's open-level proficiency in ANY other style (not just
        the paired one) sets a floor four levels below it - the CDA doc's
        own worked example: a Champ-level Latin dancer is automatically at
        least Silver for Standard/Smooth dances, despite Standard/Smooth
        being paired with each other, not with Latin.
        """
        syllabus, open_pts = self._champ_level_points(Style.LATIN)
        dancer = self._make_dancer(syllabus, open_pts)  # proficiency floor = Champ in Latin

        rhythm_level = ProficiencyCalculator.compute_proficiency_level(dancer, "Rhythm", "Cha Cha")
        standard_level = ProficiencyCalculator.compute_proficiency_level(
            dancer, "Standard", "Waltz"
        )
        smooth_level = ProficiencyCalculator.compute_proficiency_level(dancer, "Smooth", "Waltz")

        self.assertEqual(rhythm_level, 4)  # paired style: Champ (6) - 2 = Novice
        self.assertEqual(standard_level, 2)  # unrelated style: Champ (6) - 4 = Silver
        self.assertEqual(smooth_level, 2)

    def test_any_other_style_floor_applies_to_unpaired_dances_too(self):
        """Unlike the paired-dance rule (which skips Quickstep/Samba/Paso
        Doble/Bolero/Mambo entirely), the any-other-style floor applies to
        every dance, including ones with no cross-style counterpart at all.
        """
        syllabus, open_pts = self._champ_level_points(Style.LATIN)
        dancer = self._make_dancer(syllabus, open_pts)

        quickstep_level = ProficiencyCalculator.compute_proficiency_level(
            dancer, "Standard", "Quickstep"
        )

        self.assertEqual(quickstep_level, 2)  # Champ (6) - 4 = Silver, despite no pairing

    def test_gold_point_out_alone_does_not_overreach_into_other_styles(self):
        """Pointing out through Gold in one style's dance lands exactly at
        the Novice floor there (index 4) - four levels below that is 0,
        always dominated by the experienced-dancer floor, so this
        shouldn't spuriously raise proficiency in an unrelated style.
        Complements test_quickstep_has_no_cross_style_pair, which covers
        the same scenario for the paired-dance rule specifically.
        """
        syllabus = np.zeros((4, 19), dtype=int)
        # Smooth Waltz (col 5) pointed out through Gold only - no open points.
        syllabus[0][5] = syllabus[1][5] = syllabus[2][5] = syllabus[3][5] = 7
        dancer = self._make_dancer(syllabus)

        level = ProficiencyCalculator.compute_proficiency_level(dancer, "Latin", "Samba")

        self.assertEqual(level, 1)  # Just the experienced-dancer floor

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
