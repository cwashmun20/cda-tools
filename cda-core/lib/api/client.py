"""CDA points database API client.

Provides typed data structures and functions for fetching dancer information
from the CDA points database.
"""

import datetime
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pytz
import requests

import api.config as config
import constants

# JSON field names from the CDA API response for indexing into fairlevelPoints
SYLLABUS_KEYS = ['newcomer_points', 'bronze_points', 'silver_points', 'gold_points']
OPEN_KEYS = ['novice_points', 'prechamp_points', 'champ_points']


@dataclass
class DancerRecord:
    """Typed representation of a dancer record from the CDA points database.

    This replaces the raw dictionary returned by the original lookup_dancer function.
    """
    cda_id: Optional[int]
    first: str
    last: str
    first_comp_date: Optional[datetime.date]
    created_date: str
    syllabus_pts: np.ndarray
    open_pts: np.ndarray


def _build_empty_record(first: str, last: str) -> DancerRecord:
    """Build a DancerRecord for a dancer not yet in the database."""
    utc_dt = datetime.datetime.now(pytz.utc)
    loc_dt = utc_dt.astimezone(pytz.timezone('US/Pacific'))
    created_dt = loc_dt.strftime('%Y-%m-%dT%H:%M:%S%z')
    created_dt = created_dt[:-2] + ':' + created_dt[-2:]

    return DancerRecord(
        cda_id=None,
        first=first,
        last=last,
        first_comp_date=None,
        created_date=created_dt,
        syllabus_pts=np.zeros((4, 19), dtype=int),
        open_pts=np.zeros((3, 4), dtype=int),
    )


def _parse_points(profile_points) -> tuple[np.ndarray, np.ndarray]:
    """Parse syllabus and open points from the API response's fairlevelPoints field."""
    if profile_points == False:
        return np.zeros((4, 19), dtype=int), np.zeros((3, 4), dtype=int)

    syllabus_pts = [[int(pt) for pt in profile_points[key][1:-1].split(',')]
                    for key in SYLLABUS_KEYS]
    open_pts = [[int(pt) for pt in profile_points[key][1:-1].split(',')]
                for key in OPEN_KEYS]
    return np.array(syllabus_pts), np.array(open_pts)


def lookup_dancer(first: str, last: str) -> DancerRecord:
    """Fetches all relevant data from the CDA points database for a dancer.

    Args:
        first: The dancer's first name.
        last: The dancer's last name.
    Returns:
        A DancerRecord with the dancer's information. For dancers not in the
        database, cda_id and first_comp_date will be None and points will be zeros.
    """
    HEADER = {"x-api-key": config.API_KEY}
    parameters = {"firstName": first,
                  "lastName": last}
    result = requests.get("https://collegiatedancesport.org/db/namematch.php",
                          headers=HEADER, params=parameters).json()

    if not result['success']:
        return _build_empty_record(first, last)

    profile = result['competitor']
    profile_points = profile['fairlevelPoints']

    yr, m, d = [int(x) for x in profile['firstCompetitionDate'].split('-')]
    first_comp_date = datetime.date(yr, m, d)

    syllabus_pts, open_pts = _parse_points(profile_points)

    return DancerRecord(
        cda_id=profile['cdaId'],
        first=profile['firstName'],
        last=profile['lastName'],
        first_comp_date=first_comp_date,
        created_date=profile['dateCreated'],
        syllabus_pts=syllabus_pts,
        open_pts=open_pts,
    )