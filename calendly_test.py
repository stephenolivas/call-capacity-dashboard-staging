#!/usr/bin/env python3
"""
Calendly API Test Script
========================
Runs via GitHub Actions. Outputs results to index.html for GitHub Pages viewing.
Reads CALENDLY_API_KEY from environment variable.
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta

CALENDLY_TOKEN = os.environ.get("CALENDLY_API_KEY", "")
if not CALENDLY_TOKEN:
    print("❌ CALENDLY_API_KEY not set. Add it as a GitHub secret.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {CALENDLY_TOKEN}",
    "Content-Type": "application/json",
}

TARGET_SLUGS = {
    "cxv9-jg6-m53": "Vending Accelerator Call",
    "cxfn-hh2-h8g": "Vendingpreneurs Consultation",
}

results = []

def log(msg):
    print(msg)
    results.append(msg)

def api_get(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def main():
    log("=" * 60)
    log("CALENDLY API TEST")
    log("=" * 60)

    # Step 1: Auth
    log("\n📋 Step 1: Verify authentication...")
    try:
        user_data = api_get("https://api.calendly.com/users/me")
        user_uri = user_data["resource"]["uri"]
        org_uri = user_data["resource"]["current_organization"]
        log(f"   ✅ Authenticated as: {user_data['resource']['name']}")
        log(f"   User URI: {user_uri}")
        log(f"   Org URI: {org_uri}")
    except Exception as e:
        log(f"   ❌ Auth failed: {e}")
        write_html()
        sys.exit(1)

    # Step 2: Find event types
    log("\n📋 Step 2: Finding event type UUIDs...")
    try:
        et_data = api_get("https://api.calendly.com/event_types", {
            "organization": org_uri,
            "active": "true",
            "count": 100,
        })
    except Exception as e:
        log(f"   ❌ Could not fetch event types: {e}")
        write_html()
        sys.exit(1)

    found_types = {}
    for et in et_data.get("collection", []):
        url = et.get("scheduling_url", "")
        for target_slug, target_name in TARGET_SLUGS.items():
            if target_slug in url:
                found_types[target_name] = {
                    "uri": et["uri"],
                    "name": et["name"],
                    "slug": target_slug,
                    "url": url,
                    "duration": et.get("duration"),
                    "kind": et.get("kind"),
                    "pooling_type": et.get("pooling_type"),
                }
                log(f"   ✅ Found: {et['name']}")
                log(f"      URI: {et['uri']}")
                log(f"      Duration: {et.get('duration')} min")
                log(f"      Kind: {et.get('kind')} | Pooling: {et.get('pooling_type')}")

    if len(found_types) < 2:
        log(f"\n   ⚠️ Only found {len(found_types)} of 2 target event types!")
        log("   All active event types in org:")
        for et in et_data.get("collection", []):
            log(f"     - {et['name']} → {et.get('scheduling_url')}")

    # Step 3: Available times + booked events
    log("\n📋 Step 3: Querying available time slots + booked events...")
    today = datetime.utcnow().date()

    for day_offset in range(5):
        check_date = today + timedelta(days=day_offset)
        start = f"{check_date}T00:00:00Z"
        end = f"{check_date}T23:59:59Z"
        day_label = "TODAY" if day_offset == 0 else check_date.strftime("%a %m/%d")

        total_available = 0
        total_booked = 0

        for name, info in found_types.items():
            try:
                avail = api_get("https://api.calendly.com/event_type_available_times", {
                    "event_type": info["uri"],
                    "start_time": start,
                    "end_time": end,
                })
                available_count = len(avail.get("collection", []))
                total_available += available_count
            except Exception as e:
                available_count = f"ERR: {e}"

            try:
                sched = api_get("https://api.calendly.com/scheduled_events", {
                    "organization": org_uri,
                    "event_type": info["uri"],
                    "min_start_time": start,
                    "max_start_time": end,
                    "status": "active",
                    "count": 100,
                })
                booked_count = len(sched.get("collection", []))
                total_booked += booked_count
            except Exception as e:
                booked_count = f"ERR: {e}"

            log(f"   {day_label} | {name}: {available_count} avail, {booked_count} booked")

        total_capacity = total_available + total_booked
        log(f"   {day_label} | TOTAL: {total_available} avail + {total_booked} booked = {total_capacity} capacity")
        log("")

    # Step 4: Raw slots for today
    if found_types:
        log("\n📋 Step 4: Raw available slots for today (first event type)...")
        first_type = list(found_types.values())[0]
        start = f"{today}T00:00:00Z"
        end = f"{today}T23:59:59Z"
        try:
            avail = api_get("https://api.calendly.com/event_type_available_times", {
                "event_type": first_type["uri"],
                "start_time": start,
                "end_time": end,
            })
            for slot in avail.get("collection", []):
                st = slot.get("start_time", "")
                et_time = slot.get("end_time", "")
                remaining = slot.get("invitees_remaining", "?")
                status = slot.get("status", "?")
                log(f"   {st} → {et_time} | remaining: {remaining} | status: {status}")
            log(f"   Total: {len(avail.get('collection', []))} slots")
        except Exception as e:
            log(f"   ERROR: {e}")

    # Step 5: Raw scheduled events for today
    if found_types:
        log("\n📋 Step 5: Raw scheduled events for today (first event type)...")
        try:
            sched = api_get("https://api.calendly.com/scheduled_events", {
                "organization": org_uri,
                "event_type": first_type["uri"],
                "min_start_time": f"{today}T00:00:00Z",
                "max_start_time": f"{today}T23:59:59Z",
                "status": "active",
                "count": 100,
            })
            for ev in sched.get("collection", []):
                st = ev.get("start_time", "")
                et_time = ev.get("end_time", "")
                name = ev.get("name", "?")
                log(f"   {st} → {et_time} | {name}")
            log(f"   Total: {len(sched.get('collection', []))} events")
        except Exception as e:
            log(f"   ERROR: {e}")

    log("\n" + "=" * 60)
    log("TEST COMPLETE")
    log("=" * 60)

    write_html()


def write_html():
    """Write results to index.html for GitHub Pages viewing."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    body = "\n".join(results)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Calendly API Test</title>
<style>
  body {{ font-family: monospace; background: #1a1a1a; color: #e0e0e0; padding: 2rem; }}
  pre {{ white-space: pre-wrap; line-height: 1.6; font-size: 14px; }}
  h1 {{ color: #1b7a2e; }}
  .time {{ color: #888; font-size: 12px; }}
</style></head><body>
<h1>Calendly API Test Results</h1>
<p class="time">Last run: {now}</p>
<pre>{body}</pre>
</body></html>"""

    with open("index.html", "w") as f:
        f.write(html)
    print(f"\n✅ Results written to index.html")


if __name__ == "__main__":
    main()
