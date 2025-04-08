# -*- coding: utf-8 -*-

"""
Manifest build script.
"""

import contextlib
import datetime
import json
import pathlib
from zoneinfo import ZoneInfo

import click
import jsonschema
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from definitions import EventLane, EventLaneEvent, EventLaneMeta, EventLaneRawEvents
from formats.old import generate_old_format


SCRIPTS_FOLDER = pathlib.Path(__file__).parent
SCHEMA_FOLDER = SCRIPTS_FOLDER.parent / 'schema'
TEMPLATES_FOLDER = SCRIPTS_FOLDER.parent / 'templates'
OUTPUT_FOLDER = SCRIPTS_FOLDER.parent / 'output'


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

    event_lanes: list[EventLane] = []

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

        event_lanes.append(event_lane)

    OUTPUT_FORMATS = (
        (generate_old_format, "old.json"),
    )

    click.secho("Generating output formats...", fg='blue')

    OUTPUT_FOLDER.mkdir(exist_ok=True)

    for callback, target_filename in OUTPUT_FORMATS:
        with report_error(f"    Generating {target_filename}"):
            output = callback(event_lanes)

            with open(OUTPUT_FOLDER / target_filename, 'w', encoding='utf-8') as fp:
                json.dump(output, fp, indent=2)


if __name__ == '__main__':
    main()
