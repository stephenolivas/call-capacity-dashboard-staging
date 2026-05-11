#!/usr/bin/env python3
"""
Calendly API Test Script
========================
Run this locally to verify the API works and see what data we get.
Usage: python3 calendly_test.py
"""

import requests
import json
from datetime import datetime, timedelta

CALENDLY_TOKEN = "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiUEFUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzc4NDY2NjI3LCJqdGkiOiJlMjAzNDljMi0xZjRhLTRjMmMtYjBmMS0yYTc1YTM4OTg4ZjkiLCJ1c2VyX3V1aWQiOiJjODExODkxMS02YTA2LTRmM2YtOGE4Yy0zZDNjMzk3MDEyZjYiLCJzY29wZSI6ImF2YWlsYWJpbGl0eTpyZWFkIGF2YWlsYWJpbGl0eTp3cml0ZSBldmVudF90eXBlczpyZWFkIGV2ZW50X3R5cGVzOndyaXRlIGxvY2F0aW9uczpyZWFkIHJvdXRpbmdfZm9ybXM6cmVhZCBzaGFyZXM6d3JpdGUgc2NoZWR1bGVkX2V2ZW50czpyZWFkIHNjaGVkdWxlZF9ldmVudHM6d3JpdGUgc2NoZWR1bGluZ19saW5rczp3cml0ZSBncm91cHM6cmVhZCBvcmdhbml6YXRpb25zOnJlYWQgb3JnYW5pemF0aW9uczp3cml0ZSB1c2VyczpyZWFkIGFjdGl2aXR5X2xvZzpyZWFkIGRhdGFfY29tcGxpYW5jZTp3cml0ZSBvdXRnb2luZ19jb21tdW5pY2F0aW9uczpyZWFkIHdlYmhvb2tzOnJlYWQgd2ViaG9va3M6d3JpdGUifQ.kVaR5Q_2UvRfDnBj5d7eJaThQncdZwq9SD7c_IFTMv3vGOvHwXZtqBloEENEru9eGjuvyioUF_tySQId3WtbDw"

HEADERS = {
    "Authorization": f"Bearer {CALENDLY_TOKEN}",
    "Content-Type": "application/json",
}

# The two Calendly event type URLs we need to track
TARGET_SLUGS = {
    "cxv9-jg6-m53": "Vending Accelerator Call",
    "cxfn-hh2-h8g": "Vendingpreneurs Consultation",
}

def api_get(url, params=None):
    """Make a GET request to the Calendly API."""
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def main():
    print("=" * 60)
    print("CALENDLY API TEST")
    print("=" * 60)

    # Step 1: Get current user info
    print("\n📋 Step 1: Verify authentication...")
    user_data = api_get("https://api.calendly.com/users/me")
    user_uri = user_data["resource"]["uri"]
    org_uri = user_data["resource"]["current_organization"]
    print(f"   ✅ Authenticated as: {user_data['resource']['name']}")
    print(f"   User URI: {user_uri}")
    print(f"   Org URI: {org_uri}")

    # Step 2: List event types to find our two target calendars
    print("\n📋 Step 2: Finding event type UUIDs...")
    et_data = api_get("https://api.calendly.com/event_types", {
        "organization": org_uri,
        "active": "true",
        "count": 100,
    })

    found_types = {}
    for et in et_data.get("collection", []):
        slug = et.get("scheduling_url", "").split("/")[-1] if "/d/" not in et.get("scheduling_url", "") else ""
        # Check both regular and /d/ style URLs
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
                    "type": et.get("type"),
                }
                print(f"   ✅ Found: {et['name']}")
                print(f"      URI: {et['uri']}")
                print(f"      Duration: {et.get('duration')} min")
                print(f"      Kind: {et.get('kind')} | Pooling: {et.get('pooling_type')}")

    if len(found_types) < 2:
        print(f"\n   ⚠️ Only found {len(found_types)} of 2 target event types!")
        print("   All event types in org:")
        for et in et_data.get("collection", []):
            print(f"     - {et['name']} → {et.get('scheduling_url')}")

    # Step 3: Query available times for today and next 3 days
    print("\n📋 Step 3: Querying available time slots...")
    today = datetime.utcnow().date()

    for day_offset in range(4):  # Today + 3 forward days
        check_date = today + timedelta(days=day_offset)
        start = f"{check_date}T00:00:00Z"
        end = f"{check_date}T23:59:59Z"
        day_label = "TODAY" if day_offset == 0 else check_date.strftime("%a %m/%d")

        total_available = 0
        total_booked = 0

        for name, info in found_types.items():
            try:
                # Available slots
                avail = api_get("https://api.calendly.com/event_type_available_times", {
                    "event_type": info["uri"],
                    "start_time": start,
                    "end_time": end,
                })
                available_count = len(avail.get("collection", []))
                total_available += available_count
            except Exception as e:
                available_count = f"ERROR: {e}"

            try:
                # Scheduled (booked) events
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
                booked_count = f"ERROR: {e}"

            print(f"   {day_label} | {name}: {available_count} available, {booked_count} booked")

        total_capacity = total_available + total_booked
        print(f"   {day_label} | TOTAL: {total_available} available + {total_booked} booked = {total_capacity} capacity")
        print()

    # Step 4: Show raw available times for today (first event type) for debugging
    if found_types:
        print("\n📋 Step 4: Raw available time slots for today (first event type)...")
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
                print(f"   {st} → {et_time} (invitees_remaining: {remaining})")
            print(f"   Total: {len(avail.get('collection', []))} slots")
        except Exception as e:
            print(f"   ERROR: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE — copy the output above and share it back")
    print("=" * 60)


if __name__ == "__main__":
    main()
