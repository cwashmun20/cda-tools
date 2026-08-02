"""Tests for cda_core.lib.models.entry module."""

import unittest
from cda_core.lib.models.dance import Dance
from cda_core.lib.models.entry import Entry


class _MockPartnership:
    """Minimal stand-in for Partnership - Entry.__init__ calls partnership.add(self)."""

    def __init__(self):
        self.entries = set()

    def add(self, entry_obj):
        self.entries.add(entry_obj)


class TestEntry(unittest.TestCase):
    """Tests for the Entry class."""

    def test_eq_to_matching_entry(self):
        dance = Dance("Bronze", "Smooth", "Waltz")
        e1 = Entry(dance, _MockPartnership())
        e2 = Entry(dance, _MockPartnership())
        self.assertEqual(e1, e2)

    def test_eq_to_matching_dance(self):
        dance = Dance("Bronze", "Smooth", "Waltz")
        e = Entry(dance, _MockPartnership())
        self.assertEqual(e, dance)

    def test_eq_to_unrelated_type_returns_false(self):
        """Comparing an Entry to an unrelated type should be False, not None."""
        dance = Dance("Bronze", "Smooth", "Waltz")
        e = Entry(dance, _MockPartnership())
        self.assertFalse(e == "Bronze Am. Waltz")
        self.assertNotEqual(e, 42)

    def test_hash_based_on_dance_only(self):
        dance = Dance("Bronze", "Smooth", "Waltz")
        e1 = Entry(dance, _MockPartnership())
        e2 = Entry(dance, _MockPartnership())
        self.assertEqual(hash(e1), hash(e2))


if __name__ == "__main__":
    unittest.main()
