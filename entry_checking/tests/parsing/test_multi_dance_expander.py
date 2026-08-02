"""Tests for entry_checking.lib.parsing.multi_dance_expander."""

import unittest
import pandas as pd
from entry_checking.lib.parsing.multi_dance_expander import (
    expand_abbreviation,
    expand_multi_dance_events,
)


class TestMultiDanceExpander(unittest.TestCase):
    """Tests for parsing.multi_dance_expander."""

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

    def test_expand_multi_dance_events(self):
        data = {
            "Style": ["Standard"],
            "Dance": ["WTQ"],
            "Skill": ["Bronze"],
            "Lead First": ["Kaiyu"],
            "Lead Last": ["Ren"],
            "Follow First": ["Kristina"],
            "Follow Last": ["Andreyeva"],
        }
        df = pd.DataFrame(data)
        result = expand_multi_dance_events(df)
        self.assertEqual(len(result), 3)
        self.assertEqual(result["Dance"].tolist(), ["Waltz", "Tango", "Quickstep"])

    def test_expand_multi_dance_events_regular_unchanged(self):
        data = {
            "Style": ["Rhythm"],
            "Dance": ["Rumba"],
            "Skill": ["Bronze"],
            "Lead First": ["Alexey"],
            "Lead Last": ["Tregubov"],
            "Follow First": ["Madelyn"],
            "Follow Last": ["Officer"],
        }
        df = pd.DataFrame(data)
        result = expand_multi_dance_events(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result["Dance"].tolist(), ["Rumba"])

    def test_expand_multi_dance_with_slash(self):
        data = {
            "Style": ["Latin"],
            "Dance": ["C/S/R"],
            "Skill": ["Bronze"],
            "Lead First": ["Toby"],
            "Lead Last": ["Anderson"],
            "Follow First": ["Kenzie"],
            "Follow Last": ["Kaku"],
        }
        df = pd.DataFrame(data)
        result = expand_multi_dance_events(df)
        self.assertEqual(len(result), 3)
        self.assertEqual(result["Dance"].tolist(), ["Cha Cha", "Samba", "Rumba"])

    def test_expand_multi_dance_comma_separated_full_names(self):
        data = {
            "Style": ["Standard"],
            "Dance": ["Waltz,Tango,Foxtrot,Viennese Waltz"],
            "Skill": ["Prechamp"],
            "Lead First": ["Weston"],
            "Lead Last": ["Beebe"],
            "Follow First": ["Jessica"],
            "Follow Last": ["Lacy"],
        }
        df = pd.DataFrame(data)
        result = expand_multi_dance_events(df)
        self.assertEqual(len(result), 4)
        self.assertEqual(result["Dance"].tolist(), ["Waltz", "Tango", "Foxtrot", "Viennese Waltz"])

    def test_expand_multi_dance_style_alias_normalized_before_expansion(self):
        """The style alias for the abbreviation-map lookup ("Ballroom" ->
        "Standard") has to be resolved before expand_abbreviation runs, not
        just later when the Dance object gets constructed."""
        data = {
            "Style": ["Ballroom"],
            "Dance": ["WQ"],
            "Skill": ["Gold"],
            "Lead First": ["Yannik"],
            "Lead Last": ["Cadin"],
            "Follow First": ["Yuni"],
            "Follow Last": ["Jho"],
        }
        df = pd.DataFrame(data)
        result = expand_multi_dance_events(df)
        self.assertEqual(result["Dance"].tolist(), ["Waltz", "Quickstep"])

    def test_expand_multi_dance_comma_separated_strips_whitespace(self):
        data = {
            "Style": ["Rhythm"],
            "Dance": ["Cha Cha, Rumba, East Coast Swing"],
            "Skill": ["Gold"],
            "Lead First": ["Yannik"],
            "Lead Last": ["Cadin"],
            "Follow First": ["Moani"],
            "Follow Last": ["Ackbar"],
        }
        df = pd.DataFrame(data)
        result = expand_multi_dance_events(df)
        self.assertEqual(result["Dance"].tolist(), ["Cha Cha", "Rumba", "East Coast Swing"])


if __name__ == "__main__":
    unittest.main()
