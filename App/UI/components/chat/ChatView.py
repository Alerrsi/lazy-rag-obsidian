from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, RichLog
from ..prompt.SearchBarView import SearchBarView


class ChatView(Widget):

    DEFAULT_CSS = """
    ChatView {
        height: 1fr;
        width: 60%;
    }

    ChatView > VerticalScroll {
        height: 1fr;
    }

    ChatView > Input {
        dock: bottom;
    }
    """

    class MessageSubmitted(Message):
        """Se emite cuando el usuario envía un mensaje.
        Quien escuche este mensaje decide qué hacer (RAG, LLM, lo que sea)."""

        def __init__(self, text: str) -> None:
            super().__init__()

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="messages"):
            yield RichLog(wrap=True, markup=True, id="log")

    def on_input_submitted(self, text) -> None:
        if not text:
            return

        self.add_user_message(text)
        self.post_message(self.MessageSubmitted(text))

    # --- API pública para que quien conecte el backend actualice la UI ---

    def add_user_message(self, text: str) -> None:
        self.query_one(RichLog).write(f"[b]Tú:[/b] {text}")

    def add_assistant_message(self, text: str) -> None:
        self.query_one(RichLog).write(f"[b]Asistente:[/b] {text}")

    def set_loading(self, loading: bool) -> None:
        self.query_one("#chat-input", Input).disabled = loading