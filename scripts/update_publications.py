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
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data" / "publications.json"
ORCID = "0000-0002-6442-2355"
ALLOWED_ORCID_TYPES = {
    "journal-article", "conference-paper", "book-chapter", "book",
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
            kind = str(work.get("publication-type") or "(missing)")
            kinds[kind] = kinds.get(kind, 0) + 1
    print(f"ORCID public record: {len(groups)} groups; work types: {kinds}")

    for group in groups:
        summaries = group.get("work-summary") or []
        for work in summaries:
            work_type = str(work.get("publication-type") or "").lower()
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
            result.append({
                "title": title,
                "year": year_of(work.get("publication-date")),
                "venue": journal_info.get("value") or "",
                "doi": doi,
                "url": link,
                "type": "journal-article" if work_type == "journal-article" else "other",
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
    all_records: dict[str, dict] = {}
    for record in prior_auto + discovered + curated:
        k = key(record)
        if k != "title:":
            all_records[k] = record  # curated takes precedence
    updated = sorted(all_records.values(),
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
