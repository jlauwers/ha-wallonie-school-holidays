"""Outils pour retrouver et parser les calendriers .ics d'enseignement.be.

On évite volontairement une dépendance externe (ex: la lib `icalendar`) :
les fichiers publiés par la Fédération Wallonie-Bruxelles sont simples
(événements sur base de journées entières, pas de récurrence RRULE), donc un
petit parseur maison suffit et garde l'intégration légère.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import logging
import re

_LOGGER = logging.getLogger(__name__)

# Repère les liens .ics du calendrier scolaire, ex:
# .../calendrier_scolaire/2025_Cal_Obli_2627.ics
_ICS_LINK_RE = re.compile(
    r"""(?P<url>[^\s"'<>]*calendrier_scolaire/[^\s"'<>]*\.ics)""",
    re.IGNORECASE,
)

_VEVENT_RE = re.compile(r"BEGIN:VEVENT(?P<body>.*?)END:VEVENT", re.DOTALL)
_SUMMARY_RE = re.compile(r"^SUMMARY:(.*)$", re.MULTILINE)
_DTSTART_RE = re.compile(r"^DTSTART(?:;[^:]*)?:(\d{8})", re.MULTILINE)
_DTEND_RE = re.compile(r"^DTEND(?:;[^:]*)?:(\d{8})", re.MULTILINE)


@dataclass
class HolidayEvent:
    """Un événement du calendrier scolaire (jour férié ou période de congé)."""

    summary: str
    start: date
    end: date  # exclusif, comme le veut la norme iCalendar

    @property
    def is_multi_day(self) -> bool:
        return (self.end - self.start).days > 1


def find_ics_urls(page_html: str, filename_pattern: str) -> list[str]:
    """Retourne les URLs absolues des .ics correspondant au motif donné.

    `filename_pattern` est un fragment attendu dans le nom de fichier,
    par ex. "Cal_Obli" ou "Cal_ESAHR".
    """
    urls: list[str] = []
    for match in _ICS_LINK_RE.finditer(page_html):
        url = match.group("url")
        if filename_pattern.lower() not in url.lower():
            continue
        if url.startswith("http"):
            urls.append(url)
        else:
            urls.append("https://www.enseignement.be/" + url.lstrip("/"))

    # dédoublonnage en conservant l'ordre
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def _unfold_ics_lines(raw: str) -> str:
    """Défait le "line folding" iCalendar (une ligne continuée commence par un espace)."""
    return re.sub(r"\r?\n[ \t]", "", raw)


def parse_ics(raw: str) -> list[HolidayEvent]:
    """Parse un fichier .ics et retourne la liste des événements journée entière."""
    raw = _unfold_ics_lines(raw)
    events: list[HolidayEvent] = []

    for vevent_match in _VEVENT_RE.finditer(raw):
        body = vevent_match.group("body")

        summary_match = _SUMMARY_RE.search(body)
        start_match = _DTSTART_RE.search(body)
        end_match = _DTEND_RE.search(body)

        if not (summary_match and start_match):
            continue

        summary = summary_match.group(1).strip()
        # Les caractères échappés dans un SUMMARY iCalendar
        summary = summary.replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")

        try:
            start = datetime.strptime(start_match.group(1), "%Y%m%d").date()
        except ValueError:
            _LOGGER.debug("Date de début invalide ignorée: %s", start_match.group(1))
            continue

        if end_match:
            try:
                end = datetime.strptime(end_match.group(1), "%Y%m%d").date()
            except ValueError:
                end = start
        else:
            end = start

        if end <= start:
            # Sécurité : un DTEND égal ou antérieur au DTSTART n'a pas de sens
            from datetime import timedelta

            end = start + timedelta(days=1)

        events.append(HolidayEvent(summary=summary, start=start, end=end))

    return events


def merge_and_sort(all_events: list[HolidayEvent]) -> list[HolidayEvent]:
    """Fusionne les événements de plusieurs fichiers .ics et les trie par date.

    Élimine les doublons exacts (même résumé + mêmes dates), ce qui peut
    arriver si deux calendriers se chevauchent d'une année à l'autre.
    """
    seen: set[tuple[str, date, date]] = set()
    result: list[HolidayEvent] = []
    for event in all_events:
        key = (event.summary, event.start, event.end)
        if key in seen:
            continue
        seen.add(key)
        result.append(event)

    result.sort(key=lambda e: (e.start, e.end))
    return result
