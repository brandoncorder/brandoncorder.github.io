#!/usr/bin/env python3
"""Verify that every site's global sidebar links and contact details match.

Run locally: python scripts/check_navigation.py
Requires only the Python standard library.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "index.html",
    "aboutme.html",
    "research.html",
    "teaching.html",
    "publications.html",
    "awards.html",
    "service.html",
    "fieldwork.html",
]
EXPECTED = [
    ("index.html", "Home"),
    ("aboutme.html", "About Me"),
    ("research.html", "Research"),
    ("teaching.html", "Teaching and Mentoring"),
    ("publications.html", "Publications"),
    ("index.html#science-communication", "Science Communication"),
    ("awards.html", "Awards"),
    ("service.html", "Service"),
    ("fieldwork.html", "Fieldwork"),
    ("index.html#collections", "Collections"),
]
CONTACTS = ("mailto:bdcorder@ncsu.edu", "mailto:brandoncorder95@gmail.com")


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.current_href: str | None = None
        self.label: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.current_href = dict(attrs).get("href")
            self.label = []

    def handle_data(self, data: str) -> None:
        if self.current_href is not None:
            self.label.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.current_href is not None:
            self.links.append((self.current_href, "".join(self.label).strip()))
            self.current_href = None
            self.label = []


def audit() -> list[str]:
    failures: list[str] = []
    for path in PAGES:
        page_path = ROOT / path
        if not page_path.is_file():
            failures.append(f"{path}: missing page")
            continue
        html = page_path.read_text(encoding="utf-8")
        menu = re.search(
            r'<nav\b[^>]*\bid="menu"[^>]*>(.*?)</nav>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if not menu:
            failures.append(f"{path}: no global sidebar menu")
            continue

        parser = LinkParser()
        parser.feed(menu.group(1))
        if parser.links != EXPECTED:
            failures.append(f"{path}: sidebar does not match canonical menu")
            print(f"  {path}: actual menu: {parser.links}")

        sidebar = html[html.find('<div id="sidebar">'):]
        for contact in CONTACTS:
            if contact not in sidebar:
                failures.append(f"{path}: missing contact link {contact}")

        for href, label in parser.links:
            target, fragment = urldefrag(href)
            target_path = ROOT / target
            if not target_path.is_file():
                failures.append(f"{path}: {label} points to missing file {target}")
                continue
            if fragment:
                target_html = target_path.read_text(encoding="utf-8")
                anchor = r'\bid\s*=\s*["\']' + re.escape(fragment) + r'["\']'
                if not re.search(anchor, target_html):
                    failures.append(f"{path}: {label} points to missing anchor #{fragment}")
    return failures


if __name__ == "__main__":
    errors = audit()
    if errors:
        for error in errors:
            print("FAIL:", error, file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: {len(PAGES)} pages use the same {len(EXPECTED)}-link sidebar; all links, anchors and contacts are valid.")
