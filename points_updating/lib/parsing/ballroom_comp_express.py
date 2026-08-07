"""Ballroom Comp Express results parsing for points_updating.

Unlike CompOrganizer/O2CM, a Ballroom Comp Express results page embeds its
own fully structured data directly in the page as JSON `<script>` variables
(`results`, `dancers`, `eventinfo`) - one GET per event, no further API
calls or HTML-table scraping needed.
"""

import json
import math
import re
from datetime import date
from typing import Optional

from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.parsing.http_client import ThrottledClient
from utils.lib.constants import OpenLevel, Style, SyllabusLevel
from utils.lib.models.dance import Dance

_BASE_URL = "https://ballroomcompexpress.com"

# Ballroom Comp Express doesn't mark Rookie/Veteran events with a reliable
# numeric field, so detection is text-based, matching both "Rookie/Vet" and
# "Rookie/Veteran" phrasing.
_ROOKIE_VET_MARKER = "Rookie"

# Style phrases as they appear in Ballroom Comp Express's own event display
# names. Unlike CompOrganizer's "Int'l"/"Am." prefix, these phrases are
# unambiguous, so no trial-and-error via convert_dance() is needed.
_STYLE_PHRASES: dict[str, Style] = {
    "International Standard": Style.STANDARD,
    "International Latin": Style.LATIN,
    "American Smooth": Style.SMOOTH,
    "American Rhythm": Style.RHYTHM,
}

# Level phrases as Ballroom Comp Express writes them in display names,
# mapped to the CDA level they represent - None means the level has no CDA
# points equivalent (skip the event). Some competitions additionally use an
# NDCA-style letter-class system (N/E/D/C/B/A/S Class) alongside or instead
# of the plain CDA words; both phrasings map to the same CDA levels here.
#
# Closed vs. Open Gold maps to two different CDA levels (Gold vs. Novice),
# so "Open Gold" must be checked before the bare "Gold" fallback, or "Gold"
# would match first and always resolve to Gold. When neither modifier is
# present (e.g. "C Class Gold"), it defaults to Gold/Closed.
#
# "N Class" alone is ambiguous - it could pair with either Newcomer or
# Pre-Bronze - so explicit level words are checked before it, in case a
# future event ever spells out "N Class Newcomer".
_LEVEL_PHRASES: tuple[tuple[str, Optional[str]], ...] = (
    ("Newcomer", SyllabusLevel.NEWCOMER),
    ("Open Gold", OpenLevel.NOVICE),
    ("Pre-Bronze", None),
    ("N Class", None),
    ("Bronze", SyllabusLevel.BRONZE),
    ("E Class", SyllabusLevel.BRONZE),
    ("Silver", SyllabusLevel.SILVER),
    ("D Class", SyllabusLevel.SILVER),
    ("Gold", SyllabusLevel.GOLD),
    ("B Class", OpenLevel.PRECHAMP),
    ("A Class", OpenLevel.CHAMP),
    ("S Class", OpenLevel.CHAMP),
)

_EVENT_ENTRY_RE = re.compile(r'<a href="\./results\.php\?cid=\d+&eid=(\d+)">([^<]+)</a>')
_EMBEDDED_JSON_RE = re.compile(r"var (results|dancers|eventinfo) = JSON\.parse\('(.*?)'\);")


def fetch_event_list(cid: int, client: ThrottledClient) -> list[tuple[int, str]]:
    """Returns every event in a competition as (event_id, display name) pairs,
    scraped from the results index page's server-rendered event links.
    """
    response = client.get(f"{_BASE_URL}/results.php", params={"cid": cid})
    response.raise_for_status()
    return [(int(eid), name) for eid, name in _EVENT_ENTRY_RE.findall(response.text)]


def fetch_event_page(cid: int, eid: int, client: ThrottledClient) -> str:
    """Returns one event's results page as raw HTML."""
    response = client.get(f"{_BASE_URL}/results.php", params={"cid": cid, "eid": eid})
    response.raise_for_status()
    return response.text


def extract_embedded_json(html: str) -> dict:
    """Extracts and decodes the `results`/`dancers`/`eventinfo` JSON values
    Ballroom Comp Express embeds directly in an event page's `<script>` tag.

    Each variable is assigned via `JSON.parse('<escaped JSON string>')`; the
    string is escaped for embedding in a single-quoted JS literal (`\\"`,
    `\\/`, `\\\\`), not standard JSON escaping, so it's unescaped by hand
    rather than decoded as Python's `unicode_escape`, which would corrupt
    any non-ASCII dancer names.

    Returns:
        A dict with keys "results", "dancers", "eventinfo", each the parsed
        JSON value.
    Raises:
        ValueError: if any of the three expected variables isn't found.
    """
    found = dict(_EMBEDDED_JSON_RE.findall(html))
    missing = {"results", "dancers", "eventinfo"} - found.keys()
    if missing:
        raise ValueError(f"Could not find embedded JSON for: {sorted(missing)}")
    return {name: json.loads(_unescape_js_string(raw)) for name, raw in found.items()}


def _unescape_js_string(raw: str) -> str:
    """Reverses Ballroom Comp Express's escaping of a JSON string for
    embedding in a single-quoted JS literal (equivalent to PHP's
    addslashes()): `\\"` -> `"`, `\\/` -> `/`, `\\'` -> `'`, `\\\\` -> `\\`.
    Everything else, including non-ASCII characters, passes through
    untouched.
    """
    chars = []
    i = 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw) and raw[i + 1] in "\\\"/'":
            chars.append(raw[i + 1])
            i += 2
        else:
            chars.append(raw[i])
            i += 1
    return "".join(chars)


def parse_competition(
    cid: int, competition_name: str, competition_date: date, client: ThrottledClient
) -> list[CompetitionResult]:
    """Fetches and parses every couple event in a Ballroom Comp Express
    competition.

    Args:
        cid: The competition's id, from its results page URL
            (`results.php?cid=<cid>`).
        competition_name: The competition's name.
        competition_date: The date the competition was held.
        client: The HTTP client to fetch with.
    Returns:
        One CompetitionResult per (couple, dance) across every couple event
        in the competition. Non-couple events (e.g. Formation Team) are
        skipped here, not raised on - see _parse_event for the single-event
        contract, which does raise for those.
    """
    results = []
    for eid, _ in fetch_event_list(cid, client):
        event = extract_embedded_json(fetch_event_page(cid, eid, client))
        if event["eventinfo"]["eventtype"] != 1:
            continue
        results.extend(_parse_event(event, competition_name, competition_date))
    return results


def _parse_event(
    event: dict, competition_name: str, competition_date: date
) -> list[CompetitionResult]:
    """Parses one already-fetched event's JSON (as returned by
    extract_embedded_json()) into CompetitionResults, one per (couple,
    dance) danced in it.

    Placement comes from the final round's per-partnership top-level
    `place` field (Ballroom Comp Express's own combined placement across
    every dance in the event), not the same round's per-dance-nested
    `place` - matching the CDA's rule that a multi-dance's points are based
    on overall placement. The top-level value can itself be a true,
    unresolved tie (e.g. two couples both at 1.5), which is rounded down to
    the better integer place for both couples (standard "1224" ranking -
    ties share the higher rank).

    Args:
        event: A dict with "results"/"dancers"/"eventinfo" keys, as
            returned by extract_embedded_json().
        competition_name: The competition's name.
        competition_date: The date the competition was held.
    Returns:
        One CompetitionResult per (couple, dance), every dance in the event
        sharing one event_dances tuple and one num_rounds. Empty if the
        event is Rookie/Veteran, or a level with no CDA points equivalent
        (e.g. Pre-Bronze/N Class) - see below.
    Raises:
        NotImplementedError: if eventinfo["eventtype"] isn't 1 (Couple).
    """
    eventinfo = event["eventinfo"]
    if eventinfo["eventtype"] != 1:
        raise NotImplementedError(
            f"Unsupported Ballroom Comp Express event type: {eventinfo['eventtype']!r}"
        )
    if _ROOKIE_VET_MARKER in eventinfo["displayname"]:
        # Not points-eligible; unlike CompOrganizer, Ballroom Comp Express
        # doesn't say which partner is the rookie, so this skips rather
        # than guessing roles.
        return []

    level = _extract_level(eventinfo["displayname"])
    if level is None:
        # A level with no CDA points equivalent (e.g. Pre-Bronze/N Class).
        return []
    style, remainder = _extract_style_and_remainder(eventinfo["displayname"])

    results_json = event["results"]
    round_ids = results_json["roundorder"]
    num_rounds = len(round_ids)
    final_round = next(
        results_json[str(round_id)]
        for round_id in round_ids
        if results_json[str(round_id)]["final"] == 1
    )

    dance_names = eventinfo.get("dancenames")
    dances = tuple(
        Dance(level, style, dance_names[code] if dance_names else remainder)
        for code in final_round["dances"]
    )

    dancers_json = event["dancers"]
    results = []
    for partnership_id in final_round["partnershiporder"]:
        partnership = final_round[str(partnership_id)]
        lead, follow = _lead_follow(dancers_json[str(partnership_id)])
        for dance in dances:
            results.append(
                CompetitionResult(
                    dance=dance,
                    lead=lead,
                    follow=follow,
                    place=math.floor(partnership["place"]),
                    num_rounds=num_rounds,
                    competition_name=competition_name,
                    competition_date=competition_date,
                    event_dances=dances,
                )
            )
    return results


def _extract_level(display_name: str) -> Optional[str]:
    """Extracts the CDA level from a Ballroom Comp Express event display
    name (e.g. "Amateur Adult Bronze American Smooth Waltz" -> "Bronze"),
    per _LEVEL_PHRASES. Returns None if the level has no CDA points
    equivalent (e.g. Pre-Bronze/N Class).

    Matching is done against whitespace-split tokens (parentheses
    stripped first, so "(Closed Gold)" tokenizes the same as "Closed
    Gold"), not raw substring search, so a hyphenated word like
    "Pre-Bronze" - one token - isn't mistaken for "Bronze".
    """
    tokens = display_name.replace("(", " ").replace(")", " ").split()
    for phrase, level in _LEVEL_PHRASES:
        phrase_tokens = phrase.split()
        n = len(phrase_tokens)
        if any(tokens[i : i + n] == phrase_tokens for i in range(len(tokens) - n + 1)):
            return level
    raise ValueError(f"Could not find a recognized level in event name {display_name!r}")


def _extract_style_and_remainder(display_name: str) -> tuple[Style, str]:
    """Extracts the style from a Ballroom Comp Express event display name,
    along with everything after it. For a single-dance event, that
    remainder is the bare dance name itself (e.g. "Amateur Collegiate
    Bronze American Smooth Waltz" -> (Style.SMOOTH, "Waltz")); for a
    multi-dance event, eventinfo's own "dancenames" map is used instead and
    the remainder (e.g. "W/T/F") is unused.
    """
    for phrase, style in _STYLE_PHRASES.items():
        index = display_name.find(phrase)
        if index != -1:
            return style, display_name[index + len(phrase) :].strip()
    raise ValueError(f"Could not determine style for event name {display_name!r}")


def _lead_follow(dancer: dict) -> tuple[DancerRef, DancerRef]:
    """Ballroom Comp Express's dancers map already labels each partnership's
    two dancers as leader/follower directly, unlike CompOrganizer's
    positional Participants list."""
    return (
        DancerRef(first=dancer["leaderfname"].strip(), last=dancer["leaderlname"].strip()),
        DancerRef(first=dancer["followerfname"].strip(), last=dancer["followerlname"].strip()),
    )
