"""CompOrganizer results parsing for points_updating.

CompOrganizer/NDCA Premier is a shared third-party backend behind
school-branded dance.am results pages (e.g. mustangball.dance.am), not
dance.am's own backend. Confirmed against a real 2026 CDA competition (Cal
Poly Mustang Ball).
"""

from datetime import date

from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.parsing.http_client import ThrottledClient
from utils.lib.constants import SYLLABUS_LEVELS, Style
from utils.lib.models.dance import Dance, convert_dance, convert_level

_CALLBACK_COMPS_URL = "https://comporganizer.com/feed/callback-comps/"
_RESULTS_URL = "https://ndcapremier.com/feed/results/"

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
    response = client.get(_CALLBACK_COMPS_URL, params={"cbid": cbid})
    response.raise_for_status()
    return response.json()["Comps"][0]["Comp_Year_ID"]


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
    cbid: str, competition_name: str, competition_date: date, client: ThrottledClient
) -> list[CompetitionResult]:
    """Fetches and parses every couple event in a CompOrganizer-backed
    competition.

    Args:
        cbid: The callback token embedded in the school's dance.am results
            page.
        competition_name: The competition's name.
        competition_date: The date the competition was held.
        client: The HTTP client to fetch with.
    Returns:
        One CompetitionResult per (couple, dance) across every couple event
        in the competition. Non-couple events (Jack & Jill, team matches,
        etc.) are skipped here, not raised on - see _parse_event for the
        single-event contract, which does raise for those.
    """
    comp_year_id = resolve_comp_year_id(cbid, client)
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
    per (couple, dance) danced in it.

    Placement comes from the final round's round-level Summary, not any
    individual dance's own per-competitor Result; the Summary already
    holds the couple's combined placement across every dance in the event
    (a single-dance event's Summary result equals that one dance's own
    result), matching the CDA's rule that a multi-dance's points are based
    on overall placement, not any one dance's individual placement.

    Args:
        event: The `Result.Event` dict from fetch_event_results().
        competition_name: The competition's name.
        competition_date: The date the competition was held.
    Returns:
        One CompetitionResult per (couple, dance), every dance in the event
        sharing one event_dances tuple and one num_rounds.
    Raises:
        NotImplementedError: if event["Type"] isn't "Couple".
    """
    if event["Type"] != "Couple":
        raise NotImplementedError(f"Unsupported CompOrganizer event type: {event['Type']!r}")

    level = _extract_level(event["Name"])
    rounds = event["Rounds"]
    num_rounds = len(rounds)
    final_round = rounds[-1]
    dances_json = final_round["Dances"]

    placements = {
        competitor["ID"]: competitor["Result"][-1]
        for competitor in final_round["Summary"]["Competitors"]
    }

    dances = []
    for dance_json in dances_json:
        style, bare_name = _dance_and_style(dance_json["Dance_Name"])
        dances.append(Dance(level, style, bare_name))
    event_dances = tuple(dances)

    results = []
    for dance_json, dance in zip(dances_json, event_dances):
        for competitor in dance_json["Competitors"]:
            place = placements.get(competitor["ID"])
            if place is None:
                continue
            lead, follow = _lead_follow(competitor["Participants"])
            results.append(
                CompetitionResult(
                    dance=dance,
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
    (style, bare dance name). The "Int'l"/"Am." marker alone doesn't say
    Standard-vs-Latin or Smooth-vs-Rhythm, so each candidate style is tried
    via convert_dance() until one recognizes the bare name.
    """
    if dance_name.startswith("Int'l "):
        candidates = Style.international_styles()
        bare_name = dance_name[len("Int'l ") :]
    elif dance_name.startswith("Am. "):
        candidates = Style.american_styles()
        bare_name = dance_name[len("Am. ") :]
    else:
        raise ValueError(f"Unrecognized dance name prefix: {dance_name!r}")

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
