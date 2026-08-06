"""Tests for points_updating.lib.parsing.http_client module."""

import tempfile
import unittest
from pathlib import Path

import requests

from points_updating.lib.parsing.http_client import ThrottledClient


class _FakeSession:
    """Records every request() call and returns canned responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self._responses.pop(0)


class _FakeClock:
    """A controllable clock/sleep pair for delay/backoff tests."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _make_response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    return response


class TestThrottledClientDelay(unittest.TestCase):
    """Tests for the minimum-delay-between-requests behavior."""

    def test_enforces_minimum_delay_between_requests(self):
        clock = _FakeClock()
        session = _FakeSession([_make_response(200), _make_response(200)])
        client = ThrottledClient(
            min_delay_seconds=2.0, session=session, sleep=clock.sleep, clock=clock.clock
        )

        client.get("http://example.com/a")
        client.get("http://example.com/b")

        # No delay before the first call; the full delay before the second.
        self.assertEqual(clock.sleeps, [2.0])

    def test_no_delay_if_enough_time_already_elapsed(self):
        clock = _FakeClock()
        session = _FakeSession([_make_response(200), _make_response(200)])
        client = ThrottledClient(
            min_delay_seconds=2.0, session=session, sleep=clock.sleep, clock=clock.clock
        )

        client.get("http://example.com/a")
        clock.now += 5.0  # plenty of time passes outside the client's control
        client.get("http://example.com/b")

        self.assertEqual(clock.sleeps, [])


class TestThrottledClientBackoff(unittest.TestCase):
    """Tests for exponential backoff-and-retry on throttle responses."""

    def test_retries_on_throttle_response_with_growing_delay(self):
        clock = _FakeClock()
        session = _FakeSession([_make_response(403), _make_response(403), _make_response(200)])
        client = ThrottledClient(
            min_delay_seconds=0,
            max_retries=5,
            backoff_base_seconds=1.0,
            session=session,
            sleep=clock.sleep,
            clock=clock.clock,
        )

        response = client.get("http://example.com/a")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(clock.sleeps, [1.0, 2.0])  # backoff doubles each attempt

    def test_gives_up_after_max_retries(self):
        clock = _FakeClock()
        session = _FakeSession([_make_response(403)] * 4)  # 1 initial + 3 retries
        client = ThrottledClient(
            min_delay_seconds=0,
            max_retries=3,
            backoff_base_seconds=1.0,
            session=session,
            sleep=clock.sleep,
            clock=clock.clock,
        )

        response = client.get("http://example.com/a")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(session.calls), 4)

    def test_success_does_not_trigger_backoff(self):
        clock = _FakeClock()
        session = _FakeSession([_make_response(200)])
        client = ThrottledClient(
            min_delay_seconds=0, session=session, sleep=clock.sleep, clock=clock.clock
        )

        client.get("http://example.com/a")

        self.assertEqual(clock.sleeps, [])
        self.assertEqual(len(session.calls), 1)


class TestThrottledClientCaching(unittest.TestCase):
    """Tests for optional on-disk response caching."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_cache_hit_skips_transport_call(self):
        clock = _FakeClock()
        session = _FakeSession([_make_response(200)])
        client = ThrottledClient(
            min_delay_seconds=0,
            session=session,
            cache_dir=self.cache_dir,
            sleep=clock.sleep,
            clock=clock.clock,
        )

        first = client.get("http://example.com/a")
        second = client.get("http://example.com/a")

        self.assertEqual(len(session.calls), 1)
        self.assertEqual(first.status_code, second.status_code)

    def test_cache_miss_for_different_url_hits_transport_again(self):
        clock = _FakeClock()
        session = _FakeSession([_make_response(200), _make_response(200)])
        client = ThrottledClient(
            min_delay_seconds=0,
            session=session,
            cache_dir=self.cache_dir,
            sleep=clock.sleep,
            clock=clock.clock,
        )

        client.get("http://example.com/a")
        client.get("http://example.com/b")

        self.assertEqual(len(session.calls), 2)

    def test_no_cache_dir_never_caches(self):
        clock = _FakeClock()
        session = _FakeSession([_make_response(200), _make_response(200)])
        client = ThrottledClient(
            min_delay_seconds=0, session=session, sleep=clock.sleep, clock=clock.clock
        )

        client.get("http://example.com/a")
        client.get("http://example.com/a")

        self.assertEqual(len(session.calls), 2)

    def test_throttled_response_not_cached(self):
        clock = _FakeClock()
        session = _FakeSession([_make_response(403), _make_response(403)])
        client = ThrottledClient(
            min_delay_seconds=0,
            max_retries=0,
            session=session,
            cache_dir=self.cache_dir,
            sleep=clock.sleep,
            clock=clock.clock,
        )

        client.get("http://example.com/a")
        client.get("http://example.com/a")

        # Neither the first (throttled, unretried) response nor a later
        # identical request should have been cached - both hit the transport.
        self.assertEqual(len(session.calls), 2)


if __name__ == "__main__":
    unittest.main()
