"""Dance tests are in test_constants.py (Dance class tested via conversion functions)."""

import unittest
from utils.lib.models.dance import Dance, convert_dance, convert_level, convert_style


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
        self.assertEqual(str(d), "Rookie Lead Am. Waltz")

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
        self.assertEqual(convert_level("Int/Adv"), "Intermediate/Advanced")

    def test_convert_level_rookie_leader(self):
        self.assertEqual(convert_level("Rookie Leader"), "Rookie Lead")

    def test_convert_level_rookie_follower(self):
        self.assertEqual(convert_level("Rookie Follower"), "Rookie Follow")

    def test_convert_dance_west_coast(self):
        self.assertEqual(convert_dance("Nightclub", "West Coast Swing"), "West Coast Swing")

    def test_convert_dance_viennese_waltz(self):
        self.assertEqual(convert_dance("Smooth", "Viennese Waltz"), "Viennese Waltz")

    def test_convert_dance_standard_name(self):
        self.assertEqual(convert_dance("Standard", "Waltz"), "Waltz")

    def test_convert_style_exact(self):
        self.assertEqual(convert_style("Standard"), "Standard")

    def test_convert_style_ballroom_alias(self):
        self.assertEqual(convert_style("Ballroom"), "Standard")

    def test_convert_style_strips_whitespace(self):
        self.assertEqual(convert_style("  Latin  "), "Latin")

    def test_convert_style_unrecognized_raises(self):
        with self.assertRaises(ValueError):
            convert_style("Freestyle")

    def test_dance_with_ballroom_style(self):
        d = Dance("Bronze", "Ballroom", "Waltz")
        self.assertEqual(str(d), "Bronze Intl. Waltz")

    def test_convert_level_closed_prefix(self):
        self.assertEqual(convert_level("Closed Bronze"), "Bronze")

    def test_convert_level_rv_rookie_lead(self):
        self.assertEqual(convert_level("R/V Rookie Lead"), "Rookie Lead")

    def test_convert_level_rv_rookie_follow(self):
        self.assertEqual(convert_level("R/V Rookie Follow"), "Rookie Follow")

    def test_convert_level_strips_whitespace(self):
        self.assertEqual(convert_level("  Bronze  "), "Bronze")

    def test_convert_level_fuzzy_match(self):
        """A leading space plus otherwise-exact spelling should still fuzzy-match
        (this also exercises the whitespace-strip happening before comparison)."""
        self.assertEqual(convert_level("bronze"), "Bronze")

    def test_convert_dance_arg_tango_alias(self):
        self.assertEqual(convert_dance("Nightclub", "Arg. Tango"), "Argentine Tango")

    def test_convert_dance_wcs_alias(self):
        self.assertEqual(convert_dance("Nightclub", "WCS"), "West Coast Swing")

    def test_convert_dance_nc2s_alias(self):
        self.assertEqual(convert_dance("Nightclub", "NC2S"), "Nightclub Two-Step")

    def test_convert_dance_bare_swing_rhythm_alias(self):
        self.assertEqual(convert_dance("Rhythm", "Swing"), "East Coast Swing")

    def test_convert_dance_bare_swing_not_aliased_outside_rhythm(self):
        """ "Swing" alone shouldn't be silently reinterpreted for styles where
        it isn't the East Coast Swing shorthand (e.g. Nightclub, which has
        its own distinct "Country Swing" dance)."""
        with self.assertRaises(ValueError):
            convert_dance("Nightclub", "Swing")

    def test_convert_dance_fuzzy_match_no_space(self):
        self.assertEqual(convert_dance("Latin", "ChaCha"), "Cha Cha")

    def test_convert_dance_fuzzy_match_old_abbreviation(self):
        self.assertEqual(convert_dance("Nightclub", "Country 2-Step"), "Country Two-Step")

    def test_convert_dance_strips_whitespace(self):
        self.assertEqual(convert_dance("Standard", "  Waltz  "), "Waltz")

    def test_convert_dance_unrelated_fuzzy_candidate_not_matched(self):
        """Short, unrelated input shouldn't accidentally fuzzy-match something
        in a different style's dance list it happens to resemble."""
        with self.assertRaises(ValueError):
            convert_dance("Latin", "Paso")


if __name__ == "__main__":
    unittest.main()
