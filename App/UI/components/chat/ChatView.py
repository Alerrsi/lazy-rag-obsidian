from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, RichLog, Static

EMPTY_STATE = """[b]Tu bóveda está entera acá.[/b]

Preguntá en tus palabras lo que recordás a medias — "esa receta de pasta que anoté en algún lado" — y te devuelvo la nota donde lo escribiste.

[dim]No busco en internet. Busco en tus notas.[/dim]"""


class ChatView(Widget):

    class MessageSubmitted(Message):
        def __init__(self, text: str) -> None:
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "CONVERSACIÓN"

    def compose(self) -> ComposeResult:
        with Vertical(id="messages"):
            # Own container so the intro can be centred on its own: Textual
            # aligns the bounding box of a container's children, and the log
            # below spans the full width.
            with Horizontal(id="chat-intro"):
                yield Static(EMPTY_STATE, id="chat-empty")
            # min_width is the wrap floor; the default of 78 would clip replies
            # instead of re-wrapping them in a narrow pane.
            yield RichLog(wrap=True, markup=True, min_width=1, id="log")

    def on_input_submitted(self, text) -> None:
        if not text:
            return

        self.add_user_message(text)
        self.post_message(self.MessageSubmitted(text))

    def add_user_message(self, text: str) -> None:
        self._reveal_conversation()
        self.query_one(RichLog).write(f"[b]Tú:[/b] {text}")

    def add_assistant_message(self, text: str) -> None:
        self._reveal_conversation()
        self.query_one(RichLog).write(f"[b]Asistente:[/b] {text}")

    def set_loading(self, loading: bool) -> None:
        self.query_one("#chat-input", Input).disabled = loading

    def _reveal_conversation(self) -> None:
        self.query_one("#chat-empty").display = False
