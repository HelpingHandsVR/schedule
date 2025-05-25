# -*- coding: utf-8 -*-

"""
'Old' format - like vrsl.withdevon.xyz's format
"""

import datetime
from zoneinfo import ZoneInfo

from definitions import EventLane


OLD_DISPLAY_TIMEZONES = [
    {"alpha2": "US", "alpha3": "USA", "territory": "United States", "iana": "America/Los_Angeles"},
    {"alpha2": "US", "alpha3": "USA", "territory": "United States", "iana": "America/Chicago"},
    {"alpha2": "US", "alpha3": "USA", "territory": "United States", "iana": "America/New_York"},
    {"alpha2": "GB", "alpha3": "GBR", "territory": "United Kingdom", "iana": "Europe/London"},
    {"alpha2": "FR", "alpha3": "FRA", "territory": "France", "iana": "Europe/Paris"},
    {"alpha2": "RU", "alpha3": "RUS", "territory": "Russia", "iana": "Europe/Moscow"},
    {"alpha2": "AU", "alpha3": "AUS", "territory": "Australia", "iana": "Australia/Perth"},
    {"alpha2": "KR", "alpha3": "KOR", "territory": "Republic of Korea", "iana": "Asia/Seoul"},
]

for OLD_TZ in OLD_DISPLAY_TIMEZONES:
    OLD_TZ["tz"] = ZoneInfo(OLD_TZ["iana"])


def generate_old_format(event_lanes: list[EventLane]) -> dict:
    now = datetime.datetime.now(datetime.UTC)
    manifest = []

    for event_lane in event_lanes:
        for event in event_lane.events:
            next_occurrence = event.next_occurrence_after(now)

            if next_occurrence is None:
                continue

            # ID is generated off the basis timestamp - this should at least make it unique for different times,
            #  but if two events occur at the exact same time, we can't rely on it being enough.
            # Because events are rarely not on 15-minute intervals (900 seconds), we can multiply the timestamp
            #  by 20 for ~18000 typically unused value blocks (enough to fit 14 bits) and then use the ASCII code
            #  of the first two letters of the host name (given one host is unlikely to host two events at the
            #  same time).
            # This is suitably clash-resistant for 99% of cases, but maybe I'll think of a better solution in
            #  the future.
            # It's also OK to represent this as a pure integer because despite JavaScript using 64-bit floating
            #  numbers for all numeric values, the mantissa is large enough that this won't cause problems
            #  within the next few hundred years or so.
            event_id = (
                int(event.basis.timestamp()) * 20 +
                (ord(event.host[0]) << 7) +
                ord(event.host[1])
            )

            manifest.append({
                "id": event_id,
                "language": event_lane.meta['language_info']['abbreviation'],
                "event_name": event.name,
                "presenter": event.host,
                "location": "unknown",
                "timestamp": str(int(next_occurrence.timestamp() * 1000)),
                "time_until": str(int((next_occurrence - now).total_seconds() * 1000)),
                "root_timezone": event.timezone,
                "timezones": [
                    {
                        "iana": display_tz['iana'],
                        "alpha2": display_tz['alpha2'],
                        "alpha3": display_tz['alpha3'],
                        "territory": display_tz['territory'],
                        "text": f"{next_occurrence.astimezone(display_tz['tz']).strftime('%A %I:%M %p')} {next_occurrence.astimezone(display_tz['tz']).tzname()}"
                    }
                    for display_tz in OLD_DISPLAY_TIMEZONES
                ]
            })

    manifest.sort(key=lambda event: int(event['time_until']))

    return manifest
