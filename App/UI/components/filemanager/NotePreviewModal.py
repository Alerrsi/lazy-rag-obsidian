"""Modal dialog for viewing markdown (.md) note files.

Displays rendered markdown content with headers, lists, blockquotes,
syntax-highlighted code blocks, and an optional table of contents toggle.
"""

from pathlib import Path
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, MarkdownViewer


class NotePreviewModal(ModalScreen[None]):
    """Modal dialog that renders a markdown file with MarkdownViewer."""

    BINDINGS = [
        Binding("escape", "close", "Cerrar visor", show=True),
        Binding("t", "toggle_toc", "Tabla de contenidos", show=True),
    ]

    def __init__(self, file_path: str, title: str | None = None) -> None:
        super().__init__()
        self.file_path = file_path
        self.path_obj = Path(file_path)
        self.note_title = title or self.path_obj.name
        self.content = self._load_file_content()

    def _load_file_content(self) -> str:
        """Loads file text safely with utf-8 encoding and fallback."""
        try:
            return self.path_obj.read_text(encoding="utf-8", errors="replace")
        except Exception as err:
            return f"# ⚠️ Error al abrir el archivo\n\nNo se pudo leer `{self.file_path}`:\n\n```\n{err}\n```"

    def compose(self) -> ComposeResult:
        with Vertical(id="note-modal-dialog"):
            with Horizontal(id="note-modal-header"):
                with Vertical(id="note-modal-header-titles"):
                    yield Label(f"📄 {self.note_title}", id="note-modal-title")
                    yield Label(str(self.path_obj), id="note-modal-subtitle")
                yield Button("✕ Cerrar", id="btn-note-modal-close", variant="default")

            with Vertical(id="note-modal-body"):
                yield MarkdownViewer(
                    self.content,
                    show_table_of_contents=False,
                    id="note-modal-viewer",
                )

            with Horizontal(id="note-modal-footer"):
                yield Label(
                    "Esc salir · t índice · ↑↓ scroll · RePág/AvPág",
                    id="note-modal-hints",
                )
                with Horizontal(id="note-modal-buttons"):
                    yield Button("📑 Índice", id="btn-note-modal-toc", variant="default")
                    yield Button("Cerrar", id="btn-note-modal-bottom-close", variant="primary")

    def on_mount(self) -> None:
        """Focus the viewer so navigation keys work immediately."""
        viewer = self.query_one("#note-modal-viewer", MarkdownViewer)
        viewer.focus()

    def action_close(self) -> None:
        """Dismisses the modal."""
        self.dismiss(None)

    def action_toggle_toc(self) -> None:
        """Toggles the table of contents panel in MarkdownViewer."""
        viewer = self.query_one("#note-modal-viewer", MarkdownViewer)
        viewer.show_table_of_contents = not viewer.show_table_of_contents

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("btn-note-modal-close", "btn-note-modal-bottom-close"):
            self.action_close()
        elif event.button.id == "btn-note-modal-toc":
            self.action_toggle_toc()
