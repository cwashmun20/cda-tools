"""Tests for utils.lib.multi_dance module."""

import unittest

from utils.lib.multi_dance import expand_abbreviation


class TestExpandAbbreviation(unittest.TestCase):
    """Tests for expand_abbreviation."""

    def test_expand_abbreviation_wtq(self):
        result = expand_abbreviation("Standard", "WTQ")
        self.assertEqual(result, ["Waltz", "Tango", "Quickstep"])

    def test_expand_abbreviation_fv(self):
        result = expand_abbreviation("Standard", "FV")
        self.assertEqual(result, ["Foxtrot", "Viennese Waltz"])

    def test_expand_abbreviation_csr(self):
        result = expand_abbreviation("Latin", "CSR")
        self.assertEqual(result, ["Cha Cha", "Samba", "Rumba"])

    def test_expand_abbreviation_pj(self):
        result = expand_abbreviation("Latin", "PJ")
        self.assertEqual(result, ["Paso Doble", "Jive"])

    def test_expand_abbreviation_crs(self):
        result = expand_abbreviation("Rhythm", "CRS")
        self.assertEqual(result, ["Cha Cha", "Rumba", "East Coast Swing"])

    def test_expand_abbreviation_bm(self):
        result = expand_abbreviation("Rhythm", "BM")
        self.assertEqual(result, ["Bolero", "Mambo"])

    def test_expand_abbreviation_unknown_style(self):
        with self.assertRaises(ValueError):
            expand_abbreviation("Unknown", "WTQ")


if __name__ == "__main__":
    unittest.main()
