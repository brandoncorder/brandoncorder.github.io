#!/usr/bin/env python3
"""
Refresh the site's publication dataset from ORCID first, then Crossref.
No credentials required for the anonymous ORCID API or Crossref REST API.

The manually verified publications in assets/data/publications.json are
never discarded. Records are matched by DOI (or normalized title when
there is no DOI); Crossref is an additional source for works that ORCID
has not yet indexed. Failed API requests do not remove any records.

Run: python3 scripts/update_publications.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data" / "publications.json"
ORCID = "0000-0002-6442-2355"
ALLOWED_ORCID_TYPES = {
    "journal-article", "conference-paper", "book-chapter", "book", "dissertation", "dissertation-thesis",
}
ALLOWED_CROSSREF_TYPES = {
    "journal-article", "proceedings-article", "book-chapter", "book",
}


def fetch_json(url: str, accept: str = "application/json") -> dict:
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "BrandonCorderAcademicSite/1.0 (GitHub Pages bibliography sync)",
        },
    )
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def doi_value(raw: object) -> str:
    value = str(raw or "").strip()
    value = re.sub(r"(?i)^https?://(?:dx\.)?doi\.org/", "", value)
    value = re.sub(r"(?i)^doi:\s*", "", value)
    return value.lower() if re.match(r"^10\.\d{4,9}/", value, re.I) else ""


def crossref_authors(work: dict) -> list[dict]:
    """Get authors in publisher-supplied order, with ORCID when available."""
    authors: list[dict] = []
    for entry in work.get("author") or []:
        given = str(entry.get("given") or "").strip()
        family = str(entry.get("family") or "").strip()
        full_name = str(entry.get("name") or "").strip()
        if not family and not full_name:
            continue
        author = {"given": given, "family": family} if family else {"name": full_name}
        orcid_id = str(entry.get("ORCID") or "").rstrip("/").split("/")[-1]
        if re.fullmatch(r"\d{4}-\d{4}-\d{4}-[\dX]{4}", orcid_id):
            author["orcid"] = orcid_id
        authors.append(author)
    return authors


def enrich_authors_by_doi(records: list[dict]) -> None:
    """Resolve DOI author lists, including records missing the queried ORCID."""
    for record in records:
        doi = doi_value(record.get("doi"))
        if not doi:
            continue
        try:
            url = "https://api.crossref.org/works/" + quote(doi, safe="/")
            work = fetch_json(url).get("message") or {}
            authors = crossref_authors(work)
            if authors:
                record["authors"] = authors
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            print(f"Could not refresh DOI author list for {doi}: {type(exc).__name__}",
                  file=sys.stderr)


def key(record: dict) -> str:
    doi = doi_value(record.get("doi"))
    if doi:
        return "doi:" + doi
    title = re.sub(r"[^a-z0-9]", "", str(record.get("title", "")).casefold())
    return "title:" + title


def year_of(date_info: dict | None) -> int | None:
    if not isinstance(date_info, dict):
        return None
    raw_year = date_info.get("year")
    if isinstance(raw_year, dict):
        raw_year = raw_year.get("value")
    try:
        year = int(raw_year)
        return year if 1800 <= year <= 2200 else None
    except (TypeError, ValueError):
        return None


def read_orcid_works() -> list[dict]:
    url = f"https://pub.orcid.org/v3.0/{ORCID}/works"
    data = fetch_json(url, "application/vnd.orcid+json")
    result: list[dict] = []
    groups = data.get("group") or []
    kinds = {}
    for group in groups:
        for work in group.get("work-summary") or []:
            kind = str(work.get("type") or work.get("publication-type") or "(missing)")
            kinds[kind] = kinds.get(kind, 0) + 1
    print(f"ORCID public record: {len(groups)} groups; work types: {kinds}")

    for group in groups:
        summaries = group.get("work-summary") or []
        for work in summaries:
            work_type = str(work.get("type") or work.get("publication-type") or "").lower()
            if work_type not in ALLOWED_ORCID_TYPES:
                continue
            title_info = work.get("title") or {}
            title = ((title_info.get("title") or {}).get("value") or "").strip()
            if not title:
                continue
            doi = ""
            for ext in ((work.get("external-ids") or {}).get("external-id") or []):
                if str(ext.get("external-id-type") or "").lower() == "doi":
                    doi = doi_value(ext.get("external-id-value"))
                    if doi:
                        break
            url_info = work.get("url") or {}
            link = ("https://doi.org/" + doi) if doi else (url_info.get("value") or "")
            # Don't publish non-DOI entries without a stable linked source.
            if not link.startswith("https://"):
                continue
            journal_info = work.get("journal-title") or {}
            print(f"ORCID matched: {title}")
            result.append({
                "title": title,
                "year": year_of(work.get("publication-date")),
                "venue": journal_info.get("value") or "",
                "doi": doi,
                "url": link,
                "type": "journal-article" if work_type == "journal-article" else ("dissertation" if work_type in {"dissertation", "dissertation-thesis"} else "other"),
                "source": "ORCID",
            })
            break  # One preferred summary per ORCID work group
    return result


def read_crossref_works() -> list[dict]:
    query = urlencode({"filter": f"orcid:{ORCID}", "rows": 100})
    data = fetch_json("https://api.crossref.org/works?" + query)
    result: list[dict] = []
    for work in ((data.get("message") or {}).get("items") or []):
        kind = str(work.get("type") or "")
        if kind not in ALLOWED_CROSSREF_TYPES:
            continue
        doi = doi_value(work.get("DOI"))
        titles = work.get("title") or []
        if not doi or not titles:
            continue
        title = str(titles[0]).strip()
        if not title:
            continue
        dates = [work.get(field) or {} for field in
                 ("published", "published-online", "published-print", "issued")]
        publication_year = next((y for d in dates if (y := year_from_crossref(d))), None)
        journal = (work.get("container-title") or [""])
        result.append({
            "title": title,
            "year": publication_year,
            "venue": journal[0] if journal else "",
            "doi": doi,
            "url": "https://doi.org/" + doi,
            "type": "journal-article" if kind == "journal-article" else "other",
            "source": "Crossref",
            "authors": crossref_authors(work),
        })
    return result


def year_from_crossref(info: dict) -> int | None:
    parts = (info or {}).get("date-parts") or []
    try:
        return int(parts[0][0])
    except (IndexError, TypeError, ValueError):
        return None


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    curated = [item for item in data["publications"] if item.get("manual")]
    prior_auto = [item for item in data["publications"] if not item.get("manual")]
    discovered: list[dict] = []
    status = []
    successes = 0

    for source, reader in (("ORCID", read_orcid_works),
                           ("Crossref", read_crossref_works)):
        try:
            works = reader()
            successes += 1
            status.append(f"{source}: {len(works)} qualifying records")
            print(status[-1])
            discovered.extend(works)
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            status.append(f"{source}: unavailable ({type(exc).__name__})")
            print(status[-1], file=sys.stderr)

    if not successes:
        print("No API succeeded. Retaining the last saved dataset.", file=sys.stderr)
        return 1

    # Preserve curated entries and prior auto results. The APIs may omit works
    # temporarily; absence from one response must not silently delete a paper.
    # Match by either DOI or normalized title so a newly added DOI does not
    # create a second entry for a previously DOI-less, manually curated work.
    records: list[dict] = []
    for record in prior_auto + discovered + curated:
        title_key = re.sub(r"[^a-z0-9]", "", record.get("title", "").casefold())
        doi = doi_value(record.get("doi"))
        match = next((
            i for i, old in enumerate(records)
            if (doi and doi == doi_value(old.get("doi"))) or
               (title_key and title_key ==
                re.sub(r"[^a-z0-9]", "", old.get("title", "").casefold()))
        ), None)
        if match is None:
            if title_key:
                records.append(record)
            continue
        previous = records[match]
        if previous.get("manual"):
            winner = {**record, **previous}
        elif record.get("manual"):
            winner = {**previous, **record}
        else:
            winner = {**previous, **record}
        if not doi_value(winner.get("doi")):
            supplement = doi_value(previous.get("doi")) or doi
            if supplement:
                winner["doi"] = supplement
                if not winner.get("url"):
                    winner["url"] = "https://doi.org/" + supplement
        records[match] = winner
    # Publisher DOI metadata is preferred for author order and full names.
    # If the API is unavailable, any saved author list is retained.
    enrich_authors_by_doi(records)
    updated = sorted(records,
                     key=lambda item: (-(item.get("year") or 0),
                                       item.get("title", "").casefold()))
    data.update({
        "orcid": ORCID,
        "last_checked": date.today().isoformat(),
        "source_status": "; ".join(status),
        "publications": updated,
    })
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if DATA.read_text(encoding="utf-8") != serialized:
        DATA.write_text(serialized, encoding="utf-8")
        print(f"Updated publications.json: {len(updated)} works")
    else:
        print(f"No changes: {len(updated)} works")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
