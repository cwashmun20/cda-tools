"""Tests for points_updating.lib.parsing.routing module."""

import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import requests

from points_updating.lib.parsing import ballroom_comp_express, comporganizer, o2cm
from points_updating.lib.parsing.http_client import ThrottledClient
from points_updating.lib.parsing.routing import parse_results_url

_FIXTURES = Path(__file__).parent / "fixtures" / "routing"


def _load_fixture(name: str) -> str:
    with open(_FIXTURES / name, encoding="utf-8") as f:
        return f.read()


class _FakeSession:
    """Maps a url to a canned HTML response body, ignoring params/data."""

    def __init__(self, responses: dict):
        self._responses = responses

    def request(self, method, url, **kwargs):
        if url not in self._responses:
            raise AssertionError(f"Unexpected request: {url}")
        response = requests.Response()
        response.status_code = 200
        response._content = self._responses[url].encode("utf-8")
        response.encoding = "utf-8"
        return response


def _make_client(responses: dict = {}) -> ThrottledClient:
    return ThrottledClient(min_delay_seconds=0, session=_FakeSession(responses))


class TestParseResultsUrl(unittest.TestCase):
    @patch.object(o2cm, "fetch_competition_name", return_value="Claremont Showdown")
    @patch.object(o2cm, "parse_competition", return_value=["sentinel"])
    def test_routes_o2cm_url(self, mock_parse, mock_fetch_name):
        client = _make_client()

        results = parse_results_url(
            "https://results.o2cm.com/event3.asp?event=isc25", date(2025, 11, 14), client
        )

        self.assertEqual(results, ["sentinel"])
        mock_fetch_name.assert_called_once_with("isc25", client)
        mock_parse.assert_called_once_with(
            "isc25", "Claremont Showdown", date(2025, 11, 14), client
        )

    @patch.object(ballroom_comp_express, "fetch_competition_name", return_value="Solar Flare")
    @patch.object(ballroom_comp_express, "parse_competition", return_value=["sentinel"])
    def test_routes_ballroom_comp_express_url(self, mock_parse, mock_fetch_name):
        client = _make_client()

        results = parse_results_url(
            "https://ballroomcompexpress.com/results.php?cid=178", date(2025, 2, 8), client
        )

        self.assertEqual(results, ["sentinel"])
        mock_fetch_name.assert_called_once_with(178, client)
        mock_parse.assert_called_once_with(178, "Solar Flare", date(2025, 2, 8), client)

    @patch.object(comporganizer, "resolve_comp_year_id", return_value=9629)
    @patch.object(comporganizer, "fetch_competition_name", return_value="Cal Poly Mustang Ball")
    @patch.object(comporganizer, "parse_competition", return_value=["sentinel"])
    def test_routes_cbid_danceam_url_to_comporganizer(
        self, mock_parse, mock_fetch_name, mock_resolve
    ):
        """Mustang-Ball-style template: cbid embedded in the results page."""
        url = "https://mustangball.dance.am/pages/results/Default.asp"
        client = _make_client({url: _load_fixture("danceam_page.html")})

        results = parse_results_url(url, date(2026, 2, 7), client)

        self.assertEqual(results, ["sentinel"])
        mock_resolve.assert_called_once_with("688970749df5c", client)
        mock_fetch_name.assert_called_once_with("688970749df5c", client)
        mock_parse.assert_called_once_with(9629, "Cal Poly Mustang Ball", date(2026, 2, 7), client)

    @patch.object(comporganizer, "resolve_comp_year_id_from_host", return_value=9720)
    @patch.object(
        comporganizer, "fetch_competition_name_from_host", return_value="Cardinal Classic"
    )
    @patch.object(comporganizer, "parse_competition", return_value=["sentinel"])
    def test_routes_cbid_less_danceam_url_to_comporganizer(
        self, mock_parse, mock_fetch_name, mock_resolve
    ):
        """Cardinal-Classic-style template: no cbid - resolved by host
        instead, an equally first-class discovery path."""
        url = "https://m-cardinal.dance.am/"
        client = _make_client({url: _load_fixture("danceam_page_no_cbid.html")})

        results = parse_results_url(url, date(2026, 4, 4), client)

        self.assertEqual(results, ["sentinel"])
        mock_resolve.assert_called_once_with("m-cardinal.dance.am", client)
        mock_fetch_name.assert_called_once_with("m-cardinal.dance.am", client)
        mock_parse.assert_called_once_with(9720, "Cardinal Classic", date(2026, 4, 4), client)

    @patch.object(o2cm, "fetch_competition_name")
    @patch.object(o2cm, "parse_competition", return_value=["sentinel"])
    def test_explicit_competition_name_skips_name_fetch(self, mock_parse, mock_fetch_name):
        client = _make_client()

        parse_results_url(
            "https://results.o2cm.com/event3.asp?event=isc25",
            date(2025, 11, 14),
            client,
            competition_name="Overridden Name",
        )

        mock_fetch_name.assert_not_called()
        mock_parse.assert_called_once_with("isc25", "Overridden Name", date(2025, 11, 14), client)

    def test_unrecognized_host_raises(self):
        # Neither dance.am discovery path matches: no cbid embedded in the
        # page, and /shared/comp.php isn't a real config endpoint here (its
        # response fails to parse as JSON, same as a real unrelated host).
        url = "https://example.com/results"
        client = _make_client(
            {
                url: "<html><body>Not a results page</body></html>",
                "https://example.com/shared/comp.php": "<html>404 Not Found</html>",
            }
        )

        with self.assertRaises(ValueError):
            parse_results_url(url, date(2025, 2, 8), client)

    def test_missing_query_param_raises(self):
        client = _make_client()

        with self.assertRaises(ValueError):
            parse_results_url("https://results.o2cm.com/event3.asp", date(2025, 2, 8), client)


if __name__ == "__main__":
    unittest.main()
