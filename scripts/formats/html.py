# -*- coding: utf-8 -*-

"""
HTML format, for GitHub Pages
"""

import datetime
import pathlib
import typing
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

from definitions import EventLane



THIS_FILE = pathlib.Path(__file__)
TEMPLATES_DIRECTORY = THIS_FILE.parent.parent / "templates"

JINJA_ENVIRONMENT = Environment(loader=FileSystemLoader(TEMPLATES_DIRECTORY))

DISPLAY_TIMEZONES = [ZoneInfo(iana) for iana in [
    "America/Los_Angeles",
    "America/Chicago",
    "America/New_York",
    "Europe/London",
    "Europe/Paris",
    "Australia/Perth",
    "Asia/Tokyo",
]]

WEEKNAMES_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKNAMES_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]

WEEKNAMES = {"en": WEEKNAMES_EN, "ja": WEEKNAMES_JA}


def generate_html(event_lanes: list[EventLane], language: str = "en") -> str:
    now = datetime.datetime.now(datetime.UTC)
    manifest: typing.List[typing.Tuple[typing.Dict[str, typing.Any], int]] = []

    template = JINJA_ENVIRONMENT.get_template(f"html_template.{language}.jinja2")

    for event_lane in event_lanes:
        for event in event_lane.events:
            next_occurrence = event.next_occurrence_after(now)

            if next_occurrence is None:
                continue

            manifest.append(({
                "event_name": event.name,
                "event_lane": event_lane.name,
                "presenter": event.host,
                "root_timezone": event.timezone,
                "timezones": [
                    f"{WEEKNAMES[language][next_occurrence.astimezone(tz).weekday()]} {next_occurrence.astimezone(tz).strftime('%H:%M')} {next_occurrence.astimezone(tz).tzname()}"
                    for tz in DISPLAY_TIMEZONES
                ],
            }, int((next_occurrence - now).total_seconds() * 1000)))


    manifest.sort(key=lambda pair: pair[1])

    from formats.all import OUTPUT_FORMATS

    return template.render(
        manifest=[event[0] for event in manifest],
        generation_time=now.isoformat(),
        output_formats=OUTPUT_FORMATS,
    ) + "\n"
