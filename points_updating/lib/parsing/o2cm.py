"""O2CM results parsing for points_updating.

A single POST to event3.asp with every filter left blank returns a
consolidated results page listing every event in the competition, each
with its Final-round placements and every earlier round's eliminated
couples, with a literal "----" row separating each round's group.
"""

import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup, Tag

from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.parsing.http_client import ThrottledClient
from utils.lib import constants
from utils.lib.constants import Style
from utils.lib.models.dance import Dance, convert_dance, convert_level
from utils.lib.multi_dance import expand_abbreviation

_EVENT_URL = "https://results.o2cm.com/event3.asp"

_EVENT_LINK_HREF_RE = re.compile(r"scoresheet3\.asp\?event=")
_PLACEMENT_ROW_RE = re.compile(r"^(\d+)\)\s+\d+\s+(.+)$")
_STATE_SEPARATOR_RE = re.compile(r"\s-\s*")
_CODE_RE = re.compile(r"\(([A-Za-z_]+)\)\s*$")
_SEPARATOR_TEXT = "----"
# A couple entered with no partner assigned yet shows as e.g. "TBA01 TBA" -
# not a real dancer, so that row is skipped rather than parsed.
_TBA_RE = re.compile(r"\bTBA\d*\b")

# Team Match events are not eligible for points.
_TEAM_MATCH_MARKER = "Team Match"

# Bare style words O2CM uses for multi-dance heat names (e.g. "Amateur
# Silver Smooth (WT)") - unambiguous, unlike the "Am."/"Intl." prefix used
# for single-dance heat names.
_STYLE_WORDS: dict[str, Style] = {style.value: style for style in Style.points_eligible_styles()}

# A Nightclub dance name is at most this many words (e.g. "West Coast
# Swing"), used when reading it directly from the heat name text.
_MAX_NIGHTCLUB_DANCE_WORDS = max(
    len(name.split()) for name in constants.DANCE_NAMES[Style.NIGHTCLUB]
)


def fetch_results_page(comp_id: str, client: ThrottledClient) -> str:
    """Returns a competition's full consolidated results page as raw HTML.

    POSTs event3.asp with every filter field blank, including selEnt -
    omitting any one field produces a 500.
    """
    response = client.post(
        _EVENT_URL,
        data={
            "event": comp_id,
            "selDiv": "",
            "selAge": "",
            "selSkl": "",
            "selSty": "",
            "selEnt": "",
            "submit": "OK",
        },
    )
    response.raise_for_status()
    return response.text


def fetch_competition_name(comp_id: str, client: ThrottledClient) -> str:
    """Returns the competition's own name from its results page."""
    return _extract_competition_name(fetch_results_page(comp_id, client))


def _extract_competition_name(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    cell = soup.find("td", class_="h4")
    if not isinstance(cell, Tag):
        raise ValueError("Could not find a competition name on the results page")
    return cell.get_text(strip=True)


def parse_competition(
    comp_id: str, competition_name: str, competition_date: date, client: ThrottledClient
) -> list[CompetitionResult]:
    """Fetches and parses every event in an O2CM-backed competition.

    Args:
        comp_id: The competition's id, from its results page URL
            (`event3.asp?event=<comp_id>`).
        competition_name: The competition's name.
        competition_date: The date the competition was held.
        client: The HTTP client to fetch with.
    Returns:
        One CompetitionResult per (couple, dance) across every event's
        Final round in the competition.
    """
    html = fetch_results_page(comp_id, client)
    return _parse_results_page(html, competition_name, competition_date)


def _parse_results_page(
    html: str, competition_name: str, competition_date: date
) -> list[CompetitionResult]:
    """Parses a competition's full consolidated results page into
    CompetitionResults, one per (couple, dance) danced in each event's
    Final round.
    """
    soup = BeautifulSoup(html, "lxml")
    results: list[CompetitionResult] = []
    heat_name: Optional[str] = None
    in_final_group = False
    final_rows: list[str] = []
    num_rounds = 1

    def flush() -> None:
        if heat_name is not None:
            results.extend(
                _build_results(
                    heat_name, final_rows, num_rounds, competition_name, competition_date
                )
            )

    for row in soup.find_all("tr"):
        link = row.find("a", href=_EVENT_LINK_HREF_RE)
        if link is not None:
            flush()
            heat_name = " ".join(link.get_text(strip=True).split())
            in_final_group = True
            final_rows = []
            num_rounds = 1
            continue
        if heat_name is None:
            continue
        # A nested tag (e.g. the <b> O2CM wraps a "TBA" placeholder
        # partner in) splits a row's text into separate fragments -
        # get_text()'s default separator ("") would silently glue them
        # together with no space, so use " " and re-normalize instead.
        text = " ".join(row.get_text(" ", strip=True).split())
        if text == _SEPARATOR_TEXT:
            in_final_group = False
            num_rounds += 1
            continue
        if in_final_group and _PLACEMENT_ROW_RE.match(text) and _TBA_RE.search(text) is None:
            final_rows.append(text)
    flush()
    return results


def _build_results(
    heat_name: str,
    final_rows: list[str],
    num_rounds: int,
    competition_name: str,
    competition_date: date,
) -> list[CompetitionResult]:
    if _TEAM_MATCH_MARKER in heat_name:
        return []

    level = _extract_level(heat_name)
    style, dances = _resolve_style_and_dances(heat_name, level)
    event_dances = tuple(dances)

    results = []
    for row_text in final_rows:
        place, lead, follow = _parse_placement_row(row_text)
        for dance in dances:
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


def _parse_placement_row(text: str) -> tuple[int, DancerRef, DancerRef]:
    """Parses one Final-round placement row (e.g. "1) 141 Eugene Xie & Yue
    Tong Lee -  CA") into (place, lead, follow), discarding the couple
    number and trailing state/region.
    """
    match = _PLACEMENT_ROW_RE.match(text)
    if match is None:
        raise ValueError(f"Could not parse placement row {text!r}")
    place = int(match.group(1))
    names_part = _STATE_SEPARATOR_RE.split(match.group(2), maxsplit=1)[0].strip()
    lead_str, follow_str = names_part.split(" & ", 1)
    return place, _split_name(lead_str), _split_name(follow_str)


def _extract_level(heat_name: str) -> str:
    """Extracts the level from an O2CM heat name (e.g. "Amateur Bronze Am.
    Waltz" -> "Bronze") by trying convert_level() against each word (and,
    first, each adjacent word pair, so two-word divisions like "Rookie
    Followers" are recognized ahead of a skill word appearing later in the
    same name, e.g. "Rookie Followers Bronze Am. Waltz").
    """
    tokens = heat_name.split()
    two_word_windows = [" ".join(pair) for pair in zip(tokens, tokens[1:])]
    for candidate in two_word_windows + tokens:
        try:
            return convert_level(candidate)
        except ValueError:
            continue
    raise ValueError(f"Could not find a recognized level in heat name {heat_name!r}")


def _resolve_style_and_dances(heat_name: str, level: str) -> tuple[Style, list[Dance]]:
    """Resolves a heat's style and Dance objects from its name and
    trailing letter code (e.g. "Amateur Silver Smooth (WT)", "Amateur
    Bronze Am. Waltz (W)", "Amateur Beginner Merengue (M)").

    A bare style word (e.g. "Smooth") gives the style directly, and the
    code expands via expand_abbreviation(). Otherwise an "Am."/"Amer."/
    "Intl." prefix narrows it to two candidate styles, disambiguated by checking
    which one's abbreviation map covers every letter in the code - Smooth/
    Rhythm and Standard/Latin use entirely disjoint letters, so exactly
    one candidate ever matches. With neither a bare style word nor a
    prefix, it's a Nightclub dance, whose name is read directly from the
    heat name text instead.
    """
    code_match = _CODE_RE.search(heat_name)
    if code_match is None:
        raise ValueError(f"Could not find a dance code in heat name {heat_name!r}")
    # A trailing "_" placeholder shows up on some real heats (e.g.
    # "(CRSB_)") - not a real dance slot, so it's dropped rather than
    # treated as an unrecognized letter.
    code = code_match.group(1).replace("_", "")

    for word, style in _STYLE_WORDS.items():
        if word in heat_name:
            return style, [Dance(level, style, name) for name in expand_abbreviation(style, code)]

    if "Intl." in heat_name:
        candidates = Style.international_styles()
    elif "Am." in heat_name or "Amer." in heat_name:
        candidates = Style.american_styles()
    else:
        candidates = None

    if candidates is not None:
        for style in candidates:
            abbrev_map = constants.ABBREVIATION_MAPS[style]
            if all(letter in abbrev_map for letter in code):
                return style, [
                    Dance(level, style, name) for name in expand_abbreviation(style, code)
                ]
        raise ValueError(f"Could not determine style for heat name {heat_name!r}")

    name_without_code = _CODE_RE.sub("", heat_name).strip()
    dance_name = _extract_nightclub_dance_name(name_without_code)
    return Style.NIGHTCLUB, [Dance(level, Style.NIGHTCLUB, dance_name)]


def _extract_nightclub_dance_name(name_without_code: str) -> str:
    """Finds a recognized Nightclub dance name as a word-suffix of the
    heat name text (after the trailing letter code has been stripped),
    trying longer suffixes first so a multi-word name (e.g. "West Coast
    Swing") isn't cut short - robust to however much boilerplate/level
    text precedes it, without needing to know exactly which words those
    were.
    """
    tokens = name_without_code.split()
    for n in range(min(_MAX_NIGHTCLUB_DANCE_WORDS, len(tokens)), 0, -1):
        candidate = " ".join(tokens[-n:])
        try:
            return convert_dance(Style.NIGHTCLUB, candidate)
        except ValueError:
            continue
    raise ValueError(f"Could not find a recognized Nightclub dance name in {name_without_code!r}")


def _split_name(full_name: str) -> DancerRef:
    """Splits a "First Last" (or "First Middle Last") string on its last
    space, since O2CM gives one combined name string per dancer rather
    than separate first/last fields.
    """
    first, _, last = full_name.strip().rpartition(" ")
    return DancerRef(first=first, last=last) if first else DancerRef(first="", last=last)
