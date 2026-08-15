"""CompOrganizer results parsing for points_updating.

CompOrganizer/NDCA Premier is a shared third-party backend behind
school-branded dance.am results pages, not dance.am's own backend.
Confirmed against two real 2026 CDA competitions, each using a different
dance.am front-end template over the same backend/data schema:

- Cal Poly Mustang Ball (mustangball.dance.am): embeds a callback token
  (`var cbid = "...";`), resolved to a Comp_Year_ID via callback-comps -
  see resolve_comp_year_id()/fetch_competition_name().
- Stanford Cardinal Classic (m-cardinal.dance.am): no cbid - its
  Comp_Year_ID resolves from a `/shared/comp.php` endpoint on the
  school's own subdomain instead - see
  resolve_comp_year_id_from_host()/fetch_competition_name_from_host().

Both templates pull from the same ndcapremier.com feed API once a
Comp_Year_ID is known, confirmed by diffing real event-list/event-results
responses from both competitions against the same schema.
"""

import math
from datetime import date

from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.parsing.http_client import ThrottledClient
from utils.lib.constants import SYLLABUS_LEVELS, Style
from utils.lib.models.dance import Dance, convert_dance, convert_level

_CALLBACK_COMPS_URL = "https://comporganizer.com/feed/callback-comps/"
_RESULTS_URL = "https://ndcapremier.com/feed/results/"
_COMP_PHP_PATH = "/shared/comp.php"

# The longest level phrase CompOrganizer writes ("R/V Rookie Lead"/"R/V
# Rookie Follow") is 3 words.
_MAX_LEVEL_WORDS = 3


def resolve_comp_year_id(cbid: str, client: ThrottledClient) -> int:
    """Resolves a school's dance.am callback token to CompOrganizer's own
    competition-year identifier.

    Args:
        cbid: The callback token embedded in a dance.am results page (e.g.
            `var cbid = "688970749df5c";`).
        client: The HTTP client to fetch with.
    Returns:
        CompOrganizer's `Comp_Year_ID` for this competition.
    """
    return _fetch_comp_info_from_cbid(cbid, client)["Comp_Year_ID"]


def fetch_competition_name(cbid: str, client: ThrottledClient) -> str:
    """Returns the competition's own name for a school's dance.am callback
    token."""
    return _fetch_comp_info_from_cbid(cbid, client)["Full_Name"]


def _fetch_comp_info_from_cbid(cbid: str, client: ThrottledClient) -> dict:
    response = client.get(_CALLBACK_COMPS_URL, params={"cbid": cbid})
    response.raise_for_status()
    return response.json()["Comps"][0]


def resolve_comp_year_id_from_host(host: str, client: ThrottledClient) -> int:
    """Resolves a dance.am subdomain directly to CompOrganizer's own
    competition-year identifier, for the template family that carries no
    cbid token at all (e.g. Stanford's Cardinal Classic).

    Args:
        host: The dance.am subdomain (e.g. "m-cardinal.dance.am").
        client: The HTTP client to fetch with.
    Returns:
        CompOrganizer's `Comp_Year_ID` for this competition.
    """
    return _fetch_comp_info_from_host(host, client)["Comp_Year_ID"]


def fetch_competition_name_from_host(host: str, client: ThrottledClient) -> str:
    """Returns the competition's own name for a dance.am subdomain, for the
    cbid-less template family - see resolve_comp_year_id_from_host()."""
    return _fetch_comp_info_from_host(host, client)["Competition_Name"]


def _fetch_comp_info_from_host(host: str, client: ThrottledClient) -> dict:
    response = client.get(f"https://{host}{_COMP_PHP_PATH}")
    response.raise_for_status()
    return response.json()


def fetch_event_list(comp_year_id: int, client: ThrottledClient) -> list[tuple[int, str]]:
    """Returns every event in a competition as (event_id, name) pairs."""
    response = client.get(_RESULTS_URL, params={"cyi": comp_year_id, "list": "events"})
    response.raise_for_status()
    events = response.json()["Result"]["Events"]
    return [(event["ID"], event["Name"]) for event in events]


def fetch_event_results(comp_year_id: int, event_id: int, client: ThrottledClient) -> dict:
    """Returns one event's full results as CompOrganizer's raw JSON dict."""
    response = client.get(_RESULTS_URL, params={"cyi": comp_year_id, "event": event_id})
    response.raise_for_status()
    return response.json()


def parse_competition(
    comp_year_id: int, competition_name: str, competition_date: date, client: ThrottledClient
) -> list[CompetitionResult]:
    """Fetches and parses every couple event in a CompOrganizer-backed
    competition.

    Args:
        comp_year_id: CompOrganizer's own competition-year identifier,
            already resolved by the caller (see resolve_comp_year_id()/
            resolve_comp_year_id_from_host(), depending on which dance.am
            template family the results page uses).
        competition_name: The competition's name.
        competition_date: The date the competition was held.
        client: The HTTP client to fetch with.
    Returns:
        One CompetitionResult per (couple, event) across every couple event
        in the competition. Non-couple events (Jack & Jill, team matches,
        etc.) are skipped here, not raised on - see _parse_event for the
        single-event contract, which does raise for those.
    """
    results = []
    for event_id, _ in fetch_event_list(comp_year_id, client):
        event = fetch_event_results(comp_year_id, event_id, client)["Result"]["Event"]
        if event["Type"] != "Couple":
            continue
        results.extend(_parse_event(event, competition_name, competition_date))
    return results


def _parse_event(
    event: dict, competition_name: str, competition_date: date
) -> list[CompetitionResult]:
    """Parses one already-fetched event's JSON into CompetitionResults, one
    per couple regardless of how many dances the event covers.

    Placement comes from the Summary (combined across dances), except for
    a single-dance event with only one couple entered - Summary Result is
    null there, so we fall back to the dance's own Result. Fractional Results
    (ties) get floored - "1224" ranking. Every couple dances every dance in
    a multi-dance combo, so dances_json[0]'s Competitors list alone is
    enough to enumerate them.
    """
    if event["Type"] != "Couple":
        raise NotImplementedError(f"Unsupported CompOrganizer event type: {event['Type']!r}")

    level = _extract_level(event["Name"])
    rounds = event["Rounds"]
    num_rounds = len(rounds)
    final_round = rounds[-1]
    dances_json = final_round["Dances"]

    if len(dances_json) == 1:
        placements = {
            competitor["ID"]: math.floor(competitor["Result"])
            for competitor in dances_json[0]["Competitors"]
        }
    else:
        placements = {
            competitor["ID"]: math.floor(competitor["Result"][-1])
            for competitor in final_round["Summary"]["Competitors"]
            if competitor["Result"]
        }

    dances = []
    for dance_json in dances_json:
        style, bare_name = _dance_and_style(dance_json["Dance_Name"])
        dances.append(Dance(level, style, bare_name))
    event_dances = tuple(dances)

    results = []
    for competitor in dances_json[0]["Competitors"]:
        place = placements.get(competitor["ID"])
        if place is None:
            continue
        lead, follow = _lead_follow(competitor["Participants"])
        results.append(
            CompetitionResult(
                dance=event_dances[0],
                lead=lead,
                follow=follow,
                place=place,
                num_rounds=num_rounds,
                competition_name=competition_name,
                competition_date=competition_date,
                event_dances=event_dances,
            )
        )
    return results


def _extract_level(event_name: str) -> str:
    """Extracts the level phrase from a CompOrganizer event name (e.g.
    "Closed Bronze Int'l Waltz" -> "Bronze"), stripping an optional
    "Closed "/"Open " registration-eligibility prefix first.

    An "Open" syllabus-level event (e.g. "Open Gold") isn't expected from
    CompOrganizer-backed competitions on our circuit - Open Gold might map to
    a different CDA level ("Novice") than Closed Gold, so this raises rather
    than silently returning "Gold" if one is ever seen.
    """
    name = event_name
    is_open = False
    for prefix in ("Closed ", "Open "):
        if name.startswith(prefix):
            is_open = prefix == "Open "
            name = name[len(prefix) :]
            break

    tokens = name.split()
    for n in range(1, _MAX_LEVEL_WORDS + 1):
        try:
            level = convert_level(" ".join(tokens[:n]))
        except ValueError:
            continue
        if is_open and level in SYLLABUS_LEVELS:
            raise ValueError(
                f"Unexpected 'Open' syllabus-level event {event_name!r} - "
                "needs a code change to determine the correct CDA level."
            )
        return level
    raise ValueError(f"Could not find a recognized level in event name {event_name!r}")


def _dance_and_style(dance_name: str) -> tuple[Style, str]:
    """Splits a per-dance name like "Int'l Waltz" or "Am. Cha Cha" into
    (style, bare dance name). The "Int'l"/"Am."/"Amer." marker alone doesn't
    say Standard-vs-Latin or Smooth-vs-Rhythm, so each candidate style is
    tried via convert_dance() until one recognizes the bare name. Nightclub
    dance names (e.g. "Salsa") carry neither marker, so they're tried as
    Style.NIGHTCLUB directly.
    """
    if dance_name.startswith("Int'l "):
        candidates = Style.international_styles()
        bare_name = dance_name[len("Int'l ") :]
    elif dance_name.startswith("Amer. "):
        candidates = Style.american_styles()
        bare_name = dance_name[len("Amer. ") :]
    elif dance_name.startswith("Am. "):
        candidates = Style.american_styles()
        bare_name = dance_name[len("Am. ") :]
    else:
        candidates = [Style.NIGHTCLUB]
        bare_name = dance_name

    for style in candidates:
        try:
            convert_dance(style, bare_name)
            return style, bare_name
        except ValueError:
            continue
    raise ValueError(f"Could not determine style for dance name {dance_name!r}")


def _lead_follow(participants: list) -> tuple[DancerRef, DancerRef]:
    """CompOrganizer lists Participants as [lead, follow] for a Couple-type
    event (Config "LF")."""
    lead_json, follow_json = participants
    return (
        DancerRef(first=lead_json["Name"][0], last=lead_json["Name"][1]),
        DancerRef(first=follow_json["Name"][0], last=follow_json["Name"][1]),
    )
