"""Tests for entry_checking.lib.parsing.multi_dance_resolver."""

import unittest

from entry_checking.lib.parsing.multi_dance_resolver import resolve_dance_names


class TestResolveDanceNames(unittest.TestCase):
    """Tests for resolve_dance_names."""

    def test_letter_abbreviation_expands_to_dance_names(self):
        self.assertEqual(resolve_dance_names("WTQ", "Standard"), ["Waltz", "Tango", "Quickstep"])

    def test_single_dance_row_unchanged(self):
        self.assertEqual(resolve_dance_names("Rumba", "Rhythm"), ["Rumba"])

    def test_slash_separated_letters_expand_to_dance_names(self):
        self.assertEqual(resolve_dance_names("C/S/R", "Latin"), ["Cha Cha", "Samba", "Rumba"])

    def test_comma_separated_full_names(self):
        self.assertEqual(
            resolve_dance_names("Waltz,Tango,Foxtrot,Viennese Waltz", "Standard"),
            ["Waltz", "Tango", "Foxtrot", "Viennese Waltz"],
        )

    def test_style_alias_normalized_before_expansion(self):
        """The style alias for the abbreviation-map lookup ("Ballroom" ->
        "Standard") has to be resolved before expand_abbreviation runs, not
        just later when the Dance object gets constructed."""
        self.assertEqual(resolve_dance_names("WQ", "Ballroom"), ["Waltz", "Quickstep"])

    def test_comma_separated_strips_whitespace(self):
        self.assertEqual(
            resolve_dance_names("Cha Cha, Rumba, East Coast Swing", "Rhythm"),
            ["Cha Cha", "Rumba", "East Coast Swing"],
        )


if __name__ == "__main__":
    unittest.main()
