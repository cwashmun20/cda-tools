"""Tests for cda_core.lib.parsing modules."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import unittest
import pandas as pd
from parsing.csv_reader import read_entries, validate_columns, normalize_column_names
from parsing.row_parser import is_tba_row, parse_dancer_names, extract_entry, EntryData
from parsing.multi_dance_expander import expand_abbreviation, expand_multi_dance_events


class TestCsvReader(unittest.TestCase):
    """Tests for parsing.csv_reader."""

    def test_validate_columns_valid(self):
        df = pd.DataFrame(columns=["Style", "Dance", "Skill", "Lead First",
                                    "Lead Last", "Follow First", "Follow Last"])
        self.assertTrue(validate_columns(df))

    def test_validate_columns_missing(self):
        df = pd.DataFrame(columns=["Style", "Dance"])
        with self.assertRaises(ValueError):
            validate_columns(df)

    def test_normalize_column_names_leader(self):
        df = pd.DataFrame(columns=["Leader First", "Leader Last", "Style"])
        result = normalize_column_names(df)
        self.assertIn("Lead First", result.columns)
        self.assertIn("Lead Last", result.columns)
        self.assertNotIn("Leader First", result.columns)

    def test_normalize_column_names_no_change(self):
        df = pd.DataFrame(columns=["Style", "Dance", "Lead First"])
        result = normalize_column_names(df)
        self.assertEqual(list(result.columns), ["Style", "Dance", "Lead First"])


class TestRowParser(unittest.TestCase):
    """Tests for parsing.row_parser."""

    def test_is_tba_row_false(self):
        row = pd.Series({"Lead First": "John", "Lead Last": "Doe",
                         "Follow First": "Jane", "Follow Last": "Smith"})
        self.assertFalse(is_tba_row(row))

    def test_is_tba_row_missing_lead(self):
        row = pd.Series({"Lead First": float('nan'), "Lead Last": "Doe",
                         "Follow First": "Jane", "Follow Last": "Smith"})
        self.assertTrue(is_tba_row(row))

    def test_is_tba_row_missing_follow(self):
        row = pd.Series({"Lead First": "John", "Lead Last": "Doe",
                         "Follow First": float('nan'), "Follow Last": float('nan')})
        self.assertTrue(is_tba_row(row))

    def test_parse_dancer_names(self):
        row = pd.Series({"Lead First": "John", "Lead Last": "Doe",
                         "Follow First": "Jane", "Follow Last": "Smith"})
        lead, follow = parse_dancer_names(row)
        self.assertEqual(lead, "John Doe")
        self.assertEqual(follow, "Jane Smith")

    def test_extract_entry(self):
        row = pd.Series({"Style": "Smooth", "Dance": "Waltz", "Skill": "Bronze",
                         "Lead First": "John", "Lead Last": "Doe",
                         "Follow First": "Jane", "Follow Last": "Smith"})
        entry = extract_entry(row, heat="10")
        self.assertIsInstance(entry, EntryData)
        self.assertEqual(entry.style, "Smooth")
        self.assertEqual(entry.dance_name, "Waltz")
        self.assertEqual(entry.level, "Bronze")
        self.assertEqual(entry.lead_first, "John")
        self.assertEqual(entry.lead_last, "Doe")
        self.assertEqual(entry.follow_first, "Jane")
        self.assertEqual(entry.follow_last, "Smith")
        self.assertEqual(entry.heat, "10")


class TestMultiDanceExpander(unittest.TestCase):
    """Tests for parsing.multi_dance_expander."""

    def test_expand_abbreviation_wtq(self):
        result = expand_abbreviation("Standard", "WTQ")
        self.assertEqual(result, ["Waltz", "Tango", "Quickstep"])

    def test_expand_abbreviation_fv(self):
        result = expand_abbreviation("Standard", "FV")
        self.assertEqual(result, ["Foxtrot", "Viennese"])

    def test_expand_abbreviation_csr(self):
        result = expand_abbreviation("Latin", "CSR")
        self.assertEqual(result, ["ChaCha", "Samba", "Rumba"])

    def test_expand_abbreviation_pj(self):
        result = expand_abbreviation("Latin", "PJ")
        self.assertEqual(result, ["Paso", "Jive"])

    def test_expand_abbreviation_crs(self):
        result = expand_abbreviation("Rhythm", "CRS")
        self.assertEqual(result, ["ChaCha", "Rumba", "Swing"])

    def test_expand_abbreviation_bm(self):
        result = expand_abbreviation("Rhythm", "BM")
        self.assertEqual(result, ["Bolero", "Mambo"])

    def test_expand_abbreviation_unknown_style(self):
        with self.assertRaises(ValueError):
            expand_abbreviation("Unknown", "WTQ")

    def test_expand_multi_dance_events(self):
        data = {"Style": ["Standard"], "Dance": ["WTQ"], "Skill": ["Bronze"],
                "Lead First": ["John"], "Lead Last": ["Doe"],
                "Follow First": ["Jane"], "Follow Last": ["Smith"]}
        df = pd.DataFrame(data)
        result = expand_multi_dance_events(df)
        self.assertEqual(len(result), 3)
        self.assertEqual(result["Dance"].tolist(), ["Waltz", "Tango", "Quickstep"])

    def test_expand_multi_dance_events_regular_unchanged(self):
        data = {"Style": ["Standard"], "Dance": ["Waltz"], "Skill": ["Bronze"],
                "Lead First": ["John"], "Lead Last": ["Doe"],
                "Follow First": ["Jane"], "Follow Last": ["Smith"]}
        df = pd.DataFrame(data)
        result = expand_multi_dance_events(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result["Dance"].tolist(), ["Waltz"])

    def test_expand_multi_dance_with_slash(self):
        data = {"Style": ["Standard"], "Dance": ["W/T/Q"], "Skill": ["Bronze"],
                "Lead First": ["John"], "Lead Last": ["Doe"],
                "Follow First": ["Jane"], "Follow Last": ["Smith"]}
        df = pd.DataFrame(data)
        result = expand_multi_dance_events(df)
        self.assertEqual(len(result), 3)
        self.assertEqual(result["Dance"].tolist(), ["Waltz", "Tango", "Quickstep"])


if __name__ == '__main__':
    unittest.main()