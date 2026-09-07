#!/usr/bin/env python3
# +-------------------------------------------------------------------------+
# | Vibe-coded with an LLM, auto-created & published by Claude (Claude Code),|
# | directed by the author. Verified against one FRITZ!Box; machine-written  |
# | prose/comments may read unevenly. Background: PROVENANCE.md              |
# +-------------------------------------------------------------------------+
"""
Plan C: drive the FRITZ!Box web UI with Playwright.

Only useful if both the REST API and data.lua stop working -- a browser is the
slowest and most fragile of the three channels. Kept here because it is the one
path that cannot break through an API change, and because the findings below
are not documented anywhere.

Tested on: FRITZ!Box 7520, FRITZ!OS 8.25 (build 175.08.25), headless Chromium. 2026-09-07.

THE ONE THING THAT MATTERS
--------------------------
The "IPv4-Adresse dauerhaft zuweisen" checkbox is NOT on the "Allgemein" tab
of the device detail page. It sits on the "Heimnetz" tab. Until that tab is
clicked, the checkbox exists in the DOM but has no layout box (0x0) -- with
display:block and visibility:visible and no hidden attribute. Every clever
explanation for that (isTrusted, content-visibility, view-stack, headless
rendering, CDP viewport) is wrong. It is just an inactive tab panel.

Corollaries:
  * the Apply button (#uiMainApply) exists once per tab panel -- .first picks
    an invisible one; iterate and take the instance with a non-zero box
  * the real <input> is display:none; click the label, not the input
  * headless works fine; xvfb is not needed
  * take a screenshot before measuring the DOM, always

Usage:
    pip install playwright && playwright install chromium
    export FRITZ_URL=http://192.168.178.1 FRITZ_USER=<user>
    read -rs FRITZ_PASSWORD && export FRITZ_PASSWORD
    python3 fritz_ui.py read 192.168.178.50
    python3 fritz_ui.py pin  192.168.178.50

License: CC0 1.0 (public domain dedication)
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SHOTS = Path("/tmp")
VIEWPORT = {"width": 1600, "height": 2400}  # the footer is sticky and tall


def shot(page, name: str) -> None:
    """Screenshots are not optional here. See module docstring."""
    path = SHOTS / f"fritz_ui_{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [shot] {path}")


def login(page, url: str, user: str, password: str) -> None:
    page.goto(url, wait_until="networkidle")
    if user:
        try:
            page.get_by_label("Benutzername").select_option(label=user)
        except Exception:
            pass
    page.get_by_label("FRITZ!Box-Kennwort", exact=False).fill(password)
    page.get_by_role("button", name="Anmelden").click()
    page.wait_for_load_state("networkidle")


def open_device(page, url: str, needle: str) -> None:
    """Open the device detail page and switch to the Heimnetz tab."""
    page.goto(f"{url}/#/network", wait_until="networkidle")
    page.get_by_text(needle, exact=False).first.click()
    page.wait_for_load_state("networkidle")
    shot(page, "1_detail")

    # THE fix: without this the checkbox has no layout box.
    tab = page.get_by_role("tab", name="Heimnetz")
    if tab.count() == 0:
        tab = page.locator("[class*=tab]").get_by_text("Heimnetz", exact=True)
    tab.first.click()
    page.locator("input[name=isIpv4Static]").wait_for(state="attached")
    page.wait_for_function(
        "() => { const e = document.querySelector('input[name=isIpv4Static]');"
        "  return e && e.closest('js3-input-checkbox')"
        "         .getBoundingClientRect().height > 0; }",
        timeout=10000)
    shot(page, "2_heimnetz_tab")


def read_flag(page) -> bool:
    box = page.locator("js3-input-checkbox:has(input[name=isIpv4Static])")
    return box.get_attribute("aria-checked") == "true" or \
        page.locator("input[name=isIpv4Static]").is_checked()


def click_apply(page) -> bool:
    """Find the *visible* apply button; several exist, one per tab panel."""
    handles = page.locator("#uiMainApply")
    for i in range(handles.count()):
        el = handles.nth(i)
        if (el.bounding_box() or {}).get("height"):
            el.scroll_into_view_if_needed()
            el.click()
            return True
    btn = page.get_by_role("button", name="Übernehmen")
    if btn.count():
        btn.last.click()
        return True
    return False


def main() -> int:
    p = argparse.ArgumentParser(prog="fritz-ui")
    p.add_argument("--url", default=os.environ.get("FRITZ_URL", "http://fritz.box"))
    p.add_argument("--user", default=os.environ.get("FRITZ_USER", ""))
    # no --password: see fritz_lease.py
    p.add_argument("--headed", action="store_true", help="not needed; for debugging")
    p.add_argument("action", choices=("read", "pin", "unpin"))
    p.add_argument("device", help="IP, MAC or name as shown in the device list")
    args = p.parse_args()

    password = os.environ.get("FRITZ_PASSWORD")
    if password is None:
        password = (getpass.getpass("FRITZ!Box password: ")
                    if sys.stdin.isatty()
                    else sys.stdin.readline().rstrip("\n"))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed)
        page = browser.new_context(viewport=VIEWPORT).new_page()
        page.on("pageerror", lambda e: print(f"  [pageerror] {e}"))
        try:
            login(page, args.url, args.user, password)
            open_device(page, args.url, args.device)

            current = read_flag(page)
            if args.action == "read":
                print(f"UI-READ {args.device}: static_dhcp="
                      f"{1 if current else 0}")
                return 0

            want = args.action == "pin"
            if current == want:
                print(f"{args.device} already static_dhcp={1 if want else 0}")
                return 0

            page.locator(
                "js3-input-checkbox:has(input[name=isIpv4Static])"
            ).click()
            shot(page, "3_toggled")

            if not click_apply(page):
                print("could not find a visible Übernehmen button", file=sys.stderr)
                return 1
            page.wait_for_load_state("networkidle")
            shot(page, "4_applied")
            print(f"clicked apply for {args.device} -> "
                  f"static_dhcp={1 if want else 0}")
            print("now verify via REST or query.lua -- a click is not a save")
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
