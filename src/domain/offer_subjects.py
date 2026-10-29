"""Split the guide's `Matières` column by serie (story E3.1).

The cell lists, per serie, the three ranking subjects of an offer, but the
segments are often glued together ("...SVTDEAT/Pêche et aquaculture : ...").
Splitting on the serie headers recovers every segment; `data/` is never
modified, the split is computed. Known subjects are normalized with
`normalize_subject`; unknown labels (Concours épreuves, "Economie",
"Espagnol ou Allemand", "Les trois (03) matières écrites") are kept verbatim:
nothing is ever invented.
"""

import re

from src.domain.coefficients import load_coefficients
from src.domain.subjects import UnknownSubjectError, normalize_subject

SUBJECTS_NOT_PUBLISHED = "matières non publiées"  # PUB-220, PUB-223: the cell is "—"
STATUS_CALCULABLE = "calculable"
STATUS_NOT_CALCULABLE = "non calculable"
STATUS_CONCOURS = "concours"  # épreuves listed, no Bac subject assumed (PRD section 3.1)
EXPECTED_SUBJECT_COUNT = 3  # Guide d'information 2026-2027, page 8: trois matières
ALL_SERIES_HEADER = "Toutes séries"

_SIMPLE_SERIES = {"A1", "A2", "B", "C", "D", "E", "EA",
                  "F1", "F2", "F3", "F4", "G1", "G2", "G3"}
_SERIE_TOKEN = re.compile(r"(DEAT|DT|A1|A2|EA|F[1-4]|G[1-3]|[BCDE])(?=[,/\s;:]|$)")
_EMPTY_CELLS = {"", "—", "–", "-"}


class OfferSubjectsError(ValueError):
    """Raised when a `Matières` cell has no readable serie header; we never guess."""


def parse_subjects_by_series(matieres: str) -> dict[str, list[str]]:
    """Return {serie: [subjects]} for one raw `Matières` cell.

    Combined headers ("C, D : ...") are expanded to one key per serie.
    Subjects are normalized when `normalize_subject` knows them, otherwise
    kept verbatim. An unpublished cell ("—") returns {}.
    """
    return _parse_segments(matieres, normalize=True)


def _parse_segments(matieres: str, normalize: bool) -> dict[str, list[str]]:
    if not isinstance(matieres, str):
        raise OfferSubjectsError(f"Matières illisible: {matieres!r}")
    if matieres.strip() in _EMPTY_CELLS:
        return {}
    chunks = matieres.split(":")
    headers = [_read_header(chunks[0])]
    segments: list[str] = []
    for index, chunk in enumerate(chunks[1:]):
        if index < len(chunks) - 2:
            segment, header = _split_segment_and_header(chunk)
            segments.append(segment)
            headers.append(header)
        else:
            segments.append(chunk)
    parsed: dict[str, list[str]] = {}
    for header, segment in zip(headers, segments):
        names = _split_subjects(segment)
        subjects = [_normalize_or_keep(raw) for raw in names] if normalize else names
        for serie in header:
            parsed[serie] = subjects
    return parsed


def subjects_for_serie(row: dict, serie: str) -> dict:
    """Return the ranking subjects of one guide row for `serie`.

    Result: {"status", "subjects", "epreuves", "reason"}. `status` is
    `calculable` only when exactly three normalized subjects carry a
    coefficient in `serie`; otherwise it is `non calculable`,
    `matières non publiées` or `concours`, with an explicit `reason`.
    """
    raw = row.get("Matières", "")
    # Concours first: even with nothing published, the entry mode is the
    # information the student needs (E3.5), not a missing ranking subject.
    if row.get("Mode_entrée") == "Concours":
        epreuves: list[str] = []
        if isinstance(raw, str) and raw.strip() not in _EMPTY_CELLS:
            verbatim = _parse_segments(raw, normalize=False)
            epreuves = verbatim.get(serie, verbatim.get(ALL_SERIES_HEADER, []))
        return _result(STATUS_CONCOURS, epreuves=epreuves,
                       reason="Concours : les notes du Bac ne suffisent pas, "
                              "admission par épreuve séparée")
    if not isinstance(raw, str) or raw.strip() in _EMPTY_CELLS:
        return _result(SUBJECTS_NOT_PUBLISHED, reason=SUBJECTS_NOT_PUBLISHED)
    parsed = parse_subjects_by_series(raw)
    subjects_raw = parsed.get(serie, parsed.get(ALL_SERIES_HEADER))
    if subjects_raw is None:
        return _result(STATUS_NOT_CALCULABLE,
                       reason=f"série {serie} absente des matières de l'offre")
    return _calculable_result(serie, subjects_raw)


def _calculable_result(serie: str, subjects_raw: list[str]) -> dict:
    try:
        coefficients = load_coefficients(serie)
    except ValueError as error:
        return _result(STATUS_NOT_CALCULABLE, reason=str(error))
    subjects, problems = [], []
    for raw in subjects_raw:
        if " ou " in f" {raw.casefold()} ":
            problems.append(f"matière alternative non tranchée : « {raw} »")
            continue
        try:
            subject = normalize_subject(raw)
        except UnknownSubjectError:
            problems.append(f"matière inconnue pour la série {serie} : « {raw} »")
            continue
        if subject not in coefficients:
            problems.append(f"coefficient manquant : {subject} en série {serie}")
        else:
            subjects.append(subject)
    if problems:
        return _result(STATUS_NOT_CALCULABLE, reason="; ".join(problems))
    if len(subjects) != EXPECTED_SUBJECT_COUNT or len(set(subjects)) != len(subjects):
        return _result(STATUS_NOT_CALCULABLE,
                       reason=f"{len(subjects)} matière(s) exploitable(s) au lieu de "
                              f"{EXPECTED_SUBJECT_COUNT} (guide, page 8)")
    return _result(STATUS_CALCULABLE, subjects=subjects)


def _result(status: str, subjects: list[str] | None = None,
            epreuves: list[str] | None = None, reason: str | None = None) -> dict:
    return {"status": status, "subjects": subjects or [],
            "epreuves": epreuves or [], "reason": reason}


def _read_header(text: str) -> list[str]:
    header = text.strip()
    if not _is_header_list(header):
        raise OfferSubjectsError(f"en-tête de série illisible: {text!r}")
    return [token.strip() for token in header.split(",")]


def _split_segment_and_header(chunk: str) -> tuple[str, list[str]]:
    for match in _SERIE_TOKEN.finditer(chunk):
        candidate = chunk[match.start():].strip().rstrip(";").strip()
        if _is_header_list(candidate):
            return chunk[:match.start()], [t.strip() for t in candidate.split(",")]
    raise OfferSubjectsError(f"en-tête de série introuvable après: {chunk!r}")


def _is_header_list(text: str) -> bool:
    tokens = [token.strip() for token in text.split(",")]
    return all(token and _is_serie_token(token) for token in tokens)


def _is_serie_token(token: str) -> bool:
    return (token in _SIMPLE_SERIES or token == ALL_SERIES_HEADER
            or token in ("DT", "DEAT")
            or token.startswith(("DT/", "DEAT/")))


def _split_subjects(segment: str) -> list[str]:
    return [name for name in
            (part.strip().rstrip(";").strip() for part in segment.split(",")) if name]


def _normalize_or_keep(raw: str) -> str:
    try:
        return normalize_subject(raw)
    except UnknownSubjectError:
        return raw
