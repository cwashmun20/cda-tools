"""URL-based results-source routing for points_updating.

Routes a competition's results-page URL to the matching source parser
(O2CM, Ballroom Comp Express, or CompOrganizer/dance.am), determined from
the URL's host. A dance.am page carries no identifier in the URL itself, so
that source is the fallback - and CompOrganizer itself serves dance.am
results through (at least) two distinct front-end templates:

- Mustang-Ball-style: the results page embeds a `cbid` callback token
  (`var cbid = "...";`), resolved to a Comp_Year_ID via callback-comps.
- Cardinal-Classic-style: no cbid at all - the school's dance.am subdomain
  itself resolves directly to a Comp_Year_ID via a `/shared/comp.php`
  config endpoint on that subdomain.

See points_updating/lib/parsing/comporganizer.py's module docstring for
how each is confirmed against real competition data.
"""

import re
from datetime import date
from typing import Optional
from urllib.parse import parse_qs, urlparse

import requests

from points_updating.lib.models.result import CompetitionResult
from points_updating.lib.parsing import ballroom_comp_express, comporganizer, o2cm
from points_updating.lib.parsing.http_client import ThrottledClient

_O2CM_HOST = "results.o2cm.com"
_BALLROOM_COMP_EXPRESS_HOST = "ballroomcompexpress.com"

_CBID_RE = re.compile(r'var cbid = "([^"]+)"')


def parse_results_url(
    url: str,
    competition_date: date,
    client: ThrottledClient,
    competition_name: Optional[str] = None,
) -> list[CompetitionResult]:
    """Fetches and parses a competition's results from whichever of the
    three supported sources the URL points to.

    Args:
        url: A results-page URL, e.g.
            `https://results.o2cm.com/event3.asp?event=isc25`,
            `https://ballroomcompexpress.com/results.php?cid=178`, or a
            school's dance.am results page.
        competition_date: The date the competition was held.
        client: The HTTP client to fetch with.
        competition_name: Overrides the name recovered from the source
            itself, if given.
    Returns:
        One CompetitionResult per (couple, dance) across the competition.
    Raises:
        ValueError: if the URL doesn't match any supported source.
    """
    host = urlparse(url).hostname or ""

    if host == _O2CM_HOST:
        comp_id = _query_param(url, "event")
        name = competition_name or o2cm.fetch_competition_name(comp_id, client)
        return o2cm.parse_competition(comp_id, name, competition_date, client)

    if host == _BALLROOM_COMP_EXPRESS_HOST:
        cid = int(_query_param(url, "cid"))
        name = competition_name or ballroom_comp_express.fetch_competition_name(cid, client)
        return ballroom_comp_express.parse_competition(cid, name, competition_date, client)

    response = client.get(url)
    response.raise_for_status()
    cbid_match = _CBID_RE.search(response.text)
    if cbid_match is not None:
        cbid = cbid_match.group(1)
        comp_year_id = comporganizer.resolve_comp_year_id(cbid, client)
        name = competition_name or comporganizer.fetch_competition_name(cbid, client)
        return comporganizer.parse_competition(comp_year_id, name, competition_date, client)

    try:
        comp_year_id = comporganizer.resolve_comp_year_id_from_host(host, client)
        name = competition_name or comporganizer.fetch_competition_name_from_host(host, client)
    except (requests.RequestException, KeyError):
        raise ValueError(
            f"Could not find a CompOrganizer results page at {url!r}. Neither "
            "dance.am template this source supports matched: no `cbid` token is "
            f"embedded in the page, and {host!r} doesn't expose a "
            "/shared/comp.php config endpoint either - navigate to the "
            "competition's actual results page in a browser (usually reached "
            'via a "Results" link) and use that URL instead.'
        ) from None
    return comporganizer.parse_competition(comp_year_id, name, competition_date, client)


def _query_param(url: str, name: str) -> str:
    values = parse_qs(urlparse(url).query).get(name)
    if not values:
        raise ValueError(f"URL {url!r} is missing required query parameter {name!r}")
    return values[0]
