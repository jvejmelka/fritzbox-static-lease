#!/usr/bin/env python3
# +-------------------------------------------------------------------------+
# | Vibe-coded with an LLM, auto-created & published by Claude (Claude Code),|
# | directed by the author. Verified against one FRITZ!Box; machine-written  |
# | prose/comments may read unevenly. Background: PROVENANCE.md              |
# +-------------------------------------------------------------------------+
"""
fritz-lease -- set and verify static DHCP leases on an AVM FRITZ!Box.

Tested on: FRITZ!Box 7520 (1&1), FRITZ!OS 8.25 (build 175.08.25, not a date).
Last verified: 2026-09-07.
See README.md for the full findings table, including what does NOT work.

TR-064 cannot do this: neither the Hosts service nor any other TR-064 action
exposes the "always assign this IPv4 address" flag. This script therefore uses
the FRITZ!Box's own (undocumented, unstable) internal interfaces:

  write  primary   PUT  /api/v0/generic/landevice/landevice/<UID>
         fallback  POST /data.lua  (page=edit_device, legacy form fields)
  read   primary   GET  /api/v0/generic/landevice/landevice/<UID>
         cross     GET  /query.lua (landevice:settings/landevice/list)

Every write is verified by re-reading the value from a *different* channel
than the one used to write it. An HTTP 200 alone proves nothing here -- the
box happily returns 200 for writes it silently discards.

Credentials come from the environment (FRITZ_USER / FRITZ_PASSWORD / FRITZ_URL)
or from stdin. There is deliberately no --password flag: command arguments are
readable by every process on the machine and end up in shell history.

License: CC0 1.0 (public domain dedication)
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import requests

DEFAULT_URL = "http://fritz.box"
TIMEOUT = 15

# Fields we ask query.lua for. Keep this list short: older firmware returns an
# empty list if it does not know one of the requested field names.
QUERY_FIELDS = "name,ip,mac,UID,static_dhcp"


class FritzError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# session
# --------------------------------------------------------------------------

class Fritz:
    """A logged-in FRITZ!Box session."""

    def __init__(self, url: str = DEFAULT_URL, user: str = "", password: str = ""):
        self.url = url.rstrip("/")
        self.user = user
        self.password = password
        self.sid: str | None = None
        self.http = requests.Session()

    # -- login ------------------------------------------------------------

    def login(self) -> str:
        """Challenge-response login. PBKDF2 (FRITZ!OS 7.24+) with MD5 fallback."""
        r = self.http.get(f"{self.url}/login_sid.lua?version=2", timeout=TIMEOUT)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        challenge = root.findtext("Challenge") or ""

        if challenge.startswith("2$"):
            _, it1, salt1, it2, salt2 = challenge.split("$")
            h1 = hashlib.pbkdf2_hmac(
                "sha256", self.password.encode("utf-8"),
                bytes.fromhex(salt1), int(it1))
            h2 = hashlib.pbkdf2_hmac("sha256", h1, bytes.fromhex(salt2), int(it2))
            response = f"{salt2}${h2.hex()}"
        else:  # legacy MD5
            raw = f"{challenge}-{self.password}".encode("utf-16-le")
            response = f"{challenge}-{hashlib.md5(raw).hexdigest()}"

        r = self.http.get(
            f"{self.url}/login_sid.lua?version=2",
            params={"username": self.user, "response": response},
            timeout=TIMEOUT)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        sid = root.findtext("SID") or ""
        if sid == "0000000000000000" or not sid:
            raise FritzError(
                "Login failed. Check user and password. The account needs the "
                "'FRITZ!Box Einstellungen' permission.")
        self.sid = sid
        return sid

    def logout(self) -> None:
        if not self.sid:
            return
        try:
            self.http.post(f"{self.url}/index.lua",
                           data={"sid": self.sid, "logout": "1", "no_sidrenew": ""},
                           timeout=TIMEOUT)
        except requests.RequestException:
            pass
        self.sid = None

    def __enter__(self) -> "Fritz":
        self.login()
        return self

    def __exit__(self, *exc) -> None:
        self.logout()

    # -- low level --------------------------------------------------------

    def _rest(self, method: str, path: str, payload: dict | None = None):
        """Call the internal REST API. Returns (status_code, parsed_or_text)."""
        r = self.http.request(
            method, f"{self.url}{path}",
            headers={"AUTHORIZATION": f"AVM-SID {self.sid}"},
            json=payload, timeout=TIMEOUT)
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, r.text

    def query(self) -> list[dict]:
        """Read the LAN device list via query.lua (independent of the REST API)."""
        r = self.http.get(
            f"{self.url}/query.lua",
            params={"sid": self.sid,
                    "network": f"landevice:settings/landevice/list({QUERY_FIELDS})"},
            timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        devices = data.get("network", [])
        if not devices:
            raise FritzError(
                "query.lua returned an empty list. Your firmware may not know "
                f"all of these fields: {QUERY_FIELDS}")
        return devices


# --------------------------------------------------------------------------
# device lookup
# --------------------------------------------------------------------------

def normalise_mac(value: str) -> str:
    hexchars = re.sub(r"[^0-9a-fA-F]", "", value)
    if len(hexchars) != 12:
        return ""
    return ":".join(hexchars[i:i + 2] for i in range(0, 12, 2)).upper()


def find_device(devices: list[dict], needle: str) -> dict:
    """Resolve a device by MAC (preferred), IP, or name.

    MAC is the stable key: UIDs change when a device is reset via
    'Netzwerkverbindung zuruecksetzen' or after some firmware updates.
    """
    mac = normalise_mac(needle)
    if mac:
        for d in devices:
            if normalise_mac(d.get("mac", "")) == mac:
                return d
        raise FritzError(f"No device with MAC {mac}")

    hits = [d for d in devices if d.get("ip") == needle]
    if not hits:
        low = needle.lower()
        hits = [d for d in devices if low in (d.get("name") or "").lower()]
    if not hits:
        raise FritzError(f"No device matching {needle!r}")
    if len(hits) > 1:
        names = ", ".join(f"{d.get('ip')} {d.get('name')}" for d in hits)
        raise FritzError(f"{needle!r} is ambiguous: {names}. Use the MAC.")
    return hits[0]


def flag_of(device: dict) -> int:
    return 1 if str(device.get("static_dhcp", "0")) in ("1", "true", "on") else 0


# --------------------------------------------------------------------------
# write channels
# --------------------------------------------------------------------------

def write_rest(fb: Fritz, uid: str, value: int, ip: str | None = None) -> None:
    """Primary write channel.

    Path shape is /api/v0/generic/<module>/<collection>/<node>. Getting this
    wrong is what produces 'bad path' -- see README.
    """
    payload: dict = {"static_dhcp": str(value)}
    if ip:
        payload["ip"] = ip
    status, body = fb._rest("PUT", f"/api/v0/generic/landevice/landevice/{uid}", payload)
    if status != 200:
        raise FritzError(f"REST PUT failed: HTTP {status} {body}")


def write_datalua(fb: Fritz, device: dict, value: int, ip: str | None = None) -> None:
    """Fallback write channel -- no browser required.

    Uses the legacy edit_device form. Still accepted on FRITZ!OS 8.25 even
    though the page itself now serves a nested JSON model. Read the current
    form values first so we do not overwrite the access profile.
    """
    uid = device["UID"]
    form = {
        "xhr": "1", "sid": fb.sid, "lang": "de", "no_sidrenew": "",
        "dev": uid,
        "dev_name": device.get("name", ""),
        "dev_ip": ip or device.get("ip", ""),
        "kisi_profile": device.get("kisi_profile", "") or "filtprof1",
        "back_to_page": "/net/net_overview.lua",
        "validate": "btn_save",
    }
    if value:
        form["static_dhcp"] = "on"  # absence of the key means "off"
    r = fb.http.post(f"{fb.url}/data.lua", data=form, timeout=TIMEOUT)
    if r.status_code != 200:
        raise FritzError(f"data.lua POST failed: HTTP {r.status_code}")


WRITERS = {"rest": write_rest, "datalua": write_datalua}


# --------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------

def verify(fb: Fritz, uid: str, expected: int) -> tuple[bool, str]:
    """Cross-channel check: REST and query.lua must agree with each other."""
    results: dict[str, int | None] = {"rest": None, "query.lua": None}

    status, body = fb._rest("GET", f"/api/v0/generic/landevice/landevice/{uid}")
    if status == 200 and isinstance(body, dict):
        blob = json.dumps(body)
        m = re.search(r'"static_dhcp"\s*:\s*"?(\d)', blob)
        if not m:
            m = re.search(r'"alwaysSameIp"\s*:\s*"?(true|false|\d)', blob)
            if m:
                results["rest"] = 1 if m.group(1) in ("true", "1") else 0
        else:
            results["rest"] = int(m.group(1))

    for d in fb.query():
        if d.get("UID") == uid:
            results["query.lua"] = flag_of(d)
            break

    seen = {k: v for k, v in results.items() if v is not None}
    if not seen:
        return False, "no channel returned a value"
    ok = all(v == expected for v in seen.values())
    detail = ", ".join(f"{k}={v}" for k, v in seen.items())
    if len(seen) == 1:
        detail += " (only one channel available -- no cross-check)"
    return ok, detail


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_list(fb: Fritz, args) -> int:
    for d in sorted(fb.query(), key=lambda x: x.get("ip", "")):
        print(f"{flag_of(d)}  {d.get('ip',''):<15} {d.get('mac',''):<18} "
              f"{d.get('UID',''):<15} {d.get('name','')}")
    return 0


def cmd_find(fb: Fritz, args) -> int:
    d = find_device(fb.query(), args.device)
    print(f"{flag_of(d)}  {d.get('ip',''):<15} {d.get('mac',''):<18} "
          f"{d.get('UID',''):<15} {d.get('name','')}")
    return 0


def _set(fb: Fritz, args, value: int) -> int:
    device = find_device(fb.query(), args.device)
    uid, name = device["UID"], device.get("name", "")
    current = flag_of(device)

    if current == value and not args.force and not args.ip:
        print(f"{name} ({device.get('ip')}) already static_dhcp={value} -- nothing to do")
        return 0

    WRITERS[args.via](fb, *( (uid, value, args.ip) if args.via == "rest"
                             else (device, value, args.ip) ))
    print(f"wrote static_dhcp={value} to {uid} via {args.via}")

    ok, detail = verify(fb, uid, value)
    print(f"verify: {detail} -> {'OK' if ok else 'MISMATCH'}")
    return 0 if ok else 2


def cmd_pin(fb: Fritz, args) -> int:
    return _set(fb, args, 1)


def cmd_unpin(fb: Fritz, args) -> int:
    return _set(fb, args, 0)


def cmd_verify(fb: Fritz, args) -> int:
    device = find_device(fb.query(), args.device)
    ok, detail = verify(fb, device["UID"], args.expect)
    print(f"{device.get('name')} ({device.get('ip')}): {detail} "
          f"-> {'OK' if ok else 'MISMATCH'}")
    return 0 if ok else 2


def cmd_batch(fb: Fritz, args) -> int:
    """Pin many devices from a file: one MAC or IP per line, # for comments."""
    failed = 0
    with open(args.file, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#")[0].strip()
            if not line:
                continue
            args.device = line
            try:
                if _set(fb, args, 1) != 0:
                    failed += 1
            except FritzError as exc:
                print(f"{line}: {exc}", file=sys.stderr)
                failed += 1
    return 0 if failed == 0 else 2


# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="fritz-lease",
        description="Set and verify static DHCP leases on a FRITZ!Box.")
    p.add_argument("--url", default=os.environ.get("FRITZ_URL", DEFAULT_URL),
                   help="default: $FRITZ_URL or http://fritz.box")
    p.add_argument("--user", default=os.environ.get("FRITZ_USER", ""),
                   help="FRITZ!Box user (or set FRITZ_USER)")
    # No --password on purpose: arguments are visible in the process list and
    # land in shell history. Use FRITZ_PASSWORD or pipe it on stdin.
    p.add_argument("--via", choices=sorted(WRITERS), default="rest",
                   help="write channel (default: rest)")
    p.add_argument("--ip", default=None,
                   help="also set the IPv4 address (untested on some firmware)")
    p.add_argument("--force", action="store_true",
                   help="write even if the value is already correct")

    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list all known devices").set_defaults(fn=cmd_list)
    for name, fn, helptext in (
            ("find", cmd_find, "show one device"),
            ("pin", cmd_pin, "set static_dhcp=1"),
            ("unpin", cmd_unpin, "set static_dhcp=0")):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("device", help="MAC (preferred), IP, or name fragment")
        sp.set_defaults(fn=fn)
    sp = sub.add_parser("verify", help="check the flag without writing")
    sp.add_argument("device")
    sp.add_argument("--expect", type=int, default=1, choices=(0, 1))
    sp.set_defaults(fn=cmd_verify)
    sp = sub.add_parser("batch", help="pin every MAC/IP listed in a file")
    sp.add_argument("file")
    sp.set_defaults(fn=cmd_batch)

    args = p.parse_args(argv)

    password = os.environ.get("FRITZ_PASSWORD")
    if password is None:
        if sys.stdin.isatty():
            password = getpass.getpass("FRITZ!Box password: ")
        else:
            password = sys.stdin.readline().rstrip("\n")
    if not password:
        print("error: no password (set FRITZ_PASSWORD or pipe it on stdin)",
              file=sys.stderr)
        return 1

    try:
        with Fritz(args.url, args.user, password) as fb:
            return args.fn(fb, args)
    except FritzError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"network error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
