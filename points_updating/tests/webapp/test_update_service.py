"""Tests for points_updating.lib.webapp.update_service module."""

import unittest
from datetime import date
from unittest import mock

import numpy as np

from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.webapp import update_service
from points_updating.lib.webapp.update_service import UpdateError, UpdateSuccess, run_update
from utils.lib.api.client import DancerRecord
from utils.lib.models.dance import Dance


def _new_dancer_lookup(first: str, last: str) -> DancerRecord:
    """Every dancer starts fresh at zero points - keeps expected totals
    easy to reason about without a real database."""
    return DancerRecord(
        cda_id=None,
        first=first,
        last=last,
        first_comp_date=None,
        created_date="2026-01-01",
        syllabus_pts=np.zeros((4, 19), dtype=int),
        open_pts=np.zeros((3, 4), dtype=int),
    )


def _existing_dancer_lookup(first: str, last: str) -> DancerRecord:
    """A dancer already in the CDA DB - has a real cda_id."""
    return DancerRecord(
        cda_id=12345,
        first=first,
        last=last,
        first_comp_date=date(2020, 1, 1),
        created_date="2020-01-01",
        syllabus_pts=np.zeros((4, 19), dtype=int),
        open_pts=np.zeros((3, 4), dtype=int),
    )


def _make_result(place: int, num_rounds: int = 2) -> CompetitionResult:
    dance = Dance("Bronze", "Smooth", "Waltz")
    return CompetitionResult(
        dance=dance,
        lead=DancerRef(first="Alex", last="Zephyr"),
        follow=DancerRef(first="Jamie", last="Adams"),
        place=place,
        num_rounds=num_rounds,
        competition_name="Test Classic",
        competition_date=date(2026, 1, 1),
        event_dances=(dance,),
    )


class TestRunUpdate(unittest.TestCase):
    def test_no_urls_returns_error(self):
        result = run_update([], [])

        self.assertIsInstance(result, UpdateError)
        self.assertIn("at least one", result.message.lower())

    def test_invalid_date_returns_error(self):
        result = run_update(["https://example.com"], ["not-a-date"])

        self.assertIsInstance(result, UpdateError)
        self.assertIn("not-a-date", result.message)

    def test_parse_failure_returns_error_with_502(self):
        with mock.patch.object(
            update_service, "parse_results_url", side_effect=ValueError("bad url")
        ):
            result = run_update(["https://example.com"], ["2026-01-01"])

        self.assertIsInstance(result, UpdateError)
        self.assertEqual(result.status_code, 502)
        self.assertIn("bad url", result.message)

    def test_successful_run_produces_all_and_per_dancer_text(self):
        with mock.patch.object(
            update_service, "parse_results_url", return_value=[_make_result(place=1)]
        ):
            result = run_update(["https://example.com"], ["2026-01-01"], lookup=_new_dancer_lookup)

        self.assertIsInstance(result, UpdateSuccess)
        self.assertEqual(result.dancer_names, ["Jamie Adams", "Alex Zephyr"])  # by last name
        self.assertIn("Alex Zephyr", result.all_text)
        self.assertIn("Jamie Adams", result.all_text)
        self.assertIn("Alex Zephyr", result.dancer_text["Alex Zephyr"])
        self.assertNotIn("Jamie Adams", result.dancer_text["Alex Zephyr"])
        self.assertEqual(result.new_dancer_count, 2)  # both dancers are new, per _new_dancer_lookup

    def test_new_dancer_count_excludes_dancers_already_in_the_db(self):
        with mock.patch.object(
            update_service, "parse_results_url", return_value=[_make_result(place=1)]
        ):
            result = run_update(
                ["https://example.com"], ["2026-01-01"], lookup=_existing_dancer_lookup
            )

        self.assertEqual(result.new_dancer_count, 0)

    def test_new_dancer_count_only_counts_the_dancers_missing_from_the_db(self):
        def _mixed_lookup(first: str, last: str) -> DancerRecord:
            # Only the lead ("Alex Zephyr") is new - the follow is already
            # in the DB - so this exercises a genuine partial count rather
            # than the all-new/all-existing extremes above.
            if first == "Alex":
                return _new_dancer_lookup(first, last)
            return _existing_dancer_lookup(first, last)

        with mock.patch.object(
            update_service, "parse_results_url", return_value=[_make_result(place=1)]
        ):
            result = run_update(["https://example.com"], ["2026-01-01"], lookup=_mixed_lookup)

        self.assertEqual(result.new_dancer_count, 1)

    def test_multiple_urls_paired_with_dates_in_order(self):
        calls = []

        def _fake_parse(url, comp_date, client):
            calls.append((url, comp_date))
            return [_make_result(place=1)]

        with mock.patch.object(update_service, "parse_results_url", side_effect=_fake_parse):
            run_update(
                ["https://a.example.com", "https://b.example.com"],
                ["2026-01-01", "2026-02-01"],
                lookup=_new_dancer_lookup,
            )

        self.assertEqual(
            calls,
            [
                ("https://a.example.com", date(2026, 1, 1)),
                ("https://b.example.com", date(2026, 2, 1)),
            ],
        )


if __name__ == "__main__":
    unittest.main()
