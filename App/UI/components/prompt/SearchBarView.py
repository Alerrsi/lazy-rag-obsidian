from typing import Callable

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input, Label

PLACEHOLDER = "Escribí tu pregunta…"


class SearchBarView(Widget):

    def __init__(self, on_send: Callable[[str], None] = None, **kwargs):
        self.on_send = on_send
        super().__init__(**kwargs)
        self.border_title = "PREGUNTA"

    def send(self):
        self.on_send(self.query_one(Input).value)

    def compose(self) -> ComposeResult:
        yield Label("❯", id="prompt-caret")
        yield Input(id="message", placeholder=PLACEHOLDER)
