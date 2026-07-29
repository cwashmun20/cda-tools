"""Tests for cda_core.lib.constants module."""

import unittest
from cda_core.lib.constants import (
    Style,
    SyllabusLevel,
    OpenLevel,
    NightclubLevel,
    RookieVetLevel,
    STYLES,
    AM_STYLES,
    INTL_STYLES,
    SYLLABUS_LEVELS,
    OPEN_LEVELS,
    LEVELS,
    NC_LEVELS,
    ALL_LEVELS,
    DANCE_NAMES,
    ABBREVIATION_MAPS,
)


class TestStyleEnum(unittest.TestCase):
    """Tests for the Style enum."""

    def test_values(self):
        self.assertEqual(Style.STANDARD, "Standard")
        self.assertEqual(Style.SMOOTH, "Smooth")
        self.assertEqual(Style.LATIN, "Latin")
        self.assertEqual(Style.RHYTHM, "Rhythm")
        self.assertEqual(Style.NIGHTCLUB, "Nightclub")

    def test_points_eligible_styles_excludes_nightclub(self):
        eligible = list(Style.points_eligible_styles())
        self.assertIn(Style.STANDARD, eligible)
        self.assertIn(Style.SMOOTH, eligible)
        self.assertIn(Style.LATIN, eligible)
        self.assertIn(Style.RHYTHM, eligible)
        self.assertNotIn(Style.NIGHTCLUB, eligible)
        self.assertEqual(len(eligible), 4)

    def test_american_styles(self):
        am = list(Style.american_styles())
        self.assertIn(Style.SMOOTH, am)
        self.assertIn(Style.RHYTHM, am)
        self.assertEqual(len(am), 2)

    def test_international_styles(self):
        intl = list(Style.international_styles())
        self.assertIn(Style.STANDARD, intl)
        self.assertIn(Style.LATIN, intl)
        self.assertEqual(len(intl), 2)

    def test_string_comparison(self):
        # StrEnum members work directly as strings
        self.assertTrue(Style.NIGHTCLUB == "Nightclub")
        self.assertTrue(Style.SMOOTH in ["Smooth", "Latin"])

    def test_dict_key(self):
        d = {Style.STANDARD: "standard"}
        self.assertEqual(d[Style.STANDARD], "standard")
        self.assertEqual(d["Standard"], "standard")


class TestSyllabusLevelEnum(unittest.TestCase):
    """Tests for the SyllabusLevel enum."""

    def test_values(self):
        self.assertEqual(SyllabusLevel.NEWCOMER, "Newcomer")
        self.assertEqual(SyllabusLevel.BRONZE, "Bronze")
        self.assertEqual(SyllabusLevel.SILVER, "Silver")
        self.assertEqual(SyllabusLevel.GOLD, "Gold")


class TestOpenLevelEnum(unittest.TestCase):
    """Tests for the OpenLevel enum."""

    def test_values(self):
        self.assertEqual(OpenLevel.NOVICE, "Novice")
        self.assertEqual(OpenLevel.PRECHAMP, "Prechamp")
        self.assertEqual(OpenLevel.CHAMP, "Champ")


class TestNightclubLevelEnum(unittest.TestCase):
    """Tests for the NightclubLevel enum."""

    def test_values(self):
        self.assertEqual(NightclubLevel.BEGINNER, "Beginner")
        self.assertEqual(NightclubLevel.INT_ADV, "IntAdv")


class TestRookieVetLevelEnum(unittest.TestCase):
    """Tests for the RookieVetLevel enum."""

    def test_values(self):
        self.assertEqual(RookieVetLevel.ROOKIE_LEAD, "RkLead")
        self.assertEqual(RookieVetLevel.ROOKIE_FOLLOW, "RkFollow")


class TestCompositeLists(unittest.TestCase):
    """Tests for the composite constant lists."""

    def test_styles(self):
        self.assertEqual(STYLES, ["Standard", "Smooth", "Latin", "Rhythm", "Nightclub"])
        self.assertEqual(len(STYLES), 5)

    def test_am_styles(self):
        self.assertEqual(AM_STYLES, ["Smooth", "Rhythm"])

    def test_intl_styles(self):
        self.assertEqual(INTL_STYLES, ["Standard", "Latin"])

    def test_syllabus_levels(self):
        self.assertEqual(SYLLABUS_LEVELS, ["Newcomer", "Bronze", "Silver", "Gold"])

    def test_open_levels(self):
        self.assertEqual(OPEN_LEVELS, ["Novice", "Prechamp", "Champ"])

    def test_levels(self):
        self.assertEqual(
            LEVELS, ["Newcomer", "Bronze", "Silver", "Gold", "Novice", "Prechamp", "Champ"]
        )
        self.assertEqual(len(LEVELS), 7)

    def test_nc_levels(self):
        self.assertEqual(NC_LEVELS, ["Beginner", "IntAdv"])

    def test_all_levels(self):
        self.assertEqual(len(ALL_LEVELS), 11)  # 7 syllabus/open + 2 NC + 2 RV
        self.assertIn("Newcomer", ALL_LEVELS)
        self.assertIn("Beginner", ALL_LEVELS)
        self.assertIn("RkLead", ALL_LEVELS)
        self.assertIn("RkFollow", ALL_LEVELS)


class TestDanceNames(unittest.TestCase):
    """Tests for the DANCE_NAMES dictionary."""

    def test_standard_dances(self):
        self.assertEqual(
            DANCE_NAMES["Standard"], ["Waltz", "Tango", "Viennese", "Foxtrot", "Quickstep"]
        )

    def test_smooth_dances(self):
        self.assertEqual(DANCE_NAMES["Smooth"], ["Waltz", "Tango", "Foxtrot", "Viennese"])

    def test_latin_dances(self):
        self.assertEqual(DANCE_NAMES["Latin"], ["ChaCha", "Samba", "Rumba", "Paso", "Jive"])

    def test_rhythm_dances(self):
        self.assertEqual(DANCE_NAMES["Rhythm"], ["ChaCha", "Rumba", "Swing", "Bolero", "Mambo"])

    def test_nightclub_dances(self):
        nc = DANCE_NAMES["Nightclub"]
        self.assertIn("WCS", nc)
        self.assertIn("Salsa", nc)
        self.assertIn("Bachata", nc)
        self.assertIn("Hustle", nc)

    def test_all_styles_present(self):
        for style in STYLES:
            self.assertIn(style, DANCE_NAMES)


class TestAbbreviationMaps(unittest.TestCase):
    """Tests for the ABBREVIATION_MAPS dictionary."""

    def test_standard_map(self):
        m = ABBREVIATION_MAPS["Standard"]
        self.assertEqual(m["W"], "Waltz")
        self.assertEqual(m["T"], "Tango")
        self.assertEqual(m["V"], "Viennese")
        self.assertEqual(m["F"], "Foxtrot")
        self.assertEqual(m["Q"], "Quickstep")

    def test_smooth_map(self):
        m = ABBREVIATION_MAPS["Smooth"]
        self.assertEqual(m["W"], "Waltz")
        self.assertEqual(m["T"], "Tango")
        self.assertEqual(m["F"], "Foxtrot")
        self.assertEqual(m["V"], "Viennese")

    def test_latin_map(self):
        m = ABBREVIATION_MAPS["Latin"]
        self.assertEqual(m["C"], "ChaCha")
        self.assertEqual(m["S"], "Samba")
        self.assertEqual(m["R"], "Rumba")
        self.assertEqual(m["P"], "Paso")
        self.assertEqual(m["J"], "Jive")

    def test_rhythm_map(self):
        m = ABBREVIATION_MAPS["Rhythm"]
        self.assertEqual(m["C"], "ChaCha")
        self.assertEqual(m["R"], "Rumba")
        self.assertEqual(m["S"], "Swing")
        self.assertEqual(m["B"], "Bolero")
        self.assertEqual(m["M"], "Mambo")


if __name__ == "__main__":
    unittest.main()
