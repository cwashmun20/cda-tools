"""Tests for entry_checking.lib.parsing.row_parser."""

import unittest
import pandas as pd
from entry_checking.lib.parsing.row_parser import (
    is_tba_row,
    parse_dancer_names,
    extract_entry,
    EntryData,
)


class TestRowParser(unittest.TestCase):
    """Tests for parsing.row_parser."""

    def test_is_tba_row_false(self):
        row = pd.Series(
            {
                "Lead First": "Ford",
                "Lead Last": "Ashmun",
                "Follow First": "Toby",
                "Follow Last": "Anderson",
            }
        )
        self.assertFalse(is_tba_row(row))

    def test_is_tba_row_missing_lead(self):
        row = pd.Series(
            {
                "Lead First": float("nan"),
                "Lead Last": "Patel",
                "Follow First": "Elena",
                "Follow Last": "Rossi",
            }
        )
        self.assertTrue(is_tba_row(row))

    def test_is_tba_row_missing_follow(self):
        row = pd.Series(
            {
                "Lead First": "Preston",
                "Lead Last": "Lowe",
                "Follow First": float("nan"),
                "Follow Last": float("nan"),
            }
        )
        self.assertTrue(is_tba_row(row))

    def test_is_tba_row_null_string(self):
        """Some organizers write the literal string "NULL" instead of leaving
        the cell blank."""
        row = pd.Series(
            {
                "Lead First": "NULL",
                "Lead Last": "NULL",
                "Follow First": "Alyx",
                "Follow Last": "Quiroga",
            }
        )
        self.assertTrue(is_tba_row(row))

    def test_is_tba_row_null_string_lowercase(self):
        row = pd.Series(
            {
                "Lead First": "null",
                "Lead Last": "null",
                "Follow First": "Alyx",
                "Follow Last": "Quiroga",
            }
        )
        self.assertTrue(is_tba_row(row))

    def test_parse_dancer_names(self):
        row = pd.Series(
            {
                "Lead First": "Ford",
                "Lead Last": "Ashmun",
                "Follow First": "Sam",
                "Follow Last": "Saltiel",
            }
        )
        lead, follow = parse_dancer_names(row)
        self.assertEqual(lead, "Ford Ashmun")
        self.assertEqual(follow, "Sam Saltiel")

    def test_extract_entry(self):
        row = pd.Series(
            {
                "Style": "Smooth",
                "Dance": "Waltz",
                "Skill": "Bronze",
                "Lead First": "Kierah",
                "Lead Last": "James",
                "Follow First": "Mia",
                "Follow Last": "Wootton",
            }
        )
        entry = extract_entry(row, heat="10")
        self.assertIsInstance(entry, EntryData)
        self.assertEqual(entry.style, "Smooth")
        self.assertEqual(entry.dance_name, "Waltz")
        self.assertEqual(entry.level, "Bronze")
        self.assertEqual(entry.lead_first, "Kierah")
        self.assertEqual(entry.lead_last, "James")
        self.assertEqual(entry.follow_first, "Mia")
        self.assertEqual(entry.follow_last, "Wootton")
        self.assertEqual(entry.heat, "10")


if __name__ == "__main__":
    unittest.main()
