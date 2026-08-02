"""Tests for entry_checking.lib.parsing.csv_reader."""

import unittest
import pandas as pd
from entry_checking.lib.parsing.csv_reader import (
    validate_columns,
    normalize_column_names,
    drop_placeholder_rows,
)


class TestCsvReader(unittest.TestCase):
    """Tests for parsing.csv_reader."""

    def test_validate_columns_valid(self):
        df = pd.DataFrame(
            columns=[
                "Style",
                "Dance",
                "Skill",
                "Lead First",
                "Lead Last",
                "Follow First",
                "Follow Last",
            ]
        )
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

    def test_normalize_column_names_dances_and_level(self):
        df = pd.DataFrame(columns=["Style", "Dances", "Level"])
        result = normalize_column_names(df)
        self.assertIn("Dance", result.columns)
        self.assertIn("Skill", result.columns)
        self.assertNotIn("Dances", result.columns)
        self.assertNotIn("Level", result.columns)

    def test_drop_placeholder_rows_dash(self):
        """Excel sometimes exports a deleted/blank row as all-dashes."""
        df = pd.DataFrame(
            {
                "Style": ["Standard", "-"],
                "Dance": ["Waltz", "-"],
                "Skill": ["Bronze", "-"],
            }
        )
        result = drop_placeholder_rows(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result["Style"].tolist(), ["Standard"])

    def test_drop_placeholder_rows_ref_error(self):
        """Excel sometimes exports a deleted/blank row as all-#REF! errors."""
        df = pd.DataFrame(
            {
                "Style": ["Standard", "#REF!"],
                "Dance": ["Waltz", "#REF!"],
                "Skill": ["Bronze", "#REF!"],
            }
        )
        result = drop_placeholder_rows(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result["Style"].tolist(), ["Standard"])

    def test_drop_placeholder_rows_no_placeholders(self):
        df = pd.DataFrame({"Style": ["Standard", "Smooth"]})
        result = drop_placeholder_rows(df)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
