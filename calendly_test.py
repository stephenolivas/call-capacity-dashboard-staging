#!/usr/bin/env python3
"""
Calendly API Test v2 — Finding Team Calendars
==============================================
Explores routing forms, team events, and alternative endpoints
to locate the /d/ team calendar URLs.
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

# The /d/ slugs we're looking for
TARGET_SLUGS = ["cxv9-jg6-m53", "cxfn-hh2-h8g"]
TARGET_NAMES = ["Vending Accelerator Call", "Vendingpreneurs Consultation"]

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
    log("CALENDLY API TEST v2 — Finding Team Calendars")
    log("=" * 60)

    # Step 1: Auth + get org info
    log("\n📋 Step 1: Authentication...")
    user_data = api_get("https://api.calendly.com/users/me")
    if "error" in user_data:
        log(f"   ❌ Auth failed: {user_data}")
        write_html()
        sys.exit(1)
    user_uri = user_data["resource"]["uri"]
    org_uri = user_data["resource"]["current_organization"]
    log(f"   ✅ User: {user_data['resource']['name']}")
    log(f"   Org URI: {org_uri}")

    # Step 2: Check routing forms
    log("\n📋 Step 2: Checking routing forms...")
    rf_data = api_get("https://api.calendly.com/routing_forms", {
        "organization": org_uri,
        "count": 100,
    })
    if "error" in rf_data:
        log(f"   ❌ Routing forms error: {rf_data}")
    else:
        forms = rf_data.get("collection", [])
        log(f"   Found {len(forms)} routing form(s)")
        for form in forms:
            name = form.get("name", "Unnamed")
            uri = form.get("uri", "")
            status = form.get("status", "?")
            log(f"   - {name} | status: {status}")
            log(f"     URI: {uri}")
            # Check for our target slugs in any field
            form_str = json.dumps(form)
            for slug in TARGET_SLUGS:
                if slug in form_str:
                    log(f"     ✅ Contains target slug: {slug}")
            # Show form questions/routing rules if available
            for key in ["questions", "routing_rules"]:
                if key in form:
                    log(f"     Has {key}: {len(form[key])} entries")

    # Step 3: Check ALL event types (including inactive, paginated)
    log("\n📋 Step 3: All event types (checking for /d/ URLs and target names)...")
    all_event_types = []
    next_page = "https://api.calendly.com/event_types"
    params = {"organization": org_uri, "count": 100}
    page = 1
    while next_page:
        et_data = api_get(next_page, params if page == 1 else None)
        if "error" in et_data:
            log(f"   ❌ Event types error: {et_data}")
            break
        batch = et_data.get("collection", [])
        all_event_types.extend(batch)
        next_page = et_data.get("pagination", {}).get("next_page_token")
        if next_page:
            next_page = f"https://api.calendly.com/event_types?page_token={next_page}&count=100&organization={org_uri}"
        else:
            next_page = None
        page += 1

    log(f"   Total event types found: {len(all_event_types)}")

    # Search for target slugs and names
    matches = []
    for et in all_event_types:
        url = et.get("scheduling_url", "")
        name = et.get("name", "")
        et_str = json.dumps(et)

        is_match = False
        for slug in TARGET_SLUGS:
            if slug in et_str:
                is_match = True
                log(f"\n   ✅ SLUG MATCH: {slug}")
        for tname in TARGET_NAMES:
            if tname.lower() in name.lower():
                is_match = True
                log(f"\n   ✅ NAME MATCH: {tname}")

        if is_match:
            matches.append(et)
            log(f"   Name: {name}")
            log(f"   URI: {et.get('uri')}")
            log(f"   URL: {url}")
            log(f"   Kind: {et.get('kind')} | Type: {et.get('type')}")
            log(f"   Pooling: {et.get('pooling_type')}")
            log(f"   Active: {et.get('active')}")
            log(f"   Duration: {et.get('duration')} min")

    if not matches:
        log("\n   ⚠️ No matches found by slug or name")
        # Show event types with 'vending' or 'consultation' or 'accelerator' in name
        log("\n   Event types containing 'vending', 'consultation', or 'accelerator':")
        for et in all_event_types:
            name = et.get("name", "").lower()
            if "vending" in name or "consultation" in name or "accelerator" in name:
                log(f"   - {et.get('name')} | {et.get('scheduling_url')} | kind: {et.get('kind')} | active: {et.get('active')}")

    # Step 4: Try direct lookup of /d/ URLs
    log("\n📋 Step 4: Trying direct event type lookup by slug...")
    for slug in TARGET_SLUGS:
        # Try various API patterns
        for attempt_url in [
            f"https://api.calendly.com/event_types?organization={org_uri}&slug={slug}",
        ]:
            resp = api_get(attempt_url)
            if "error" not in resp:
                matches_found = [et for et in resp.get("collection", []) if slug in json.dumps(et)]
                if matches_found:
                    log(f"   ✅ Found {slug} via direct lookup!")
                    for m in matches_found:
                        log(f"      {m.get('name')} → {m.get('uri')}")

    # Step 5: Check teams/groups in org
    log("\n📋 Step 5: Checking org groups/teams...")
    groups_data = api_get("https://api.calendly.com/groups", {
        "organization": org_uri,
    })
    if "error" in groups_data:
        log(f"   Groups endpoint: {groups_data}")
    else:
        groups = groups_data.get("collection", [])
        log(f"   Found {len(groups)} group(s)")
        for g in groups:
            log(f"   - {g.get('name', 'Unnamed')} | URI: {g.get('uri')}")
            log(f"     Members: {len(g.get('member_ids', []))}")

    # Step 6: Try fetching scheduled events directly (without event_type filter)
    log("\n📋 Step 6: Today's scheduled events (all types, no filter)...")
    today = datetime.utcnow().date()
    sched = api_get("https://api.calendly.com/scheduled_events", {
        "organization": org_uri,
        "min_start_time": f"{today}T00:00:00Z",
        "max_start_time": f"{today}T23:59:59Z",
        "status": "active",
        "count": 100,
    })
    if "error" not in sched:
        events = sched.get("collection", [])
        log(f"   Found {len(events)} scheduled events today")
        # Group by event type
        by_type = {}
        for ev in events:
            et_uri = ev.get("event_type", "unknown")
            et_name = ev.get("name", "?")
            key = f"{et_name}"
            by_type[key] = by_type.get(key, 0) + 1
            # Check if any match our targets
            ev_str = json.dumps(ev)
            for slug in TARGET_SLUGS:
                if slug in ev_str:
                    log(f"   ✅ FOUND TARGET SLUG in scheduled event: {slug}")
                    log(f"      Event: {ev.get('name')} | {ev.get('start_time')}")
                    log(f"      Event Type URI: {et_uri}")

        log("   Events by type:")
        for name, count in sorted(by_type.items(), key=lambda x: -x[1]):
            log(f"     {count}x {name}")
    else:
        log(f"   ❌ Error: {sched}")

    # Step 7: Dump full JSON of first few event types for debugging
    log("\n📋 Step 7: Full JSON of first 3 event types (for debugging)...")
    for et in all_event_types[:3]:
        log(f"\n   --- {et.get('name')} ---")
        for key, val in et.items():
            if key not in ("profile",):  # skip large nested objects
                log(f"   {key}: {val}")

    log("\n" + "=" * 60)
    log("TEST v2 COMPLETE")
    log("=" * 60)

    write_html()


def write_html():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    body = "\n".join(results)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Calendly API Test v2</title>
<style>
  body {{ font-family: monospace; background: #1a1a1a; color: #e0e0e0; padding: 2rem; max-width: 1200px; }}
  pre {{ white-space: pre-wrap; line-height: 1.6; font-size: 13px; }}
  h1 {{ color: #1b7a2e; }}
  .time {{ color: #888; font-size: 12px; }}
</style></head><body>
<h1>Calendly API Test v2 — Finding Team Calendars</h1>
<p class="time">Last run: {now}</p>
<pre>{body}</pre>
</body></html>"""

    with open("index.html", "w") as f:
        f.write(html)
    print(f"\n✅ Results written to index.html")


if __name__ == "__main__":
    main()
