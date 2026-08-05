"""Tests for points_updating.lib.models.result module."""

import unittest
from datetime import date

from cda_core.lib.models.dance import Dance
from points_updating.lib.models.result import CompetitionResult, DancerRef


class TestDancerRef(unittest.TestCase):
    """Tests for the DancerRef class."""

    def test_full_name(self):
        ref = DancerRef(first="Jane", last="Doe")
        self.assertEqual(ref.full_name, "Jane Doe")


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
