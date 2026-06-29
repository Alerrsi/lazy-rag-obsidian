from textual.widget import Widget
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult
from textual.widgets import Label, Input

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

    def compose(self) -> ComposeResult:
        with Horizontal(id="big-bar"):
            with Vertical(id="div-bar"):
                yield Input(id = "message", placeholder="Escribe un mensaje...")
            