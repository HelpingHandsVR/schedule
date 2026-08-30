
import functools
import typing

from definitions import EventLane

from formats.html import generate_html
from formats.old import generate_old_format
from formats.textmeshpro import generate_textmeshpro_special, generate_textmeshpro_text
from formats.webhook import send_webhooks


__all__: typing.List[str] = [
    "OUTPUT_FORMATS"
]


OUTPUT_FORMATS: list[tuple[
    typing.Callable[[list[EventLane]], typing.Union[str, dict[str, typing.Any]]], str
]] = [
    (generate_old_format, "old.json"),
    (functools.partial(generate_html, language='en'), "index.html"),
    (functools.partial(generate_html, language='ja'), "index.ja.html"),
    (functools.partial(generate_textmeshpro_text, language='en'), "textmeshpro.en.txt"),
    (functools.partial(generate_textmeshpro_text, language='ja'), "textmeshpro.ja.txt"),
    (generate_textmeshpro_special, "textmeshpro.special.txt"),
    (send_webhooks, "webhook.json"),
]
