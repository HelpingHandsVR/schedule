# -*- coding: utf-8 -*-

"""
TextMeshPro format, for direct loading in VRChat
"""

import datetime
import textwrap
import typing
from zoneinfo import ZoneInfo

from definitions import EventLane


DISPLAY_TIMEZONES = [ZoneInfo(iana) for iana in [
    "America/Los_Angeles",
    "America/Chicago",
    "America/New_York",
    "Europe/London",
    "Europe/Paris",
    "Australia/Perth",
    "Asia/Tokyo",
]]


EVENT_TEXT_EN = """
<b>{event_name}</b> <size=70%>with {presenter}</size><size=60%>
{timezones}
</size>
""".strip()

EVENT_TEXT_JA = """
<b>{event_name}</b> <size=70%>担当者 {presenter}</size><size=60%>
{timezones}
</size>
""".strip()

EVENT_TEXTS = {"en": EVENT_TEXT_EN, "ja": EVENT_TEXT_JA}

WEEKNAMES_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKNAMES_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]

WEEKNAMES = {"en": WEEKNAMES_EN, "ja": WEEKNAMES_JA}


def generate_textmeshpro_text(event_lanes: list[EventLane], language: str = "en") -> str:
    now = datetime.datetime.now(datetime.UTC)
    manifest: typing.List[typing.Tuple[str, int]] = []

    for event_lane in event_lanes:
        for event in event_lane.events:
            next_occurrence = event.next_occurrence_after(now)

            if next_occurrence is None:
                continue

            manifest.append((
                EVENT_TEXTS[language].format(**{
                    "event_name": event.name,
                    "presenter": event.host,
                    "root_timezone": event.timezone,
                    "timezones": textwrap.indent("\n".join(
                        f"{WEEKNAMES[language][next_occurrence.astimezone(tz).weekday()]} {next_occurrence.astimezone(tz).strftime('%H:%M')} {next_occurrence.astimezone(tz).tzname()}"
                        for tz in DISPLAY_TIMEZONES
                    ), "        ")
                }),
                int((next_occurrence - now).total_seconds() * 1000)
            ))


    manifest.sort(key=lambda pair: pair[1])

    return "\n\n".join(pair[0] for pair in manifest)
