"""Dance tests are in test_constants.py (Dance class tested via conversion functions)."""

import unittest
from cda_core.lib.models.dance import Dance, convert_dance, convert_level


class TestDance(unittest.TestCase):
    """Tests for the Dance class."""

    def test_bronze_smooth_waltz(self):
        d = Dance("Bronze", "Smooth", "Waltz")
        self.assertEqual(str(d), "Bronze Am. Waltz")

    def test_champ_standard_quickstep(self):
        d = Dance("Championship", "Standard", "Quickstep")
        self.assertEqual(str(d), "Champ Intl. Quickstep")

    def test_prechamp_latin_jive(self):
        d = Dance("Pre-Champ", "Latin", "Jive")
        self.assertEqual(str(d), "Prechamp Intl. Jive")

    def test_beginner_nightclub_salsa(self):
        d = Dance("Beginner", "Nightclub", "Salsa")
        self.assertEqual(str(d), "Beginner Salsa")

    def test_rookie_lead(self):
        d = Dance("Rookie Leader", "Smooth", "Waltz")
        self.assertEqual(str(d), "RkLead Am. Waltz")

    def test_equality(self):
        d1 = Dance("Bronze", "Smooth", "Waltz")
        d2 = Dance("Bronze", "Smooth", "Waltz")
        self.assertEqual(d1, d2)

    def test_inequality(self):
        d1 = Dance("Bronze", "Smooth", "Waltz")
        d2 = Dance("Silver", "Smooth", "Waltz")
        self.assertNotEqual(d1, d2)

    def test_eq_non_dance_returns_false(self):
        """Comparing a Dance to an unrelated type should be False, not None."""
        d = Dance("Bronze", "Smooth", "Waltz")
        self.assertFalse(d == "Bronze Am. Waltz")
        self.assertNotEqual(d, 42)

    def test_hash(self):
        d1 = Dance("Bronze", "Smooth", "Waltz")
        d2 = Dance("Bronze", "Smooth", "Waltz")
        self.assertEqual(hash(d1), hash(d2))

    def test_convert_level_newcomer(self):
        self.assertEqual(convert_level("Newcomer"), "Newcomer")

    def test_convert_level_prechamp(self):
        self.assertEqual(convert_level("Pre-Champ"), "Prechamp")

    def test_convert_level_intadv(self):
        self.assertEqual(convert_level("Int/Adv"), "IntAdv")

    def test_convert_level_rookie_leader(self):
        self.assertEqual(convert_level("Rookie Leader"), "RkLead")

    def test_convert_level_rookie_follower(self):
        self.assertEqual(convert_level("Rookie Follower"), "RkFollow")

    def test_convert_dance_west_coast(self):
        self.assertEqual(convert_dance("Nightclub", "West Coast Swing"), "WCS")

    def test_convert_dance_viennese_waltz(self):
        self.assertEqual(convert_dance("Smooth", "Viennese Waltz"), "Viennese")

    def test_convert_dance_standard_name(self):
        self.assertEqual(convert_dance("Standard", "Waltz"), "Waltz")


if __name__ == "__main__":
    unittest.main()
