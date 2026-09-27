from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.widgets import Input, Label

from .components.prompt.SearchBarView import SearchBarView
from .components.filemanager.FileManagerView import FileManagerView
from .components.chat.ChatView import ChatView
from .theme import LAZY_OBSIDIAN

# Breakpoints, in cells. The TUI is a fluid surface, so instead of relying on
# percentages (which round to nothing on small terminals and overflow on large
# ones) the layout switches modes and every size is driven by 1fr plus fixed wells.
COMPACT_WIDTH = 104
NARROW_WIDTH = 76
MICRO_WIDTH = 52
SHORT_HEIGHT = 20
TINY_HEIGHT = 12

# The prompt never truncates: it steps down through shorter invitations as the
# terminal narrows, so the hint is never cut mid-word.
PROMPTS = (
    (COMPACT_WIDTH, "Escribí tu pregunta sobre tus notas…"),
    (MICRO_WIDTH, "Escribí tu pregunta…"),
    (0, "Preguntá…"),
)

LAYOUT_MODES = (
    ("compact", lambda width, height: width < COMPACT_WIDTH),
    ("narrow", lambda width, height: width < NARROW_WIDTH),
    ("micro", lambda width, height: width < MICRO_WIDTH),
    ("short", lambda width, height: height < SHORT_HEIGHT),
    ("tiny", lambda width, height: height < TINY_HEIGHT),
)


class Myapp(App):
    CSS_PATH = [
        "CSS/app.tcss",
        "CSS/ChatView.tcss",
        "CSS/FileManagerView.tcss",
        "CSS/SearchBar.tcss",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.register_theme(LAZY_OBSIDIAN)
        self.theme = LAZY_OBSIDIAN.name

    def compose(self) -> ComposeResult:
        with Vertical(id="main"):
            with Horizontal(id="header"):
                yield Label("LAZY OBSIDIAN", id="brand")
                yield Label("tu bóveda, consultable desde la terminal", id="tagline")
                yield Label("enter enviar · tab paneles", id="key-hints")
            with Horizontal(id="home"):
                yield ChatView(id="chat")
                yield FileManagerView(id="sidebar")
            with Horizontal(id="home-bar"):
                yield SearchBarView(id="search-bar")

    def on_mount(self) -> None:
        chat = self.query_one(ChatView)
        barra = self.query_one(SearchBarView)
        barra.on_send = chat.on_input_submitted
        self._apply_layout_mode(self.size.width, self.size.height)
        # The prompt is the reason the app is open: start there instead of on
        # the first focusable widget in DOM order (the log).
        self.query_one("#message", Input).focus()

    def on_resize(self, event: Resize) -> None:
        self._apply_layout_mode(event.size.width, event.size.height)

    def _apply_layout_mode(self, width: int, height: int) -> None:
        """Flag the current terminal size so the stylesheet can adapt the layout."""
        for main in self.query("#main"):
            for name, applies in LAYOUT_MODES:
                main.set_class(applies(width, height), name)
        # A resize can land before the tree is composed, hence the queries.
        for prompt in self.query("#message"):
            prompt.placeholder = next(
                text for minimum, text in PROMPTS if width >= minimum
            )

    @on(Input.Submitted, "#message")
    def send(self) -> None:
        barra = self.query_one(SearchBarView)
        barra.send()
        entrada = self.query_one("#message").value = ""
