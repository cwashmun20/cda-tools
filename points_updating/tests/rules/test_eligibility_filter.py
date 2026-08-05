"""Tests for points_updating.lib.rules.eligibility_filter module."""

import unittest
from datetime import date

from cda_core.lib.models.dance import Dance
from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.rules.eligibility_filter import filter_points_eligible

_LEAD = DancerRef(first="Jane", last="Doe")
_FOLLOW = DancerRef(first="John", last="Smith")


def _make_result(level: str, style: str, dance_name: str) -> CompetitionResult:
    dance = Dance(level, style, dance_name)
    return CompetitionResult(
        dance=dance,
        lead=_LEAD,
        follow=_FOLLOW,
        place=1,
        num_rounds=2,
        competition_name="Test Classic",
        competition_date=date(2025, 10, 4),
        event_dances=(dance,),
    )


class TestFilterPointsEligible(unittest.TestCase):
    """Tests for filter_points_eligible."""

    def test_keeps_every_points_eligible_style(self):
        results = [
            _make_result("Gold", "Standard", "Waltz"),
            _make_result("Gold", "Smooth", "Waltz"),
            _make_result("Gold", "Latin", "Cha Cha"),
            _make_result("Gold", "Rhythm", "Cha Cha"),
        ]

        filtered = filter_points_eligible(results)

        self.assertEqual(len(filtered), len(results))
        for result in results:
            self.assertIn(result, filtered)

    def test_drops_nightclub_results(self):
        results = [
            _make_result("Gold", "Standard", "Waltz"),
            _make_result("Beginner", "Nightclub", "Salsa"),
        ]

        filtered = filter_points_eligible(results)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].dance.style, "Standard")

    def test_drops_rookie_vet_results(self):
        """Rookie/Vet events are danced in a points-eligible style (e.g.
        Smooth), but the Rookie Lead/Follow level itself doesn't earn
        points."""
        results = [
            _make_result("Gold", "Smooth", "Waltz"),
            _make_result("Rookie Leader", "Smooth", "Waltz"),
            _make_result("Rookie Follower", "Latin", "Cha Cha"),
        ]

        filtered = filter_points_eligible(results)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].dance.level, "Gold")

    def test_empty_input_returns_empty(self):
        self.assertEqual(filter_points_eligible([]), [])


if __name__ == "__main__":
    unittest.main()
