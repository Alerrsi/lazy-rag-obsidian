from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Markdown, Static

EMPTY_STATE = """[b]Tu bóveda está entera acá.[/b]

Preguntá en tus palabras lo que recordás a medias — "esa receta de pasta que anoté en algún lado" — y te devuelvo la nota donde lo escribiste.

[dim]No busco en internet. Busco en tus notas.[/dim]"""


class UserMessageCard(Vertical):
    """Tarjeta superior del mensaje del usuario (barra lateral violeta, fondo panel limpio)."""

    def __init__(self, text: str, **kwargs) -> None:
        super().__init__(classes="user-card", **kwargs)
        self.text = text

    def compose(self) -> ComposeResult:
        yield Static(self.text, classes="user-text")


class AssistantMessageCard(Vertical):
    """Tarjeta de respuesta del asistente (pensamiento/metadatos sutiles y markdown libre)."""

    def __init__(self, text: str, thought: str | None = None, **kwargs) -> None:
        super().__init__(classes="assistant-card", **kwargs)
        self.text = text
        self.thought = thought

    def compose(self) -> ComposeResult:
        if self.thought:
            yield Static(f"✦ Thought · {self.thought}", classes="assistant-meta-thought")
        yield Markdown(self.text, classes="assistant-markdown")


class ChatView(Widget):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "CONVERSACIÓN"

    def compose(self) -> ComposeResult:
        with Vertical(id="messages"):
            with Horizontal(id="chat-intro"):
                yield Static(EMPTY_STATE, id="chat-empty")
            yield VerticalScroll(id="chat-scroll")
            yield Static("", id="chat-status")

    def on_input_submitted(self, text: str) -> None:
        if not text:
            return
        self.add_user_message(text)

    def add_user_message(self, text: str) -> None:
        self._reveal_conversation()
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        card = UserMessageCard(text=text)
        scroll.mount(card)
        card.scroll_visible()

    def add_assistant_message(self, text: str, thought: str | None = None) -> None:
        self._reveal_conversation()
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        card = AssistantMessageCard(text=text, thought=thought)
        scroll.mount(card)
        card.scroll_visible()

    def clear_messages(self) -> None:
        """Removes all mounted message cards."""
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        for child in list(scroll.children):
            child.remove()
        empty = self.query_one("#chat-empty")
        empty.display = True

    def load_history(self, messages) -> None:
        """Populates the chat view with persisted historical messages."""
        if not messages:
            return
        self._reveal_conversation()
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        for msg in messages:
            if msg.sender == "user":
                scroll.mount(UserMessageCard(text=msg.content))
            else:
                scroll.mount(AssistantMessageCard(text=msg.content, thought=msg.thought))

    def set_status(self, text: str | None) -> None:
        """Feedback while a question is in flight or index update."""
        status = self.query_one("#chat-status", Static)
        status.update(text or "")
        status.display = text is not None

    def _reveal_conversation(self) -> None:
        empty = self.query_one("#chat-empty")
        if empty.display:
            empty.display = False
