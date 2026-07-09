from textual.widget import Widget
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult
from textual.widgets import Label, Input
from typing import Callable

class SearchBarView(Widget):
    
    DEFAULT_CSS = """
    SearchBarView {
    width: 100%;
    height: 100%
    }

   
    #div-bar{
    padding: 1;
    layout: grid;
    height: 100%;
    color: white;
    align: center middle;
    }

    #message {
    width: 100%;
    height: 100%;
    }
    """
    def __init__(self, on_send: Callable[[str], None] = None, **kwargs):
        self.on_send = on_send
        super().__init__(**kwargs)
            

    def send(self):
        self.on_send(self.query_one(Input).value)

    def compose(self) -> ComposeResult:
        with Horizontal(id="big-bar"):
            with Vertical(id="div-bar"):
                yield Input(id = "message", placeholder="Escribe un mensaje...")

