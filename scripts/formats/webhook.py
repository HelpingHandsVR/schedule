# -*- coding: utf-8 -*-

"""
Webhook, technically not a format, but allows us to send webhook messages
"""

import datetime
import collections
from zoneinfo import ZoneInfo

import discord

from definitions import EventLane, EventLaneEvent


def calculate_notable_date_emojis(year: int) -> dict[tuple[int, int], str]:
    notable_date_emojis = {
        (1,  1):  "🎉",   # New Year's Day
        (2,  14): "❤️",   # Valentine’s Day
        (3,  13): "🦻",   # Start of National Deaf History Month
        (3,  17): "🍀",   # St. Patrick’s Day
        (4,  1):  "🥳",   # April Fools Day
        (4,  8):  "🎓",   # Anniversary of the founding of Gallaudet University
        (4,  22): "🌱",   # Earth Day
        (6,  5):  "🌍",   # World Environment Day
        (7,  26): "⚖️",   # Americans with Disabilities Act (ADA) Anniversary
        (9,  21): "🕊️",   # International Day of Peace
        (9,  23): "🤟",   # International Day of Sign Languages
        (10, 31): "🎃",   # Halloween
        (12, 24): "🎄",   # Christmas Eve
        (12, 25): "🎅",   # Christmas Day
        (12, 26): "📦",   # Boxing Day get it it's a box haha
        (12, 31): "🎆",   # New Year's Eve
    }

    return notable_date_emojis


CLOCK_EMOJIS: list[tuple[float, str]] = [
    (-01.0, "\N{CLOCK FACE ELEVEN OCLOCK}"),
    (-00.5, "\N{CLOCK FACE ELEVEN-THIRTY}"),
    (+00.0, "\N{CLOCK FACE TWELVE OCLOCK}"),
    (+00.5, "\N{CLOCK FACE TWELVE-THIRTY}"),
    (+01.0, "\N{CLOCK FACE ONE OCLOCK}"),
    (+01.5, "\N{CLOCK FACE ONE-THIRTY}"),
    (+02.0, "\N{CLOCK FACE TWO OCLOCK}"),
    (+02.5, "\N{CLOCK FACE TWO-THIRTY}"),
    (+03.0, "\N{CLOCK FACE THREE OCLOCK}"),
    (+03.5, "\N{CLOCK FACE THREE-THIRTY}"),
    (+04.0, "\N{CLOCK FACE FOUR OCLOCK}"),
    (+04.5, "\N{CLOCK FACE FOUR-THIRTY}"),
    (+05.0, "\N{CLOCK FACE FIVE OCLOCK}"),
    (+05.5, "\N{CLOCK FACE FIVE-THIRTY}"),
    (+06.0, "\N{CLOCK FACE SIX OCLOCK}"),
    (+06.5, "\N{CLOCK FACE SIX-THIRTY}"),
    (+07.0, "\N{CLOCK FACE SEVEN OCLOCK}"),
    (+07.5, "\N{CLOCK FACE SEVEN-THIRTY}"),
    (+08.0, "\N{CLOCK FACE EIGHT OCLOCK}"),
    (+08.5, "\N{CLOCK FACE EIGHT-THIRTY}"),
    (+09.0, "\N{CLOCK FACE NINE OCLOCK}"),
    (+09.5, "\N{CLOCK FACE NINE-THIRTY}"),
    (+10.0, "\N{CLOCK FACE TEN OCLOCK}"),
    (+10.5, "\N{CLOCK FACE TEN-THIRTY}"),
    (+11.0, "\N{CLOCK FACE ELEVEN OCLOCK}"),
    (+11.5, "\N{CLOCK FACE ELEVEN-THIRTY}"),
    (+12.0, "\N{CLOCK FACE TWELVE OCLOCK}"),
    (+12.5, "\N{CLOCK FACE TWELVE-THIRTY}"),
    (+13.0, "\N{CLOCK FACE ONE OCLOCK}"),
    (+13.5, "\N{CLOCK FACE ONE-THIRTY}"),
]

TIMEZONE_PAIRS = (
    ("US", ZoneInfo("Pacific/Honolulu")),
    ("US", ZoneInfo("America/Los_Angeles")),
    ("US", ZoneInfo("America/Chicago")),
    ("US", ZoneInfo("America/New_York")),
    ("UN", datetime.UTC),
    ("GB", ZoneInfo("Europe/London")),
    ("FR", ZoneInfo("Europe/Paris")),
    ("AU", ZoneInfo("Australia/Sydney")),
    ("KR", ZoneInfo("Asia/Seoul")),
)


def to_regionals(text: str):
    mapping = 0x1f1e6 - 0x61

    return ''.join(chr(ord(x) + mapping) for x in text.lower())


def send_webhooks(event_lanes: list[EventLane]) -> dict:
    # Calculate for each event lane, as it changes how we calculate what counts as 'today'
    for event_lane in event_lanes:
        # We can't work with no webhook..
        if not event_lane.webhook:
            continue

        # Use New York time at 5am
        event_lane_zone = ZoneInfo(event_lane.meta["default_timezone"])
        now = datetime.datetime.now(event_lane_zone)
        last_monday_5am = (now - datetime.timedelta(days=now.weekday())).replace(hour=5, minute=0, second=0, microsecond=0)

        # If it's, for example, 4am on a Monday, we still don't consider the week turned over yet so use last week
        if last_monday_5am > now:
            last_monday_5am = last_monday_5am - datetime.timedelta(days=7)

        next_monday_5am = last_monday_5am + datetime.timedelta(days=7)

        lane_messages = {}

        events_by_day: dict[int, list[tuple[EventLaneEvent, datetime.datetime]]] = collections.defaultdict(list)

        for event in event_lane.events:
            next_occurrence = event.next_occurrence_after(last_monday_5am)

            # If this event doesn't next occur within this week then we don't care about it right now
            if next_occurrence < last_monday_5am or next_occurrence >= next_monday_5am:
                continue

            # Add the event and its next time to the list
            events_by_day[next_occurrence.astimezone(event_lane_zone).weekday()].append((event, next_occurrence))

        # One embed for each day
        weekday_embeds = []

        for weekday_offset in range(0, 7):
            # Calculate the day
            day = last_monday_5am + datetime.timedelta(days=weekday_offset)

            # Sort the events in the list by their next occurrence
            events_by_day[weekday_offset].sort(key=lambda pair: pair[1])

            # Calculate notable date emojis
            notable_date_emojis = calculate_notable_date_emojis(day.year)

            emoji = notable_date_emojis.get((day.month, day.day), None)

            if emoji is None:
                title = f"# \N{SPIRAL CALENDAR PAD} {day:%A (%Y-%m-%d)}"
            else:
                title = f"# {emoji} {day:%A (%Y-%m-%d)}"

            description_parts = [
                title,
            ]

            if events_by_day[weekday_offset]:
                for (event, next_occurrence) in events_by_day[weekday_offset]:
                    hour_time = (next_occurrence.hour + (next_occurrence.minute / 60)) % 12
                    emoji = min(CLOCK_EMOJIS, key=lambda pair: abs(pair[0] - hour_time))[1]

                    target_timezones = []

                    for flag, target_timezone in TIMEZONE_PAIRS:
                        as_target = next_occurrence.astimezone(target_timezone)
                        flag = to_regionals(flag)

                        if as_target.day != day.day:
                            target_timezones.append(f'\u200b    {flag}  {as_target.strftime("%I:%M %p")} {as_target.tzname()} ({as_target.strftime("%a")})')
                        else:
                            target_timezones.append(f'\u200b    {flag}  {as_target.strftime("%I:%M %p")} {as_target.tzname()}')

                    description_parts.append(
                        f"**{event.name}** with {event.host}\n"
                        f"\u200b    {emoji} {discord.utils.format_dt(next_occurrence, 'f')}\n"
                        f"{'\n'.join(target_timezones)}"
                    )

            else:
                description_parts.append("-# -- No events this day. --")

            embed = discord.Embed(
                color=discord.Color.from_hsv(weekday_offset / 7.0, 1.0, 1.0),
                description="\n\n".join(description_parts)
            )

            weekday_embeds.append(embed)

        # If a message exists update it
        if event_lane.webhook_message_id:
            message = event_lane.webhook.edit_message(
                message_id=event_lane.webhook_message_id,
                embeds=weekday_embeds,
            )
        else:
            message = event_lane.webhook.send(
                embeds=weekday_embeds,
                wait=True,
            )

        lane_messages[event_lane.name] = message.id

    return lane_messages
