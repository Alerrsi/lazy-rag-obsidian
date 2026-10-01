from datetime import datetime, timezone
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.widget import Widget
from textual.widgets import Markdown, Static


def get_welcome_message(width: int = 100, height: int = 30) -> str:
    """Returns a responsive, personalized greeting based on time of day and terminal dimensions."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        saludo = "¡Buenos días!"
        icono = "🌅"
        subtitulo = "¿Qué notas deseas explorar o repasar esta mañana?"
        subtitulo_short = "¿Qué notas exploramos esta mañana?"
    elif 12 <= current_hour < 19:
        saludo = "¡Buenas tardes!"
        icono = "☀️"
        subtitulo = "¿En qué te puedo ayudar hoy con tu bóveda de notas?"
        subtitulo_short = "¿En qué te ayudo hoy con tus notas?"
    elif 19 <= current_hour < 24:
        saludo = "¡Buenas noches!"
        icono = "🌙"
        subtitulo = "¿Qué ideas o reflexiones de hoy quieres consultar?"
        subtitulo_short = "¿Qué ideas consultamos hoy?"
    else:
        saludo = "¡Hola, trasnochador!"
        icono = "✨"
        subtitulo = "La noche es buena para investigar. ¿Qué buscamos en tus notas?"
        subtitulo_short = "¿Qué buscamos en tus notas?"

    # Adaptación responsiva según el ancho y alto del contenedor
    if width < 45 or height < 14:
        # Modo ultra compacto (terminal micro o muy baja)
        return (
            f"[bold #bb9af7]{icono} {saludo}[/bold #bb9af7]\n"
            f"[dim]{subtitulo_short}[/dim]"
        )
    elif width < 70 or height < 20:
        # Modo intermedio/compacto
        return (
            f"[bold #bb9af7]{icono} {saludo}[/bold #bb9af7]\n\n"
            f"[bold]{subtitulo_short}[/bold]\n\n"
            f"[dim]Pregunta en lenguaje natural abajo.[/dim]"
        )
    else:
        # Modo normal y ancho: Arte ASCII o tipografía espaciosa
        return (
            f"[bold #bb9af7]╭───────────────────────────────────────────────────╮[/bold #bb9af7]\n"
            f"[bold #bb9af7]│                 {icono}  {saludo}                  │[/bold #bb9af7]\n"
            f"[bold #bb9af7]╰───────────────────────────────────────────────────╯[/bold #bb9af7]\n\n"
            f"[bold #7aa2f7]{subtitulo}[/bold #7aa2f7]\n\n"
            f"[dim]Escribe tu pregunta abajo en tus propias palabras para buscar en tu bóveda.[/dim]"
        )


def _format_time(timestamp: str | None = None) -> str:
    """Formats an ISO timestamp or current local time to HH:MM."""
    if not timestamp:
        return datetime.now().strftime("%H:%M")
    try:
        dt = datetime.fromisoformat(timestamp)
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%H:%M")
    except Exception:
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
            with Vertical(id="chat-intro"):
                yield Static(get_welcome_message(), id="chat-empty")
            yield VerticalScroll(id="chat-scroll")
            yield Static("", id="chat-status")

    def on_resize(self, event: Resize) -> None:
        """Adapts the welcome message reactively whenever the terminal or chat pane is resized."""
        intro = self.query_one("#chat-intro", Vertical)
        if intro.display:
            empty = self.query_one("#chat-empty", Static)
            empty.update(get_welcome_message(width=event.size.width, height=event.size.height))

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
        """Removes all mounted message cards and shows updated personalized welcome banner."""
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        for child in list(scroll.children):
            child.remove()
        empty = self.query_one("#chat-empty", Static)
        width = self.size.width or 100
        height = self.size.height or 30
        empty.update(get_welcome_message(width=width, height=height))
        intro = self.query_one("#chat-intro", Vertical)
        intro.display = True

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
        intro = self.query_one("#chat-intro", Vertical)
        if intro.display:
            intro.display = False
