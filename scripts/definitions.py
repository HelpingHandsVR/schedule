# -*- coding: utf-8 -*-

"""
Types, dataclasses, etc.
"""

import dataclasses
import datetime
import typing

import discord


class EventLaneLanguageInfo(typing.TypedDict):
    abbreviation: str
    native_localization: str
    localized_name: dict[str, str]


class EventLaneWebhookInfo(typing.TypedDict):
    channel: str
    url: str
    message_id: typing.NotRequired[str]
    header: typing.NotRequired[str]


class EventLaneMeta(typing.TypedDict):
    channels: dict[str, int]
    default_timezone: str
    use_all_events: typing.NotRequired[bool]
    language_info: typing.NotRequired[EventLaneLanguageInfo]
    webhook: typing.NotRequired[EventLaneWebhookInfo]


class EventLaneRawEventSchedule(typing.TypedDict):
    timezone: typing.NotRequired[str]
    basis: str
    day: typing.Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hour: int
    minute: int
    interval: typing.NotRequired[int]
    not_before: typing.NotRequired[str]
    not_after: typing.NotRequired[str]


class EventLaneRawEvent(typing.TypedDict):
    host: str
    name: str
    tags: list[str]
    paused: typing.NotRequired[bool]
    schedule: EventLaneRawEventSchedule


class EventLaneRawEvents(typing.TypedDict):
    events: list[EventLaneRawEvent]


@dataclasses.dataclass(frozen=True)
class EventLaneEvent:
    host: str
    name: str
    tags: list[str]
    paused: bool
    basis: datetime.datetime
    timezone: str
    interval: int
    not_before: datetime.date | None
    not_after: datetime.date | None

    def next_occurrence_after(self, target: datetime.datetime) -> typing.Optional[datetime.datetime]:
        # If paused, no next occurrence
        if self.paused:
            return None

        # Calculate the amount of days that have passed since the basis
        days_since_basis = (target - self.basis).days
        # Start search from floored interval from basis
        starting_day_offset = int(days_since_basis / self.interval) * self.interval
        needle = self.basis + datetime.timedelta(days=starting_day_offset)

        while needle < target or (needle.date() < self.not_before if self.not_before else False):
            needle += datetime.timedelta(days=self.interval)

            if self.not_after and needle.date() > self.not_after:
                return None

        if self.not_after and needle.date() > self.not_after:
            return None

        return needle


@dataclasses.dataclass(frozen=True)
class EventLane:
    name: str
    meta: EventLaneMeta
    events: list[EventLaneEvent]
    webhook: discord.SyncWebhook | None
    webhook_info: EventLaneWebhookInfo | None
    webhook_message_id: int | None
