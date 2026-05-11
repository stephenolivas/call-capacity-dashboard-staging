#!/usr/bin/env python3
"""
Calendly API Test v5 — Team Calendar Available Slots
=====================================================
Queries the TEAM event type URIs (not individual rep calendars)
for available slots. These should match what prospects see on
the booking page.
"""

import os
import sys
import requests
from datetime import datetime, timedelta

CALENDLY_TOKEN = os.environ.get("CALENDLY_API_KEY", "")
if not CALENDLY_TOKEN:
    print("❌ CALENDLY_API_KEY not set.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {CALENDLY_TOKEN}",
    "Content-Type": "application/json",
}

# TEAM event type URIs (discovered from v2 test — these are the /d/ team calendars)
TEAM_CALENDARS = {
    "Vendingprenuers Consultation": "https://api.calendly.com/event_types/3acb4582-147a-4652-ad6b-5effe4a1b755",
    "Vending Accelerator Call": "https://api.calendly.com/event_types/f1a11c05-d0c0-41b7-aaec-b60bf5d96f39",
}

# Individual rep URIs (from v3/v4 — for comparison)
REP_CALENDARS = {
    "Scott Seymour": "https://api.calendly.com/event_types/d0362c50-1e8b-4230-952b-225fb339b4b9",
    "Eric Piccione": "https://api.calendly.com/event_types/d21a1a7d-640b-41b8-9a27-b17c6bd3a446",
    "Christian Hartwell": "https://api.calendly.com/event_types/d79d10d6-7ef7-4aa7-b845-953ea719da97",
    "Robin Perkins": "https://api.calendly.com/event_types/f1748c62-210b-40e3-bdb0-cb1dbecfa258",
    "Chris Wanke": "https://api.calendly.com/event_types/b107544d-2567-4db1-a47d-43c0c766ccad",
    "Jake Skinner": "https://api.calendly.com/event_types/1977d6c2-e5ee-4721-8f33-bf802465c171",
}

results = []

def log(msg):
    print(msg)
    results.append(msg)

def api_get(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code != 200:
        return {"error": resp.status_code, "text": resp.text[:500]}
    return resp.json()


def main():
    log("=" * 70)
    log("CALENDLY v5 — Team Calendar Available Slots")
    log("=" * 70)

    # Auth
    user_data = api_get("https://api.calendly.com/users/me")
    if "error" in user_data:
        log(f"❌ Auth failed: {user_data}")
        write_html(); sys.exit(1)
    org_uri = user_data["resource"]["current_organization"]
    log(f"✅ Authenticated | Org: {org_uri}\n")

    today = datetime.utcnow().date()

    # ═══ SECTION 1: Team Calendar Available Slots ═══
    log("=" * 70)
    log("SECTION 1: TEAM CALENDAR — Available Slots")
    log("These are the /d/ team calendars prospects book through")
    log("=" * 70)

    for cal_name, cal_uri in TEAM_CALENDARS.items():
        log(f"\n📅 {cal_name}")
        log(f"   URI: {cal_uri}")

        for day_offset in range(5):
            check_date = today + timedelta(days=day_offset)
            start = f"{check_date}T00:00:00Z"
            end = f"{check_date}T23:59:59Z"
            day_label = "TODAY" if day_offset == 0 else check_date.strftime("%a %m/%d")

            avail = api_get("https://api.calendly.com/event_type_available_times", {
                "event_type": cal_uri,
                "start_time": start,
                "end_time": end,
            })

            if "error" in avail:
                log(f"   {day_label}: ERROR — {avail}")
            else:
                slots = avail.get("collection", [])
                log(f"   {day_label}: {len(slots)} available slots")

                # Show individual slot times for today
                if day_offset == 0 and slots:
                    for s in slots:
                        st = s.get("start_time", "")[11:16]
                        log(f"      → {st} UTC")

    # ═══ SECTION 2: Comparison — Team vs Individual Rep Calendars ═══
    log(f"\n{'=' * 70}")
    log("SECTION 2: COMPARISON — Team vs Rep Calendars")
    log("Checking if team and individual rep calendars return different numbers")
    log("=" * 70)

    for day_offset in range(5):
        check_date = today + timedelta(days=day_offset)
        start = f"{check_date}T00:00:00Z"
        end = f"{check_date}T23:59:59Z"
        day_label = "TODAY" if day_offset == 0 else check_date.strftime("%a %m/%d")

        # Team total
        team_total = 0
        for cal_name, cal_uri in TEAM_CALENDARS.items():
            avail = api_get("https://api.calendly.com/event_type_available_times", {
                "event_type": cal_uri, "start_time": start, "end_time": end,
            })
            if "error" not in avail:
                team_total += len(avail.get("collection", []))

        # Rep total
        rep_total = 0
        for rep_name, rep_uri in REP_CALENDARS.items():
            avail = api_get("https://api.calendly.com/event_type_available_times", {
                "event_type": rep_uri, "start_time": start, "end_time": end,
            })
            if "error" not in avail:
                rep_total += len(avail.get("collection", []))

        match = "✅ MATCH" if team_total == rep_total else f"⚠️ DIFF (team:{team_total} vs rep:{rep_total})"
        log(f"   {day_label}: Team={team_total}, Reps={rep_total} — {match}")

    # ═══ SECTION 3: Today's Scheduled Events by Calendar Name ═══
    log(f"\n{'=' * 70}")
    log("SECTION 3: TODAY'S EVENTS BY CALENDAR NAME (for Calendar Source)")
    log("=" * 70)

    sched = api_get("https://api.calendly.com/scheduled_events", {
        "organization": org_uri,
        "min_start_time": f"{today}T00:00:00Z",
        "max_start_time": f"{today}T23:59:59Z",
        "status": "active",
        "count": 100,
    })

    if "error" not in sched:
        by_name = {}
        for ev in sched.get("collection", []):
            name = ev.get("name", "Unknown")
            by_name[name] = by_name.get(name, 0) + 1
        log(f"\n   {sum(by_name.values())} total events today:")
        for name, count in sorted(by_name.items(), key=lambda x: -x[1]):
            log(f"   {count:>3}x {name}")
    else:
        log(f"   ERROR: {sched}")

    # ═══ SECTION 4: Tomorrow's Scheduled Events (for comparison) ═══
    tomorrow = today + timedelta(days=1)
    log(f"\n{'=' * 70}")
    log(f"SECTION 4: TOMORROW'S EVENTS BY CALENDAR NAME ({tomorrow})")
    log("=" * 70)

    sched2 = api_get("https://api.calendly.com/scheduled_events", {
        "organization": org_uri,
        "min_start_time": f"{tomorrow}T00:00:00Z",
        "max_start_time": f"{tomorrow}T23:59:59Z",
        "status": "active",
        "count": 100,
    })

    if "error" not in sched2:
        by_name2 = {}
        for ev in sched2.get("collection", []):
            name = ev.get("name", "Unknown")
            by_name2[name] = by_name2.get(name, 0) + 1
        log(f"\n   {sum(by_name2.values())} total events tomorrow:")
        for name, count in sorted(by_name2.items(), key=lambda x: -x[1]):
            log(f"   {count:>3}x {name}")
    else:
        log(f"   ERROR: {sched2}")

    log(f"\n{'=' * 70}")
    log("TEST v5 COMPLETE")
    log("=" * 70)
    write_html()


def write_html():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    body = "\n".join(results)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Calendly v5</title>
<style>
  body {{ font-family: monospace; background: #1a1a1a; color: #e0e0e0; padding: 2rem; max-width: 1200px; }}
  pre {{ white-space: pre-wrap; line-height: 1.5; font-size: 13px; }}
  h1 {{ color: #1b7a2e; }}
  .time {{ color: #888; font-size: 12px; }}
</style></head><body>
<h1>Calendly v5 — Team Calendar Available Slots</h1>
<p class="time">Last run: {now}</p>
<pre>{body}</pre>
</body></html>"""
    with open("index.html", "w") as f:
        f.write(html)
    print(f"\n✅ Results written to index.html")


if __name__ == "__main__":
    main()
