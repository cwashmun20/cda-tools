"""Tests for points_updating.lib.models.result module."""

import unittest
from datetime import date

from points_updating.lib.models.result import CompetitionResult, DancerRef
from utils.lib.models.dance import Dance


class TestDancerRef(unittest.TestCase):
    """Tests for the DancerRef class."""

    def test_full_name(self):
        ref = DancerRef(first="Jane", last="Doe")
        self.assertEqual(ref.full_name, "Jane Doe")

    def test_lowercase_first_letter_is_capitalized(self):
        ref = DancerRef(first="jane", last="doe")
        self.assertEqual(ref.first, "Jane")
        self.assertEqual(ref.last, "Doe")
        self.assertEqual(ref.full_name, "Jane Doe")

    def test_interior_capitalization_is_preserved(self):
        ref = DancerRef(first="McDonald", last="DiCaprio")
        self.assertEqual(ref.first, "McDonald")
        self.assertEqual(ref.last, "DiCaprio")

    def test_already_capitalized_name_is_unchanged(self):
        ref = DancerRef(first="Jane", last="Doe")
        self.assertEqual(ref.first, "Jane")
        self.assertEqual(ref.last, "Doe")

    def test_only_last_name_lowercase_is_fixed_independently(self):
        ref = DancerRef(first="Jane", last="doe")
        self.assertEqual(ref.first, "Jane")
        self.assertEqual(ref.last, "Doe")

    def test_only_first_name_lowercase_is_fixed_independently(self):
        ref = DancerRef(first="jane", last="Doe")
        self.assertEqual(ref.first, "Jane")
        self.assertEqual(ref.last, "Doe")

    def test_empty_name_does_not_raise(self):
        ref = DancerRef(first="", last="doe")
        self.assertEqual(ref.first, "")
        self.assertEqual(ref.last, "Doe")


class TestCompetitionResult(unittest.TestCase):
    """Tests for the CompetitionResult class."""

    def test_construction_with_syllabus_dance(self):
        result = CompetitionResult(
            dance=Dance("Gold", "Smooth", "Tango"),
            lead=DancerRef(first="Jane", last="Doe"),
            follow=DancerRef(first="John", last="Smith"),
            place=2,
            num_rounds=2,
            competition_name="Test Classic",
            competition_date=date(2025, 10, 4),
            event_dances=(Dance("Gold", "Smooth", "Tango"),),
        )
        self.assertEqual(str(result.dance), "Gold Am. Tango")
        self.assertEqual(result.lead.full_name, "Jane Doe")
        self.assertEqual(result.place, 2)

    def test_construction_with_open_dance(self):
        event_dances = (
            Dance("Novice", "Smooth", "Waltz"),
            Dance("Novice", "Smooth", "Tango"),
            Dance("Novice", "Smooth", "Foxtrot"),
        )
        result = CompetitionResult(
            dance=Dance("Novice", "Smooth", "Waltz"),
            lead=DancerRef(first="Jane", last="Doe"),
            follow=DancerRef(first="John", last="Smith"),
            place=1,
            num_rounds=3,
            competition_name="Test Classic",
            competition_date=date(2025, 10, 4),
            event_dances=event_dances,
        )
        self.assertEqual(result.event_dances, event_dances)
        self.assertEqual(result.num_rounds, 3)


if __name__ == "__main__":
    unittest.main()
