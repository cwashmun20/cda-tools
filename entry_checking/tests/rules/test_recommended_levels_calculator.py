"""Tests for entry_checking.lib.rules.recommended_levels_calculator module."""

import unittest
import datetime
import numpy as np
from cda_core.lib.api.client import DancerRecord
from cda_core.lib.models.dancer import Dancer
from cda_core.lib.models.partnership import Partnership
from entry_checking.lib.rules.recommended_levels_calculator import RecommendedLevelsCalculator


class TestRecommendedLevelsCalculator(unittest.TestCase):
    """Tests for RecommendedLevelsCalculator.compute()."""

    def _make_new_dancer(self, first, last):
        """A dancer just starting out (first competition is today)."""
        record = DancerRecord(
            cda_id=None,
            first=first,
            last=last,
            first_comp_date=None,
            created_date="2026-01-01",
            syllabus_pts=np.zeros((4, 19), dtype=int),
            open_pts=np.zeros((3, 4), dtype=int),
        )
        return Dancer.from_data(datetime.date(2026, 6, 1), record)

    def _make_dancer(self, first, last, syllabus_pts=None, open_pts=None):
        """An experienced (>1yr) dancer with controlled points."""
        if syllabus_pts is None:
            syllabus_pts = np.zeros((4, 19), dtype=int)
        if open_pts is None:
            open_pts = np.zeros((3, 4), dtype=int)
        record = DancerRecord(
            cda_id=1,
            first=first,
            last=last,
            first_comp_date=datetime.date(2020, 1, 1),
            created_date="2020-01-01",
            syllabus_pts=syllabus_pts,
            open_pts=open_pts,
        )
        return Dancer.from_data(datetime.date(2026, 1, 1), record)

    def test_both_newcomers_recommends_newcomer_and_bronze(self):
        lead = self._make_new_dancer("Lead", "Dancer")
        follow = self._make_new_dancer("Follow", "Dancer")
        partnership = Partnership(lead, follow)
        levels = RecommendedLevelsCalculator.compute(partnership, "Standard")
        self.assertEqual(levels, ["Newcomer", "Bronze"])

    def test_experienced_zero_points_recommends_bronze_and_silver(self):
        """A non-newcomer's per-dance proficiency floor is never Newcomer,
        so an experienced partnership with zero points is never recommended
        Newcomer even though its point-out level alone would be 0."""
        lead = self._make_dancer("Lead", "Dancer")
        follow = self._make_dancer("Follow", "Dancer")
        partnership = Partnership(lead, follow)
        levels = RecommendedLevelsCalculator.compute(partnership, "Standard")
        self.assertEqual(levels, ["Bronze", "Silver"])

    def test_point_out_raises_recommendation(self):
        """Pointing out of one dance in the style (here, Standard Tango at
        Newcomer+Bronze) raises the whole style's recommendation, since the
        couple can no longer be recommended below that dance's floor."""
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][1] = syllabus[1][1] = 7  # Standard Tango: Newcomer+Bronze pointed out
        lead = self._make_dancer("Lead", "Dancer", syllabus)
        follow = self._make_dancer("Follow", "Dancer")
        partnership = Partnership(lead, follow)
        levels = RecommendedLevelsCalculator.compute(partnership, "Standard")
        self.assertEqual(levels, ["Silver", "Gold"])

    def test_top_level_has_no_level_above(self):
        """Fully pointed out through Prechamp leaves Champ as the floor -
        there's no level above Champ to also recommend."""
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][0] = syllabus[1][0] = syllabus[2][0] = syllabus[3][0] = 7  # Standard Waltz
        open_pts = np.zeros((3, 4), dtype=int)
        open_pts[0][0] = open_pts[1][0] = 7  # Novice, Prechamp Standard
        lead = self._make_dancer("Lead", "Dancer", syllabus, open_pts)
        follow = self._make_dancer("Follow", "Dancer")
        partnership = Partnership(lead, follow)
        levels = RecommendedLevelsCalculator.compute(partnership, "Standard")
        self.assertEqual(levels, ["Champ"])

    def test_nightclub_raises_value_error(self):
        lead = self._make_dancer("Lead", "Dancer")
        follow = self._make_dancer("Follow", "Dancer")
        partnership = Partnership(lead, follow)
        with self.assertRaises(ValueError):
            RecommendedLevelsCalculator.compute(partnership, "Nightclub")


if __name__ == "__main__":
    unittest.main()
