"""Tests for the entry-checker web UI's HTML and JSON routes.

Uses Flask's test client and patches Dancer.from_api so no real network call
happens - the same mocking approach entry_checking/tests/test_entry_checker.py
uses via Dancer.from_data(), just applied at the from_api() call site since
these routes build their own Competition internally.
"""

import datetime
import io
import unittest
from unittest import mock

import numpy as np

from cda_core.lib.api.client import DancerLookupError, DancerRecord
from cda_core.lib.models.dancer import Dancer
from entry_checking.lib.webapp.app import create_app

_VALID_CSV = (
    b"Style,Dance,Skill,Lead First,Lead Last,Follow First,Follow Last\n"
    b"Smooth,Waltz,Newcomer,Baris,Varol,Denise,Machin\n"
)

_MISSING_COLUMN_CSV = (
    b"Style,Dance,Lead First,Lead Last,Follow First,Follow Last\n"
    b"Smooth,Waltz,Baris,Varol,Denise,Machin\n"
)

_VALID_FORM_FIELDS = {
    "comp_name": "Test Comp",
    "comp_date": "2026-06-01",
    "rv_ruleset": "newcomer",
    "rookie_max_level": "Bronze",
    "consecutive_level_limit": "2",
}


def _mock_dancer(curr_comp_date, first, last):
    """Build an experienced (>1yr), zero-points Dancer without hitting the API."""
    record = DancerRecord(
        cda_id=1,
        first=first,
        last=last,
        first_comp_date=datetime.date(2020, 1, 1),
        created_date="2020-01-01",
        syllabus_pts=np.zeros((4, 19), dtype=int),
        open_pts=np.zeros((3, 4), dtype=int),
    )
    return Dancer.from_data(curr_comp_date, record)


def _post_form(client, path, fields, csv_bytes, filename="entries.csv"):
    data = dict(fields)
    data["entries_csv"] = (io.BytesIO(csv_bytes), filename)
    return client.post(path, data=data, content_type="multipart/form-data")


class TestIndexRoute(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_index_returns_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="comp_name"', response.data)
        self.assertIn(b'name="entries_csv"', response.data)
        # No results yet on a bare GET, so there's nothing to download.
        self.assertNotIn(b'id="download-results-btn"', response.data)

    def test_post_valid_csv_returns_report(self):
        with mock.patch.object(Dancer, "from_api", side_effect=_mock_dancer):
            response = _post_form(self.client, "/", _VALID_FORM_FIELDS, _VALID_CSV)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"NEWCOMER VIOLATION", response.data)
        self.assertIn(b"Baris Varol", response.data)
        self.assertIn(b'id="download-results-btn"', response.data)

    def test_post_missing_columns_shows_friendly_error(self):
        with mock.patch.object(Dancer, "from_api", side_effect=_mock_dancer):
            response = _post_form(self.client, "/", _VALID_FORM_FIELDS, _MISSING_COLUMN_CSV)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Missing required columns", response.data)
        self.assertNotIn(b'id="download-results-btn"', response.data)

    def test_dancer_lookup_error_shows_friendly_message(self):
        with mock.patch.object(Dancer, "from_api", side_effect=DancerLookupError("boom")):
            response = _post_form(self.client, "/", _VALID_FORM_FIELDS, _VALID_CSV)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"boom", response.data)


class TestApiCheckRoute(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_api_check_returns_json(self):
        with mock.patch.object(Dancer, "from_api", side_effect=_mock_dancer):
            response = _post_form(self.client, "/api/check", _VALID_FORM_FIELDS, _VALID_CSV)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(len(body["groups"]), 1)
        subject_name, messages = body["groups"][0]["subject_name"], body["groups"][0]["messages"]
        self.assertEqual(subject_name, "Baris Varol & Denise Machin")
        self.assertTrue(any("NEWCOMER VIOLATION" in m for m in messages))

    def test_api_check_bad_ruleset_returns_400(self):
        fields = dict(_VALID_FORM_FIELDS, rv_ruleset="bogus")
        response = _post_form(self.client, "/api/check", fields, _VALID_CSV)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_api_check_dancer_lookup_error_returns_502(self):
        with mock.patch.object(Dancer, "from_api", side_effect=DancerLookupError("boom")):
            response = _post_form(self.client, "/api/check", _VALID_FORM_FIELDS, _VALID_CSV)

        self.assertEqual(response.status_code, 502)
        self.assertIn("boom", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
