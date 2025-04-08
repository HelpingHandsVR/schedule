# -*- coding: utf-8 -*-

"""
Types, dataclasses, etc.
"""

import dataclasses
import datetime
import typing


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
