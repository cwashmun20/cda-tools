"""Tests for the points-updater web UI's HTML routes.

Mocks update_service.run_update() at the route boundary, matching
routing.py's own tests' approach of mocking at module boundaries rather
than going all the way through a real fetch/parse/score pipeline - that
pipeline is already covered by the parsing and engine test suites.
"""

import unittest
from unittest import mock

from points_updating.lib.webapp import routes
from points_updating.lib.webapp.app import create_app
from points_updating.lib.webapp.update_service import UpdateError, UpdateSuccess


class TestIndexRoute(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_index_returns_form(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="url"', response.data)
        self.assertIn(b'name="date"', response.data)
        # No results yet on a bare GET, so there's no results tab to show.
        self.assertNotIn(b'id="results-panel"', response.data)
        # Dry run defaults to true
        self.assertIn(b'name="dry_run" id="dry-run-checkbox" checked', response.data)

    def test_post_blank_url_shows_friendly_error(self):
        response = self.client.post("/", data={"url": [""], "date": [""]})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"At least one results link is required", response.data)

    def test_post_success_shows_results_tab(self):
        success = UpdateSuccess(
            dancer_names=["Jamie Adams", "Alex Zephyr"],
            all_text="=== Alex Zephyr ===\n...\n=== Jamie Adams ===\n...",
            dancer_text={
                "Alex Zephyr": "=== Alex Zephyr ===\n...",
                "Jamie Adams": "=== Jamie Adams ===\n...",
            },
            new_dancer_count=1,
        )
        with mock.patch.object(routes, "run_update", return_value=success) as mock_run:
            response = self.client.post(
                "/",
                data={"url": ["https://example.com"], "date": ["2026-01-01"], "dry_run": "on"},
            )

        mock_run.assert_called_once_with(["https://example.com"], ["2026-01-01"], dry_run=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="results-panel"', response.data)
        self.assertIn(b"Jamie Adams", response.data)
        self.assertIn(b"Show all updates", response.data)
        self.assertIn(b"1 new dancer", response.data)
        self.assertNotIn(b"1 new dancers", response.data)  # singular, not "1 dancers"

    def test_new_dancer_count_pluralizes_for_zero_and_multiple(self):
        success = UpdateSuccess(dancer_names=[], all_text="", dancer_text={}, new_dancer_count=3)
        with mock.patch.object(routes, "run_update", return_value=success):
            response = self.client.post(
                "/",
                data={"url": ["https://example.com"], "date": ["2026-01-01"], "dry_run": "on"},
            )

        self.assertIn(b"3 new dancers", response.data)

    def test_post_update_error_shows_message_not_results(self):
        with mock.patch.object(
            routes, "run_update", return_value=UpdateError("Failed to fetch/parse it", 502)
        ):
            response = self.client.post(
                "/",
                data={"url": ["https://example.com"], "date": ["2026-01-01"], "dry_run": "on"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Failed to fetch/parse it", response.data)
        self.assertNotIn(b'id="results-panel"', response.data)

    def test_multiple_link_rows_forwarded_in_order(self):
        with mock.patch.object(
            routes,
            "run_update",
            return_value=UpdateSuccess(
                dancer_names=[], all_text="", dancer_text={}, new_dancer_count=0
            ),
        ) as mock_run:
            self.client.post(
                "/",
                data={
                    "url": ["https://a.example.com", "https://b.example.com"],
                    "date": ["2026-01-01", "2026-02-01"],
                    "dry_run": "on",
                },
            )

        mock_run.assert_called_once_with(
            ["https://a.example.com", "https://b.example.com"],
            ["2026-01-01", "2026-02-01"],
            dry_run=True,
        )

    def test_unchecked_dry_run_is_forwarded_as_false(self):
        with mock.patch.object(
            routes,
            "run_update",
            return_value=UpdateError("Live updates aren't supported yet."),
        ) as mock_run:
            response = self.client.post(
                "/", data={"url": ["https://example.com"], "date": ["2026-01-01"]}
            )

        mock_run.assert_called_once_with(["https://example.com"], ["2026-01-01"], dry_run=False)
        self.assertIn(b"Live updates aren&#39;t supported yet.", response.data)

    def test_unchecked_dry_run_preserved_on_error_rerender(self):
        response = self.client.post("/", data={"url": [""], "date": [""]})

        self.assertNotIn(b'name="dry_run" id="dry-run-checkbox" checked', response.data)
        self.assertIn(b'name="dry_run" id="dry-run-checkbox" ', response.data)


if __name__ == "__main__":
    unittest.main()
