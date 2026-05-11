#!/usr/bin/env python3
"""
Calendly API Test v4 — Available Slots Only
============================================
Queries each Lane 1 rep's calendar for available time slots.
Capacity = Available (Calendly) + Booked (Close CRM).
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

# Lane 1 rep Calendly usernames → display names
LANE_1_REPS = {
    "robin-modern-amenities": "Robin Perkins",
    "eric-modern-amenities": "Eric Piccione",
    "scott-modern-amenities": "Scott Seymour",
    "christopher-modern-amenities": "Chris Wanke",
    "jakes-modern-amenities": "Jake Skinner",
    "christian-modern-amenities": "Christian Hartwell",
}

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
    log("=" * 70)
    log("CALENDLY v4 — Lane 1 Available Slots")
    log("=" * 70)

    # Auth
    user_data = api_get("https://api.calendly.com/users/me")
    if "error" in user_data:
        log(f"❌ Auth failed: {user_data}")
        write_html(); sys.exit(1)
    org_uri = user_data["resource"]["current_organization"]
    log(f"✅ Authenticated | Org: {org_uri}\n")

    # Find Lane 1 rep event type URIs
    log("Finding Lane 1 rep calendars...")
    all_ets = []
    params = {"organization": org_uri, "active": "true", "count": 100}
    while True:
        data = api_get("https://api.calendly.com/event_types", params)
        if "error" in data:
            log(f"❌ {data}"); write_html(); sys.exit(1)
        all_ets.extend(data.get("collection", []))
        token = data.get("pagination", {}).get("next_page_token")
        if token:
            params["page_token"] = token
        else:
            break

    rep_calendars = {}
    for et in all_ets:
        url = et.get("scheduling_url", "")
        for cal_user, rep_name in LANE_1_REPS.items():
            if cal_user in url and TARGET_EVENT_SLUG in url:
                rep_calendars[cal_user] = {
                    "uri": et["uri"],
                    "rep_name": rep_name,
                    "duration": et.get("duration"),
                }
                log(f"  ✅ {rep_name} ({et.get('duration')}min)")

    missing = set(LANE_1_REPS.keys()) - set(rep_calendars.keys())
    if missing:
        log(f"  ⚠️ Missing: {', '.join(LANE_1_REPS[m] for m in missing)}")

    # Query available slots per rep per day
    log(f"\n{'=' * 70}")
    log(f"AVAILABLE SLOTS PER DAY (from Calendly)")
    log(f"{'=' * 70}")
    log(f"")
    # Header row
    header = f"{'Day':<16} | "
    for cal_user in sorted(rep_calendars.keys(), key=lambda u: rep_calendars[u]["rep_name"]):
        short = rep_calendars[cal_user]["rep_name"].split()[0][:8]
        header += f"{short:>8}"
    header += f" | {'TOTAL':>6}"
    log(header)
    log("-" * 70)

    today = datetime.utcnow().date()

    # Store results for summary
    daily_available = {}

    for day_offset in range(14):  # Full 14-day window like the dashboard
        check_date = today + timedelta(days=day_offset)
        start = f"{check_date}T00:00:00Z"
        end = f"{check_date}T23:59:59Z"

        if day_offset == 0:
            day_label = "► TODAY"
        else:
            day_label = check_date.strftime("%a %m/%d")

        day_total = 0
        rep_counts = {}
        row = f"{day_label:<16} | "

        for cal_user in sorted(rep_calendars.keys(), key=lambda u: rep_calendars[u]["rep_name"]):
            info = rep_calendars[cal_user]
            count = 0
            try:
                avail = api_get("https://api.calendly.com/event_type_available_times", {
                    "event_type": info["uri"],
                    "start_time": start,
                    "end_time": end,
                })
                if "error" not in avail:
                    count = len(avail.get("collection", []))
            except:
                pass

            rep_counts[cal_user] = count
            day_total += count
            row += f"{count:>8}"

        daily_available[check_date.isoformat()] = {
            "total": day_total,
            "per_rep": rep_counts,
        }

        row += f" | {day_total:>6}"
        log(row)

    log("-" * 70)

    # Summary
    log(f"\n{'=' * 70}")
    log("CAPACITY FORMULA")
    log(f"{'=' * 70}")
    log("")
    log("  Capacity = Available Slots (Calendly) + Booked Calls (Close CRM)")
    log("")
    log("  Example: If Calendly shows 35 available and Close shows 20 booked:")
    log("    Capacity = 35 + 20 = 55")
    log("    Utilization = 20 / 55 = 36.4%")
    log("    Available = 35")
    log("")
    log("  vs current static approach:")
    log("    Capacity = 42 (hardcoded)")
    log("    Utilization = 20 / 42 = 47.6%")
    log("    Available = 42 - 20 = 22")
    log("")
    log("  The Calendly number is more accurate because it accounts for:")
    log("  - Reps with time off / blocked calendars")
    log("  - Days with fewer/more slots than average")
    log("  - Weekends and holidays automatically")

    # Raw slot times for one rep on one day (debugging)
    log(f"\n{'=' * 70}")
    log("RAW SLOT TIMES — Tomorrow, first rep with slots")
    log(f"{'=' * 70}")
    tomorrow = today + timedelta(days=1)
    for cal_user in sorted(rep_calendars.keys(), key=lambda u: rep_calendars[u]["rep_name"]):
        info = rep_calendars[cal_user]
        try:
            avail = api_get("https://api.calendly.com/event_type_available_times", {
                "event_type": info["uri"],
                "start_time": f"{tomorrow}T00:00:00Z",
                "end_time": f"{tomorrow}T23:59:59Z",
            })
            if "error" not in avail:
                slots = avail.get("collection", [])
                if slots:
                    log(f"\n  {info['rep_name']} — {len(slots)} slots on {tomorrow}:")
                    for s in slots:
                        st = s.get("start_time", "")[11:16]
                        et = s.get("end_time", "")[11:16]
                        status = s.get("status", "?")
                        remaining = s.get("invitees_remaining", "?")
                        log(f"    {st}-{et} UTC | status: {status} | remaining: {remaining}")
                    break  # Only show first rep with data
        except:
            pass

    log(f"\n{'=' * 70}")
    log("TEST v4 COMPLETE")
    log(f"{'=' * 70}")
    write_html()


def write_html():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    body = "\n".join(results)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Calendly v4</title>
<style>
  body {{ font-family: monospace; background: #1a1a1a; color: #e0e0e0; padding: 2rem; max-width: 1400px; }}
  pre {{ white-space: pre-wrap; line-height: 1.5; font-size: 13px; }}
  h1 {{ color: #1b7a2e; }}
  .time {{ color: #888; font-size: 12px; }}
</style></head><body>
<h1>Calendly v4 — Lane 1 Available Slots</h1>
<p class="time">Last run: {now}</p>
<pre>{body}</pre>
</body></html>"""

    with open("index.html", "w") as f:
        f.write(html)
    print(f"\n✅ Results written to index.html")


if __name__ == "__main__":
    main()
