from textual.app import ComposeResult
from textual.widget import Widget
from textual.containers import Vertical
from textual.widgets import Static, Label

class ChatView(Widget):

    DEFAULT_CSS = """
    ChatView {
        width: 70%;
        height: 1fr;
        
    }

    #big-chat {
        color: white;
        height: 1fr;
        border: solid white;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical(id="big-chat"):
            yield Label("Caja de para ver chat")