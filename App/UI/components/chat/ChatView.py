from datetime import datetime, timezone
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Markdown, Static

EMPTY_STATE = """[b]Tu bóveda está entera acá.[/b]

Preguntá en tus palabras lo que recordás a medias — "esa receta de pasta que anoté en algún lado" — y te devuelvo la nota donde lo escribiste.

[dim]No busco en internet. Busco en tus notas.[/dim]"""


def _format_time(timestamp: str | None = None) -> str:
    """Formats an ISO timestamp or current local time to HH:MM."""
    if not timestamp:
        return datetime.now().strftime("%H:%M")
    try:
        # If timestamp is ISO, parse and convert to local time
        dt = datetime.fromisoformat(timestamp)
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%H:%M")
    except Exception:
        # Fallback substring if standard ISO format YYYY-MM-DDTHH:MM:SS
        if "T" in timestamp and len(timestamp) >= 16:
            return timestamp.split("T")[1][:5]
        return timestamp[:5]


class UserMessageCard(Vertical):
    """Tarjeta superior del mensaje del usuario (barra lateral violeta, hora e indicación limpia)."""

    def __init__(self, text: str, time_str: str | None = None, **kwargs) -> None:
        super().__init__(classes="user-card", **kwargs)
        self.text = text
        self.time_str = _format_time(time_str)

    def compose(self) -> ComposeResult:
        with Horizontal(classes="message-header-bar"):
            yield Static("Tú", classes="message-sender-name")
            yield Static(self.time_str, classes="message-timestamp")
        yield Static(self.text, classes="user-text")


class AssistantMessageCard(Vertical):
    """Tarjeta de respuesta del asistente con soporte para streaming reactivo, metadatos y hora."""

    def __init__(
        self,
        text: str = "",
        thought: str | None = None,
        time_str: str | None = None,
        model_name: str = "gemini-2.5-flash",
        **kwargs,
    ) -> None:
        super().__init__(classes="assistant-card", **kwargs)
        self.text = text
        self.thought = thought
        self.time_str = _format_time(time_str)
        self.model_name = model_name
        self._md_widget = Markdown(self.text or "▍", classes="assistant-markdown")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="message-header-bar"):
            yield Static(f"✦ Asistente ({self.model_name})", classes="message-sender-name assistant-name")
            yield Static(self.time_str, classes="message-timestamp")
        if self.thought:
            yield Static(f"✦ Thought · {self.thought}", classes="assistant-meta-thought")
        yield self._md_widget

    def append_chunk(self, chunk: str) -> None:
        """Appends a new token/chunk to the card and triggers real-time markdown update."""
        self.text += chunk
        self._md_widget.update(self.text)


class ChatView(Widget):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "CONVERSACIÓN"
        self._current_assistant_card: AssistantMessageCard | None = None

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

    def add_user_message(self, text: str, time_str: str | None = None) -> None:
        self._reveal_conversation()
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        card = UserMessageCard(text=text, time_str=time_str)
        scroll.mount(card)
        card.scroll_visible()

    def start_streaming_assistant_message(
        self,
        thought: str | None = None,
        time_str: str | None = None,
        model_name: str = "gemini-2.5-flash",
    ) -> AssistantMessageCard:
        """Mounts an empty assistant message card ready to receive streaming chunks."""
        self._reveal_conversation()
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        card = AssistantMessageCard(
            text="",
            thought=thought,
            time_str=time_str,
            model_name=model_name,
        )
        self._current_assistant_card = card
        scroll.mount(card)
        card.scroll_visible()
        return card

    def append_streaming_chunk(self, chunk: str) -> None:
        """Streams a token chunk into the currently active assistant message card."""
        if self._current_assistant_card:
            self._current_assistant_card.append_chunk(chunk)
            self._current_assistant_card.scroll_visible()

    def add_assistant_message(
        self,
        text: str,
        thought: str | None = None,
        time_str: str | None = None,
        model_name: str = "gemini-2.5-flash",
    ) -> None:
        self._reveal_conversation()
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        card = AssistantMessageCard(
            text=text,
            thought=thought,
            time_str=time_str,
            model_name=model_name,
        )
        scroll.mount(card)
        card.scroll_visible()

    def clear_messages(self) -> None:
        """Removes all mounted message cards."""
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        for child in list(scroll.children):
            child.remove()
        empty = self.query_one("#chat-empty")
        empty.display = True

    def load_history(self, messages, model_name: str = "gemini-2.5-flash") -> None:
        """Populates the chat view with persisted historical messages with timestamps."""
        if not messages:
            return
        self._reveal_conversation()
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        for msg in messages:
            if msg.sender == "user":
                scroll.mount(UserMessageCard(text=msg.content, time_str=msg.created_at))
            else:
                scroll.mount(
                    AssistantMessageCard(
                        text=msg.content,
                        thought=msg.thought,
                        time_str=msg.created_at,
                        model_name=model_name,
                    )
                )

    def set_status(self, text: str | None) -> None:
        """Feedback while a question is in flight or index update."""
        status = self.query_one("#chat-status", Static)
        status.update(text or "")
        status.display = text is not None

    def _reveal_conversation(self) -> None:
        empty = self.query_one("#chat-empty")
        if empty.display:
            empty.display = False
