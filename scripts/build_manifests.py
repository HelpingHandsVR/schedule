# -*- coding: utf-8 -*-

"""
Manifest build script.
"""

import contextlib
import dataclasses
import datetime
import json
import pathlib
import typing
from zoneinfo import ZoneInfo

import click
import jsonschema
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


SCRIPTS_FOLDER = pathlib.Path(__file__).parent
SCHEMA_FOLDER = SCRIPTS_FOLDER.parent / 'schema'
TEMPLATES_FOLDER = SCRIPTS_FOLDER.parent / 'templates'
OUTPUT_FOLDER = SCRIPTS_FOLDER.parent / 'output'


class EventLaneLanguageInfo(typing.TypedDict):
    abbreviation: str
    native_localization: str
    localized_name: dict[str, str]


class EventLaneMeta(typing.TypedDict):
    default_timezone: str
    language_info: typing.NotRequired[EventLaneLanguageInfo]


class EventLaneRawEventSchedule(typing.TypedDict):
    timezone: typing.NotRequired[str]
    basis: str
    day: typing.Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hour: int
    minute: int
    interval: typing.NotRequired[int]


class EventLaneRawEvent(typing.TypedDict):
    host: str
    name: str
    tags: list[str]
    schedule: EventLaneRawEventSchedule


class EventLaneRawEvents(typing.TypedDict):
    events: list[EventLaneRawEvent]


@dataclasses.dataclass
class EventLaneEvent:
    host: str
    name: str
    tags: list[str]
    basis: datetime.datetime
    timezone: str
    interval: int

    def next_occurrence_after(self, target: datetime.datetime):
        # Calculate the amount of days that have passed since the basis
        days_since_basis = (target - self.basis).days
        # Start search from floored interval from basis
        starting_day_offset = int(days_since_basis / self.interval) * self.interval
        needle = self.basis + datetime.timedelta(days=starting_day_offset)

        while needle < target:
            needle += datetime.timedelta(days=self.interval)

        return needle


@dataclasses.dataclass
class EventLane:
    name: str
    meta: EventLaneMeta
    events: list[EventLaneEvent]


EVENT_LANES: list[EventLane] = []


@contextlib.contextmanager
def report_error(label: str):
    click.secho(f"{label}... ", nl=False)
    try:
        yield
    except BaseException:
        click.secho("FAILED", fg='red')
        raise
    else:
        click.secho("OK", fg='green')


@click.command()
def main():
    click.secho("Reading schemas...", fg='blue')

    with report_error("  Parsing meta schema"):
        with open(SCHEMA_FOLDER / 'template_meta.schema.json', 'r', encoding='utf-8') as fp:
            meta_schema = json.load(fp)

    with report_error("  Parsing events schema"):
        with open(SCHEMA_FOLDER / 'template_events.schema.json', 'r', encoding='utf-8') as fp:
            events_schema = json.load(fp)

    click.secho("Reading event lane templates...", fg='blue')

    for meta_path in TEMPLATES_FOLDER.glob("*/meta.yaml"):
        event_lane_name = meta_path.parent.name
        events_path = meta_path.parent / 'events.yaml'
        click.secho(f"  Found event lane `{event_lane_name}`")

        with report_error("    Parsing meta data"):
            with open(meta_path, 'r', encoding='utf-8') as fp:
                meta_data: EventLaneMeta = load(fp, Loader=Loader)

        with report_error("    Validating meta data against schema"):
            jsonschema.validate(instance=meta_data, schema=meta_schema)

        with report_error("    Parsing events data"):
            with open(events_path, 'r', encoding='utf-8') as fp:
                events_data: EventLaneRawEvents = load(fp, Loader=Loader)

        with report_error("    Validating events data against schema"):
            jsonschema.validate(instance=events_data, schema=events_schema)

        with report_error("    Converting events into agnostic times"):
            events = []

            for raw_event in events_data["events"]:
                # Get timezone name
                timezone = raw_event["schedule"].get("timezone", None) or meta_data["default_timezone"]
                # Calculate basis datetime
                basis = datetime.datetime \
                    .strptime(raw_event["schedule"]["basis"], "%Y-%m-%d") \
                    .replace(
                        hour=raw_event["schedule"]["hour"],
                        minute=raw_event["schedule"]["minute"],
                        tzinfo=ZoneInfo(timezone)
                    )

                # Check days line up
                basis_day = basis.strftime("%A")
                claimed_day = raw_event["schedule"]["day"]
                assert \
                    basis_day == claimed_day, \
                    f"Event '{raw_event['name']}' w/ {raw_event['host']} in `{event_lane_name}` has basis time of {basis:%a %d %b %Y, %I:%M%p} but claims it is a {claimed_day}"

                events.append(EventLaneEvent(
                    host=raw_event['host'],
                    name=raw_event['name'],
                    tags=raw_event['tags'],
                    basis=basis,
                    timezone=timezone,
                    interval=raw_event['schedule'].get('interval', None) or 7
                ))

        event_lane = EventLane(
            name=event_lane_name,
            meta=meta_data,
            events=events
        )

        EVENT_LANES.append(event_lane)

    OUTPUT_FORMATS = (
        (generate_old_format, "old.json"),
    )

    click.secho("Generating output formats...", fg='blue')

    OUTPUT_FOLDER.mkdir(exist_ok=True)

    for callback, target_filename in OUTPUT_FORMATS:
        with report_error(f"    Generating {target_filename}"):
            output = callback()

            with open(OUTPUT_FOLDER / target_filename, 'w', encoding='utf-8') as fp:
                json.dump(output, fp, indent=2)


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


def generate_old_format() -> dict:
    now = datetime.datetime.now(datetime.UTC)
    manifest = []

    for event_lane in EVENT_LANES:
        for event in event_lane.events:
            next_occurrence = event.next_occurrence_after(now)

            manifest.append({
                "id": int(event.basis.timestamp()),
                "language": event_lane.meta['language_info']['abbreviation'],
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


if __name__ == '__main__':
    main()
