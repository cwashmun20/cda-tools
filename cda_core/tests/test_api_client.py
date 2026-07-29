"""Tests for cda_core.lib.api.client module."""

import unittest
from unittest.mock import patch, MagicMock
import requests

from cda_core.lib.api.client import lookup_dancer, DancerLookupError


def _mock_response(json_data, status_ok=True):
    """Build a MagicMock standing in for a requests.Response."""
    response = MagicMock()
    response.json.return_value = json_data
    if status_ok:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    return response


class TestLookupDancer(unittest.TestCase):
    """Tests for lookup_dancer()."""

    @patch("cda_core.lib.api.client.requests.get")
    def test_success(self, mock_get):
        mock_get.return_value = _mock_response(
            {
                "success": True,
                "competitor": {
                    "cdaId": 42,
                    "firstName": "Priya",
                    "lastName": "Patel",
                    "firstCompetitionDate": "2020-01-15",
                    "dateCreated": "2020-01-15T00:00:00-08:00",
                    "fairlevelPoints": {
                        "newcomer_points": "[0,0,0,0,0]",
                        "bronze_points": "[0,0,0,0,0]",
                        "silver_points": "[0,0,0,0,0]",
                        "gold_points": "[0,0,0,0,0]",
                        "novice_points": "[0,0,0,0]",
                        "prechamp_points": "[0,0,0,0]",
                        "champ_points": "[0,0,0,0]",
                    },
                },
            }
        )
        record = lookup_dancer("Priya", "Patel")
        self.assertEqual(record.cda_id, 42)
        self.assertEqual(record.first, "Priya")
        self.assertEqual(record.last, "Patel")

    @patch("cda_core.lib.api.client.requests.get")
    def test_not_found_returns_empty_record(self, mock_get):
        mock_get.return_value = _mock_response({"success": False})
        record = lookup_dancer("New", "Comer")
        self.assertIsNone(record.cda_id)
        self.assertIsNone(record.first_comp_date)

    @patch("cda_core.lib.api.client.requests.get")
    def test_network_error_raises_lookup_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("no route to host")
        with self.assertRaises(DancerLookupError):
            lookup_dancer("Alex", "Rivera")

    @patch("cda_core.lib.api.client.requests.get")
    def test_http_error_raises_lookup_error(self, mock_get):
        mock_get.return_value = _mock_response({}, status_ok=False)
        with self.assertRaises(DancerLookupError):
            lookup_dancer("Alex", "Rivera")

    @patch("cda_core.lib.api.client.requests.get")
    def test_malformed_json_raises_lookup_error(self, mock_get):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("Expecting value: line 1 column 1")
        mock_get.return_value = response
        with self.assertRaises(DancerLookupError):
            lookup_dancer("Alex", "Rivera")

    @patch("cda_core.lib.api.client.requests.get")
    def test_unexpected_shape_raises_lookup_error(self, mock_get):
        # "success": True but missing the "competitor" key entirely.
        mock_get.return_value = _mock_response({"success": True})
        with self.assertRaises(DancerLookupError):
            lookup_dancer("Alex", "Rivera")


if __name__ == "__main__":
    unittest.main()
