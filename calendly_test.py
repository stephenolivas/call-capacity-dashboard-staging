#!/usr/bin/env python3
"""
Calendly API Test v3 — Lane 1 Capacity Calculator
===================================================
Finds Lane 1 rep calendars, queries available slots + booked events,
and calculates real capacity per day.
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta

CALENDLY_TOKEN = os.environ.get("CALENDLY_API_KEY", "")
if not CALENDLY_TOKEN:
    print("❌ CALENDLY_API_KEY not set.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {CALENDLY_TOKEN}",
    "Content-Type": "application/json",
}

# Lane 1 rep Calendly usernames (from their scheduling URLs)
LANE_1_CALENDLY_USERS = {
    "robin-modern-amenities": "Robin Perkins",
    "eric-modern-amenities": "Eric Piccione",
    "scott-modern-amenities": "Scott Seymour",
    "christopher-modern-amenities": "Chris Wanke",
    "jakes-modern-amenities": "Jake Skinner",
    "christian-modern-amenities": "Christian Hartwell",
}

# Event type slug to look for on each rep's calendar
TARGET_EVENT_SLUG = "new-vendingpreneur-strategy-call"

results = []

def log(msg):
    print(msg)
    results.append(msg)

def api_get(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code != 200:
        return {"error": resp.status_code, "text": resp.text[:300]}
    return resp.json()


def main():
    log("=" * 60)
    log("CALENDLY API TEST v3 — Lane 1 Capacity")
    log("=" * 60)

    # Step 1: Auth
    log("\n📋 Step 1: Authentication...")
    user_data = api_get("https://api.calendly.com/users/me")
    if "error" in user_data:
        log(f"   ❌ Auth failed: {user_data}")
        write_html(); sys.exit(1)
    org_uri = user_data["resource"]["current_organization"]
    log(f"   ✅ Org: {org_uri}")

    # Step 2: Find Lane 1 rep event type URIs
    log("\n📋 Step 2: Finding Lane 1 rep 'New Vendingpreneur Strategy Call' calendars...")
    all_event_types = []
    params = {"organization": org_uri, "active": "true", "count": 100}
    while True:
        et_data = api_get("https://api.calendly.com/event_types", params)
        if "error" in et_data:
            log(f"   ❌ Error: {et_data}")
            write_html(); sys.exit(1)
        all_event_types.extend(et_data.get("collection", []))
        next_token = et_data.get("pagination", {}).get("next_page_token")
        if next_token:
            params["page_token"] = next_token
        else:
            break
    log(f"   Fetched {len(all_event_types)} event types")

    lane1_event_types = {}  # calendly_username → event type info
    for et in all_event_types:
        url = et.get("scheduling_url", "")
        for cal_user, rep_name in LANE_1_CALENDLY_USERS.items():
            if cal_user in url and TARGET_EVENT_SLUG in url:
                lane1_event_types[cal_user] = {
                    "uri": et["uri"],
                    "name": et["name"],
                    "rep_name": rep_name,
                    "url": url,
                    "duration": et.get("duration"),
                }
                log(f"   ✅ {rep_name}: {et['uri']}")

    missing = set(LANE_1_CALENDLY_USERS.keys()) - set(lane1_event_types.keys())
    if missing:
        log(f"\n   ⚠️ Missing reps: {', '.join(LANE_1_CALENDLY_USERS[m] for m in missing)}")

    # Step 3: Query available times + booked events per day per rep
    log("\n📋 Step 3: Capacity per day (Available + Booked = Total)...")
    log("=" * 80)

    today = datetime.utcnow().date()
    day_range = 7  # Today + 6 forward days

    # Header
    log(f"{'Day':<14} {'Rep':<22} {'Avail':>6} {'Booked':>7} {'Total':>6}")
    log("-" * 60)

    for day_offset in range(day_range):
        check_date = today + timedelta(days=day_offset)
        start = f"{check_date}T00:00:00Z"
        end = f"{check_date}T23:59:59Z"
        day_label = "► TODAY" if day_offset == 0 else check_date.strftime("%a %m/%d")

        day_available = 0
        day_booked = 0

        for cal_user, info in sorted(lane1_event_types.items(), key=lambda x: x[1]["rep_name"]):
            rep_name = info["rep_name"]

            # Available slots
            avail_count = 0
            try:
                avail = api_get("https://api.calendly.com/event_type_available_times", {
                    "event_type": info["uri"],
                    "start_time": start,
                    "end_time": end,
                })
                if "error" not in avail:
                    avail_count = len(avail.get("collection", []))
            except Exception as e:
                avail_count = 0

            # Booked events for this specific event type
            booked_count = 0
            try:
                sched = api_get("https://api.calendly.com/scheduled_events", {
                    "organization": org_uri,
                    "event_type": info["uri"],
                    "min_start_time": start,
                    "max_start_time": end,
                    "status": "active",
                    "count": 100,
                })
                if "error" not in sched:
                    booked_count = len(sched.get("collection", []))
            except Exception as e:
                booked_count = 0

            rep_total = avail_count + booked_count
            day_available += avail_count
            day_booked += booked_count

            log(f"{day_label:<14} {rep_name:<22} {avail_count:>6} {booked_count:>7} {rep_total:>6}")
            day_label = ""  # Only show day label on first rep row

        day_total = day_available + day_booked
        log(f"{'':14} {'TOTAL':<22} {day_available:>6} {day_booked:>7} {day_total:>6}  ← CAPACITY")
        log(f"{'':14} {'Static estimate':22} {'':>6} {'':>7} {'42':>6}  ← Current hardcoded")
        log("-" * 60)

    # Step 4: Also check scheduled events by event NAME (team routing names)
    log("\n📋 Step 4: Today's events by NAME (team routing names)...")
    log("   These are events booked through team /d/ links — may differ from rep calendar counts")
    sched_all = api_get("https://api.calendly.com/scheduled_events", {
        "organization": org_uri,
        "min_start_time": f"{today}T00:00:00Z",
        "max_start_time": f"{today}T23:59:59Z",
        "status": "active",
        "count": 100,
    })
    if "error" not in sched_all:
        by_name = {}
        for ev in sched_all.get("collection", []):
            name = ev.get("name", "?")
            by_name[name] = by_name.get(name, 0) + 1
        for name, count in sorted(by_name.items(), key=lambda x: -x[1]):
            log(f"   {count:>3}x {name}")

    # Step 5: Cross-check — get event_type URIs from today's scheduled events
    log("\n📋 Step 5: Event type URIs from today's scheduled events...")
    log("   Checking if team-routed events point to rep calendars or separate URIs")
    if "error" not in sched_all:
        uri_names = {}
        for ev in sched_all.get("collection", []):
            et_uri = ev.get("event_type", "?")
            name = ev.get("name", "?")
            if et_uri not in uri_names:
                uri_names[et_uri] = {"name": name, "count": 0}
            uri_names[et_uri]["count"] += 1

        known_uris = {info["uri"] for info in lane1_event_types.values()}
        for uri, data in sorted(uri_names.items(), key=lambda x: -x[1]["count"]):
            is_lane1 = "✅ LANE 1 REP" if uri in known_uris else ""
            log(f"   {data['count']:>3}x {data['name']:<45} {is_lane1}")
            log(f"        {uri}")

    log("\n" + "=" * 60)
    log("TEST v3 COMPLETE")
    log("=" * 60)

    write_html()


def write_html():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    body = "\n".join(results)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Calendly Test v3</title>
<style>
  body {{ font-family: monospace; background: #1a1a1a; color: #e0e0e0; padding: 2rem; max-width: 1200px; }}
  pre {{ white-space: pre-wrap; line-height: 1.5; font-size: 13px; }}
  h1 {{ color: #1b7a2e; }}
  .time {{ color: #888; font-size: 12px; }}
</style></head><body>
<h1>Calendly API Test v3 — Lane 1 Capacity</h1>
<p class="time">Last run: {now}</p>
<pre>{body}</pre>
</body></html>"""

    with open("index.html", "w") as f:
        f.write(html)
    print(f"\n✅ Results written to index.html")


if __name__ == "__main__":
    main()
