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
    "science-communication.html",
    "awards.html",
    "service.html",
    "fieldwork.html",
    "collections.html",
]
EXPECTED = [
    ("index.html", "Home"),
    ("aboutme.html", "About Me"),
    ("research.html", "Research and Publications"),
    ("teaching.html", "Teaching and Mentoring"),
    ("science-communication.html", "Science Communication"),
    ("service.html", "Service and Outreach"),
    ("fieldwork.html", "Fieldwork"),
    ("collections.html", "Collections"),
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
    # Catch regressions in page consolidation and home page deep links.
    research = (ROOT / "research.html").read_text(encoding="utf-8")
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    teaching = (ROOT / "teaching.html").read_text(encoding="utf-8")
    science = (ROOT / "science-communication.html").read_text(encoding="utf-8")
    legacy = (ROOT / "publications.html").read_text(encoding="utf-8")

    if 'id="publication-list"' not in research or 'assets/js/publications.js' not in research:
        failures.append("Research must contain the automatic publication list and renderer")
    if 'research.html#publications' not in homepage:
        failures.append("Homepage Publications must link to the Research publications anchor")
    for label, target in [
        ("Teaching", 'href="teaching.html"'),
        ("Mentoring", 'href="teaching.html#mentoring"'),
    ]:
        if target not in homepage:
            failures.append(f"Homepage missing {label} button")
    if 'id="mentoring"' not in teaching:
        failures.append("Teaching page is missing the Mentoring anchor")
    if 'id="science-communication"' not in homepage or 'id="science-communication"' not in science:
        failures.append("Science Communication must be present on both homepage and dedicated page")
    if 'url=research.html#publications' not in legacy:
        failures.append("Legacy publications.html redirect missing")
    about = (ROOT / "aboutme.html").read_text(encoding="utf-8")
    awards = (ROOT / "awards.html").read_text(encoding="utf-8")
    service = (ROOT / "service.html").read_text(encoding="utf-8")
    for name, content in [("About Me", about), ("Awards redirect", awards)]:
        if "aboutme.html#awards" not in content and 'id="awards"' not in content:
            failures.append(f"{name} missing awards destination")
    if 'url=aboutme.html#awards' not in awards:
        failures.append("Legacy awards.html redirect missing")
    if '<section id="awards">' in homepage or '<section id="service">' in homepage:
        failures.append("Homepage must not contain Awards or Service sections")
    if "View iNaturalist" not in homepage or 'href="aboutme.html" class="button big">About Me</a>' not in homepage:
        failures.append("Homepage missing About Me button after iNaturalist")
    if "www.instagram.com/brandoncorder/" not in homepage or "www.instagram.com/brandoncorder/" not in science:
        failures.append("Instagram feature missing in Science Communication")
    for file in PAGES:
        page = (ROOT / file).read_text(encoding="utf-8")
        if "<title>" not in page or "Brandon D. Corder</title>" not in page:
            failures.append(f"{file} missing updated Brandon D. Corder title")

    # The November 2026 refinements must survive future page edits.
    collections = (ROOT / "collections.html").read_text(encoding="utf-8")
    stylesheet = ROOT / "assets/css/site-overrides.css"
    dataset = ROOT / "assets/data/publications.json"
    publications_js = ROOT / "assets/js/publications.js"
    if not stylesheet.is_file():
        failures.append("Shared site-overrides.css stylesheet missing")
    for page_name in PAGES:
        page = (ROOT / page_name).read_text(encoding="utf-8")
        if 'assets/css/site-overrides.css' not in page:
            failures.append(f"{page_name}: missing shared heading and spacing styles")
    if 'href="collections.html" class="button"' not in homepage:
        failures.append("Homepage missing standalone Collections button")
    if 'id="collections"' not in collections or '[Content coming soon]' not in collections:
        failures.append("Collections page incomplete")
    if '<h1 class="page-title">Service and Outreach</h1>' not in service:
        failures.append("Service and Outreach page title not updated")
    if '<h1 class="page-title">About Me</h1>' not in about:
        failures.append("About Me must use consistent page-title styling")
    for label, content in [("homepage", homepage), ("science page", science)]:
        if "friendslakeshorepreserve.com/people--events/an-introduction" in content:
            failures.append(f"{label}: retired moss-walk hyperlink remains")
        if "I also share botanical photography, field observations" in content:
            failures.append(f"{label}: removed Instagram introduction sentence remains")
    if "This website brings together my teaching" in homepage:
        failures.append("Homepage intro sentence was reintroduced")
    if "Read the NC State feature" not in teaching:
        failures.append("NC State teaching feature missing")
    if "Sydney Berkeley (2024–2025)" not in teaching:
        failures.append("Sydney Berkeley dates missing")
    if teaching.index("<h3>Students Mentored</h3>") < teaching.index("<h3>Mentoring Development</h3>"):
        failures.append("Students Mentored must appear after Mentoring Development")
    if "Read more about Wisconsin’s peatlands project" not in teaching:
        failures.append("Peatland read-more link missing")
    if "Advisor: Kenneth M. Cameron" not in research or "publication-advisor" not in publications_js.read_text(encoding="utf-8"):
        failures.append("Dissertation advisor not visible in static and dynamic lists")
    if '"advisor": "Kenneth M. Cameron"' not in dataset.read_text(encoding="utf-8"):
        failures.append("Dissertation advisor missing from publication data")
    # Ensure the homepage photo cannot overlap its call-to-action buttons,
    # and every page offers the same accessible, persistent theme switch.
    theme_css = stylesheet.read_text(encoding="utf-8")
    theme_js_path = ROOT / "assets/js/theme.js"
    if not theme_js_path.is_file():
        failures.append("Theme script assets/js/theme.js missing")
    else:
        theme_js = theme_js_path.read_text(encoding="utf-8")
        for required in ["localStorage", "data-theme", "aria-pressed", "DOMContentLoaded"]:
            if required not in theme_js:
                failures.append(f"Theme script missing {required}")
    for required in [
        'body.home-page #banner',
        'grid-template-columns: repeat(auto-fit',
        'body.home-page #banner .content .actions',
        'flex-wrap: wrap',
        'html[data-theme="dark"]',
        '.theme-toggle:focus-visible',
    ]:
        if required not in theme_css:
            failures.append(f"Theme stylesheet missing {required}")
    for page_name in PAGES:
        page = (ROOT / page_name).read_text(encoding="utf-8")
        if '<script src="assets/js/theme.js"></script>' not in page:
            failures.append(f"{page_name}: theme script not loaded in the head")
        if 'class="theme-switcher"' not in page:
            failures.append(f"{page_name}: missing sidebar theme switcher")
        if page.count('data-theme-toggle') != (2 if page_name == "index.html" else 1):
            failures.append(f"{page_name}: unexpected count of theme switches")
    if 'theme-toggle-compact' not in homepage:
        failures.append("Homepage missing compact header theme switch")

    return failures


if __name__ == "__main__":
    errors = audit()
    if errors:
        for error in errors:
            print("FAIL:", error, file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: {len(PAGES)} pages use the same {len(EXPECTED)}-link sidebar; all links, anchors and contacts are valid.")
