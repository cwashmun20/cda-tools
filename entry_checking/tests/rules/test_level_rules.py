"""Tests for entry_checking.lib.rules.level_rules module."""

import unittest
from cda_core.lib.models.dance import Dance
from entry_checking.lib.rules.level_rules import LevelRulesChecker


class _FakeEntry:
    """Minimal stand-in for Entry - LevelRulesChecker only reads dance_data."""

    def __init__(self, dance_obj):
        self.dance_data = dance_obj


class _FakeDancer:
    """Minimal stand-in for Dancer - LevelRulesChecker only reads name/entries."""

    def __init__(self, name, dances):
        self.name = name
        self.entries = {_FakeEntry(d) for d in dances}


class TestLevelRulesChecker(unittest.TestCase):
    """Tests for LevelRulesChecker.check()."""

    def test_no_entries_no_violations(self):
        dancer = _FakeDancer("Solo", [])
        self.assertEqual(LevelRulesChecker.check(dancer), [])

    def test_single_dance_within_limit_no_violation(self):
        dancer = _FakeDancer(
            "Solo",
            [Dance("Bronze", "Standard", "Waltz"), Dance("Silver", "Standard", "Waltz")],
        )
        self.assertEqual(LevelRulesChecker.check(dancer), [])

    def test_same_dance_too_many_levels(self):
        dancer = _FakeDancer(
            "Solo",
            [
                Dance("Bronze", "Standard", "Waltz"),
                Dance("Silver", "Standard", "Waltz"),
                Dance("Gold", "Standard", "Waltz"),
            ],
        )
        violations = LevelRulesChecker.check(dancer)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].violation_type, "too_many_levels")
        self.assertEqual(violations[0].dance, "Waltz")
        self.assertEqual(violations[0].levels, [1, 2, 3])

    def test_same_dance_non_consecutive_gap(self):
        """Bronze + Gold Waltz with nothing at Silver is a gap for that dance,
        even though only 2 levels are registered (within the per-dance limit)."""
        dancer = _FakeDancer(
            "Solo",
            [Dance("Bronze", "Standard", "Waltz"), Dance("Gold", "Standard", "Waltz")],
        )
        violations = LevelRulesChecker.check(dancer)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].violation_type, "non_consecutive")
        self.assertEqual(violations[0].dance, "Waltz")

    def test_split_across_dances_within_span_no_violation(self):
        """Silver+Gold Waltz/Quickstep and Bronze+Silver Tango/Foxtrot/Viennese
        Waltz: no single dance exceeds 2 levels, and the overall Standard span
        (Bronze through Gold) is exactly 3 levels - right at the limit."""
        dancer = _FakeDancer(
            "Solo",
            [
                Dance("Silver", "Standard", "Waltz"),
                Dance("Gold", "Standard", "Waltz"),
                Dance("Silver", "Standard", "Quickstep"),
                Dance("Gold", "Standard", "Quickstep"),
                Dance("Bronze", "Standard", "Tango"),
                Dance("Silver", "Standard", "Tango"),
                Dance("Bronze", "Standard", "Foxtrot"),
                Dance("Silver", "Standard", "Foxtrot"),
                Dance("Bronze", "Standard", "Viennese Waltz"),
                Dance("Silver", "Standard", "Viennese Waltz"),
            ],
        )
        self.assertEqual(LevelRulesChecker.check(dancer), [])

    def test_span_too_wide_even_with_no_single_dance_violation(self):
        """Newcomer Waltz and Gold Tango: neither dance has more than one
        level registered, but the overall Standard range (Newcomer through
        Gold) is 4 levels wide - too broad even with a per-dance limit of 2."""
        dancer = _FakeDancer(
            "Solo",
            [Dance("Newcomer", "Standard", "Waltz"), Dance("Gold", "Standard", "Tango")],
        )
        violations = LevelRulesChecker.check(dancer)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].violation_type, "span_too_wide")
        self.assertIsNone(violations[0].dance)
        self.assertEqual(violations[0].levels, [0, 3])

    def test_custom_consecutive_level_limit(self):
        dancer = _FakeDancer(
            "Solo",
            [
                Dance("Bronze", "Standard", "Waltz"),
                Dance("Silver", "Standard", "Waltz"),
                Dance("Gold", "Standard", "Waltz"),
            ],
        )
        self.assertEqual(LevelRulesChecker.check(dancer, consecutive_level_limit=3), [])


if __name__ == "__main__":
    unittest.main()
