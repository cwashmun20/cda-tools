"""O2CM results parsing for points_updating.

A heat's default page (no `selCount` given, which defaults to the Final
round) embeds a `<select id=selCount>` dropdown whose `<option>`s are
exactly the rounds that heat actually had; a heat with only a Final has no
dropdown at all, just the literal text "Final". One GET per heat gives
both the round count and the Final round's placement data, so unlike a
full-archival scraper, there's no need to fetch every round separately.

Dance names come directly from each per-dance table's own header text in
that same response.
"""

import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup, Tag

from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.parsing.http_client import ThrottledClient
from utils.lib.constants import Style
from utils.lib.models.dance import Dance, convert_dance, convert_level

_EVENT_URL = "https://results.o2cm.com/event3.asp"
_SCORESHEET_URL = "https://results.o2cm.com/scoresheet3.asp"

_HEATID_RE = re.compile(r"heatid=([A-Za-z0-9]+)")
_STATE_SEPARATOR_RE = re.compile(r"\s-\s*")

# Bare style words O2CM uses for multi-dance heat names (e.g. "Amateur
# Silver Smooth (WT)") - unambiguous, unlike the "Am."/"Intl." prefix used
# for single-dance heat names.
_STYLE_WORDS: dict[str, Style] = {style.value: style for style in Style.points_eligible_styles()}

_SECTION_LABELS = ("Couples", "Judges", "Chairperson", "Scrutineer")


def fetch_heat_list(comp_id: str, client: ThrottledClient) -> list[tuple[str, str]]:
    """Returns every heat in a competition as (heat_id, heat_name) pairs.

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
    soup = BeautifulSoup(response.text, "lxml")
    heats = []
    for link in soup.find_all("a", href=True):
        match = _HEATID_RE.search(link["href"])
        if match is not None:
            heats.append((match.group(1), link.get_text(strip=True)))
    return heats


def fetch_heat_page(comp_id: str, heat_id: str, client: ThrottledClient) -> str:
    """Returns one heat's default (Final round) page as raw HTML."""
    response = client.get(_SCORESHEET_URL, params={"event": comp_id, "heatid": heat_id})
    response.raise_for_status()
    return response.text


def parse_competition(
    comp_id: str, competition_name: str, competition_date: date, client: ThrottledClient
) -> list[CompetitionResult]:
    """Fetches and parses every heat in an O2CM-backed competition.

    Args:
        comp_id: The competition's id, from its results page URL
            (`event3.asp?event=<comp_id>`).
        competition_name: The competition's name.
        competition_date: The date the competition was held.
        client: The HTTP client to fetch with.
    Returns:
        One CompetitionResult per (couple, dance) across every heat in the
        competition.
    """
    results = []
    for heat_id, heat_name in fetch_heat_list(comp_id, client):
        html = fetch_heat_page(comp_id, heat_id, client)
        results.extend(_parse_heat(html, heat_name, competition_name, competition_date))
    return results


def _parse_heat(
    html: str, heat_name: str, competition_name: str, competition_date: date
) -> list[CompetitionResult]:
    """Parses one already-fetched heat's page into CompetitionResults, one
    per (couple, dance) danced in it.

    Placement comes from the Summary table's "Res" column when present
    (a multi-dance heat's combined placement across every dance), or the
    single dance table's own "P" column otherwise - matching the CDA's
    rule that a multi-dance's points are based on overall placement.

    Args:
        html: One heat's default-view page, as returned by
            fetch_heat_page().
        heat_name: The heat's display name, as returned by
            fetch_heat_list().
        competition_name: The competition's name.
        competition_date: The date the competition was held.
    Returns:
        One CompetitionResult per (couple, dance), every dance in the heat
        sharing one event_dances tuple and one num_rounds.
    """
    soup = BeautifulSoup(html, "lxml")
    normalized_name = " ".join(heat_name.split())
    level = _extract_level(normalized_name)

    round_select = soup.find("select", id="selCount")
    num_rounds = len(round_select.find_all("option")) if isinstance(round_select, Tag) else 1

    dance_tables, summary_table, legend_table = _classify_tables(soup)
    couples = _parse_couples(legend_table)
    raw_dance_names = [name for name, _ in dance_tables]
    style, dances = _resolve_style_and_dances(normalized_name, raw_dance_names, level)
    event_dances = tuple(dances)

    if summary_table is not None:
        placements = _extract_placements(summary_table, "Res")
    else:
        placements = _extract_placements(dance_tables[0][1], "P")

    results = []
    for (_, table), dance in zip(dance_tables, dances):
        for row in table.find_all("tr")[2:]:
            couple_id = row.find_all("td")[0].get_text(strip=True)
            place = placements.get(couple_id)
            if place is None:
                continue
            lead, follow = couples[couple_id]
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


def _resolve_style_and_dances(
    heat_name: str, raw_dance_names: list[str], level: str
) -> tuple[Style, list[Dance]]:
    """Resolves a heat's style and its Dance objects.

    A multi-dance heat name carries a bare, unambiguous style word (e.g.
    "Amateur Silver Smooth (WT)"); a single-dance heat name instead carries
    an ambiguous "Am."/"Intl." prefix, resolved by trying each candidate
    style via convert_dance() against the one real dance name.
    """
    for word, style in _STYLE_WORDS.items():
        if word in heat_name:
            return style, [Dance(level, style, name) for name in raw_dance_names]

    if "Intl." in heat_name:
        candidates = Style.international_styles()
    elif "Am." in heat_name:
        candidates = Style.american_styles()
    else:
        candidates = [Style.NIGHTCLUB]

    name = raw_dance_names[0]
    for style in candidates:
        try:
            convert_dance(style, name)
            return style, [Dance(level, style, name)]
        except ValueError:
            continue
    raise ValueError(f"Could not determine style for heat name {heat_name!r}")


def _classify_tables(
    soup: BeautifulSoup,
) -> tuple[list[tuple[str, Tag]], Optional[Tag], Tag]:
    """Splits every result table on a heat's page into per-dance tables
    (name, table), the multi-dance Summary table (if any), and the
    Couples/Judges/Chairperson/Scrutineer legend table - distinguished by
    each table's first row cell count (one colspan cell naming the dance
    or "Summary", vs. two cells for the legend table).
    """
    dance_tables: list[tuple[str, Tag]] = []
    summary_table: Optional[Tag] = None
    legend_table: Optional[Tag] = None
    for table in soup.find_all("table", class_="t1n"):
        if not isinstance(table, Tag):
            continue
        first_row = table.find("tr")
        if not isinstance(first_row, Tag):
            continue
        first_row_cells = first_row.find_all("td")
        if len(first_row_cells) == 1:
            label = first_row_cells[0].get_text(strip=True)
            if label == "Summary":
                summary_table = table
            else:
                dance_tables.append((label, table))
        else:
            legend_table = table
    if legend_table is None:
        raise ValueError("Could not find the Couples/Judges legend table")
    return dance_tables, summary_table, legend_table


def _parse_couples(legend_table: Tag) -> dict[str, tuple[DancerRef, DancerRef]]:
    """Maps each couple number in the legend table to its (lead, follow)."""
    couples = {}
    section = None
    for row in legend_table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 2:
            continue
        label = cells[-1].get_text(strip=True)
        if label in _SECTION_LABELS:
            section = label
            continue
        if section == "Couples":
            couple_id = cells[0].get_text(strip=True)
            if couple_id.isdigit():
                couples[couple_id] = _split_couple_names(cells[1].get_text(strip=True))
    return couples


def _split_couple_names(text: str) -> tuple[DancerRef, DancerRef]:
    """Splits a Couples-legend entry (e.g. "Spencer Schultz, Lena Wessel -
    CA") into (lead, follow), dropping the trailing state/region.
    """
    names_part = _STATE_SEPARATOR_RE.split(text, maxsplit=1)[0].strip()
    lead_str, follow_str = names_part.split(", ", 1)
    return _split_name(lead_str), _split_name(follow_str)


def _split_name(full_name: str) -> DancerRef:
    """Splits a "First Last" (or "First Middle Last") string on its last
    space, since O2CM's Couples legend gives one combined name string per
    dancer rather than separate first/last fields.
    """
    first, _, last = full_name.strip().rpartition(" ")
    return DancerRef(first=first, last=last) if first else DancerRef(first="", last=last)


def _extract_placements(table: Tag, column_label: str) -> dict[str, int]:
    """Reads a {couple_id: place} mapping from a per-dance or Summary
    table, locating the named column ("P" or "Res") by its header text
    rather than a fixed index, since column count varies with couple
    count. Row 0 is the table's dance-name/"Summary" title, row 1 is the
    real column headers, and data rows follow from row 2 on.
    """
    rows = table.find_all("tr")
    header_cells = rows[1].find_all("td")
    col_index = next(
        i for i, cell in enumerate(header_cells) if cell.get_text(strip=True) == column_label
    )
    placements = {}
    for row in rows[2:]:
        cells = row.find_all("td")
        couple_id = cells[0].get_text(strip=True)
        placements[couple_id] = int(cells[col_index].get_text(strip=True))
    return placements
