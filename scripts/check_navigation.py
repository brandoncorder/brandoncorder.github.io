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
    "gallery.html",
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
    ("gallery.html", "Gallery"),
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
        for required in ["localStorage", "data-theme", "aria-pressed", "DOMContentLoaded", "matchMedia", "prefers-color-scheme: dark", "restoreSystem", "data-theme-source"]:
            if required not in theme_js:
                failures.append(f"Theme script missing {required}")
    for required in [
        'body.home-page #banner',
        'grid-template-areas: "intro portrait"',
        'body.home-page #banner .content > ul.actions',
        'flex-wrap: wrap',
        'html[data-theme="dark"]',
        '.theme-toggle:focus-visible',
        '#main .inner ul.actions',
        'flex-wrap: wrap',
        '#fieldwork .fieldwork-title',
        '#main > .inner > .mobile-theme-controls',
    ]:
        if required not in theme_css:
            failures.append(f"Theme stylesheet missing {required}")
    for page_name in PAGES:
        page = (ROOT / page_name).read_text(encoding="utf-8")
        if '<script src="assets/js/theme.js?v=20261111b"></script>' not in page:
            failures.append(f"{page_name}: theme script not loaded in the head")
        if 'class="theme-switcher"' not in page:
            failures.append(f"{page_name}: missing sidebar theme switcher")
        if 'class="mobile-theme-controls"' not in page:
            failures.append(f"{page_name}: missing mobile-only appearance row")
        if page.count('data-theme-toggle') != 2:
            failures.append(f"{page_name}: unexpected count of theme switches")
        if page.count('data-theme-system') != 2:
            failures.append(f"{page_name}: missing system preference reset button")
        if 'assets/css/site-overrides.css?v=20261111d' not in page:
            failures.append(f"{page_name}: stylesheet cache version not updated")
    if 'theme-toggle-compact' in homepage:
        failures.append("Homepage still has a desktop header theme switch")
    if '<h3>PB ### — Plant Geography</h3>' not in teaching or 'Fall 2027' not in teaching:
        failures.append("Fall 2027 Plant Geography course is missing")
    if "Featured by NC State" in teaching or "Read more about my appointment in NC State's faculty introduction" not in teaching:
        failures.append("NC State faculty introduction must be an inline link, not a feature card")

    # Gallery is populated with existing local photos, not external placeholders.
    gallery_html = (ROOT / "gallery.html").read_text(encoding="utf-8")
    local_photos = re.findall(r'<img[^>]*src="(images/[^"]+)"', gallery_html)
    if len(local_photos) < 6:
        failures.append("Gallery should contain at least six botanical photographs")
    for photo in local_photos:
        if not (ROOT / photo).is_file():
            failures.append(f"Gallery photo missing: {photo}")
    if '<li><a href="gallery.html">Gallery</a></li>' not in gallery_html:
        failures.append("Gallery does not include its own navigation link")
    # Gallery uploads must remain automatic: Jekyll builds the image list from
    # images/gallery/ and displays each filename stem unchanged as a caption.
    if not (ROOT / "images/gallery/README.md").is_file():
        failures.append("images/gallery/ upload folder or instructions missing")
    if (ROOT / ".nojekyll").exists():
        failures.append("Jekyll must remain enabled for automatic gallery file listing")
    if gallery_html.splitlines()[:3] != ["---", "layout: null", "---"]:
        failures.append("gallery.html must have Jekyll front matter")
    for required in (
        "site.static_files",
        "photo.path contains '/images/gallery/'",
        'sort: "name"',
        "photo.extname | downcase",
        "photo.basename | escape",
        "photo.path | relative_url | escape",
        "gallery_photo_count",
    ):
        if required not in gallery_html:
            failures.append(f"Automatic gallery template missing: {required}")


    # Preserve the main iNaturalist CTA while removing the broken FA5 leaf icon.
    if 'icon brands fa-leaf' in homepage:
        failures.append("Blank iNaturalist social icon is still present")
    if 'View iNaturalist</a>' not in homepage:
        failures.append("Main iNaturalist profile button was removed")

    # Awards keep the preliminary About Me placeholder, but display recognition
    # in ordered, accessible groups with clearer dates and smaller titles.
    for section_id in ("teaching-awards", "research-awards", "fellowships-grants"):
        if f'id="{section_id}"' not in about:
            failures.append(f"Awards group missing: {section_id}")
    if about.count('class="award-row"') < 12:
        failures.append("Awards timeline appears incomplete")
    for selector in ('.award-row', '.award-year', '.botanical-gallery', '.gallery-item'):
        if selector not in theme_css:
            failures.append(f"Missing gallery/awards CSS selector {selector}")

    # User-confirmed professional and community service.
    for detail in ("Native Orchid Conference", "Botanical Club of Wisconsin",
                   "Botanical Society of America", "American Journal of Botany",
                   "Phytotaxa", "iNaturalist", "NC State University"):
        if detail not in service:
            failures.append(f"Service page missing: {detail}")


    # Verify the uploaded PNG and the icon reference on each page.
    favicon = ROOT / "images/favicon.png"
    if not favicon.is_file():
        failures.append("images/favicon.png is missing")
    elif favicon.read_bytes()[:8] != bytes.fromhex("89504e470d0a1a0a"):
        failures.append("images/favicon.png does not have a valid PNG signature")
    for page_name in PAGES:
        page = (ROOT / page_name).read_text(encoding="utf-8")
        for icon_ref in (
            '<link rel="icon" type="image/png" href="/images/favicon.png?v=20261111-2" />',
            '<link rel="shortcut icon" href="/images/favicon.png?v=20261111-2" type="image/png" />',
            '<link rel="apple-touch-icon" href="/images/favicon.png?v=20261111-2" />',
        ):
            if page.count(icon_ref) != 1:
                failures.append(f"{page_name}: missing or duplicated browser icon: {icon_ref}")
        if 'favicon.png?v=1' in page:
            failures.append(f"{page_name}: old cached favicon URL remains")

    # The optimization source and workflow must stay in sync. The generated
    # icon files are checked after the build workflow has produced them.
    if not (ROOT / "scripts/build_favicons.py").is_file():
        failures.append("Favicon optimization script missing")
    if not (ROOT / ".github/workflows/build-favicons.yml").is_file():
        failures.append("Favicon generation workflow missing")

    return failures


if __name__ == "__main__":
    errors = audit()
    if errors:
        for error in errors:
            print("FAIL:", error, file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: {len(PAGES)} pages use the same {len(EXPECTED)}-link sidebar; all links, anchors and contacts are valid.")
