"""Modal dialog displaying chat conversation history with options to switch, create new, or delete."""

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label

from App.DB.storage import AppDatabase, ChatSession


class ChatHistoryModal(ModalScreen[str | None]):
    """Modal screen displaying past chat sessions stored in SQLite."""

    DEFAULT_CSS = """
    ChatHistoryModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #history-dialog {
        width: 84;
        max-width: 90%;
        height: 24;
        max-height: 85%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
        layout: vertical;
    }

    #history-title {
        width: 100%;
        height: 1;
        text-style: bold;
        color: $brand-bright;
        margin-bottom: 1;
    }

    #history-table {
        width: 100%;
        height: 1fr;
        background: $boost;
        border: solid $line;
        margin-bottom: 1;
    }

    #history-actions {
        width: 100%;
        height: 3;
        layout: horizontal;
        align: right middle;
    }

    #history-actions > Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Cerrar", show=True),
        Binding("enter", "select_current", "Cargar chat", show=True),
    ]

    def __init__(self, current_session_id: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.current_session_id = current_session_id
        self.db = AppDatabase.get_instance()
        self.sessions: list[ChatSession] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="history-dialog"):
            yield Label("💬 HISTORIAL DE CONVERSACIONES", id="history-title")
            yield DataTable(id="history-table", cursor_type="row")
            with Horizontal(id="history-actions"):
                yield Button("➕ Nuevo Chat", id="btn-hist-new", variant="primary")
                yield Button("Cargar Chat", id="btn-hist-load", variant="success")
                yield Button("🗑️ Eliminar", id="btn-hist-delete", variant="error")
                yield Button("Cerrar [Esc]", id="btn-hist-close")

    def on_mount(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.add_columns("Estado", "Título", "Modelo", "Última actividad")
        self._refresh_sessions()

    def _refresh_sessions(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.clear()
        self.sessions = self.db.list_sessions()

        for s in self.sessions:
            is_active = "✦ Activo" if s.id == self.current_session_id else ""
            # Format timestamp nicely (YYYY-MM-DD HH:MM)
            updated_display = s.updated_at[:16].replace("T", " ")
            model_display = getattr(s, "model", "gemini-2.5-flash")
            table.add_row(is_active, s.title, model_display, updated_display, key=s.id)

    def _get_selected_session_id(self) -> str | None:
        table = self.query_one("#history-table", DataTable)
        if table.cursor_row is not None and 0 <= table.cursor_row < len(self.sessions):
            return self.sessions[table.cursor_row].id
        return None

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def action_select_current(self) -> None:
        selected_id = self._get_selected_session_id()
        if selected_id:
            self.dismiss(selected_id)

    @on(Button.Pressed, "#btn-hist-load")
    def on_btn_load(self) -> None:
        selected_id = self._get_selected_session_id()
        if selected_id:
            self.dismiss(selected_id)

    @on(Button.Pressed, "#btn-hist-new")
    def on_btn_new(self) -> None:
        # Return special signal to create a clean deferred chat in the UI
        self.dismiss("__NEW_CHAT__")

    @on(Button.Pressed, "#btn-hist-delete")
    def on_btn_delete(self) -> None:
        selected_id = self._get_selected_session_id()
        if selected_id:
            self.db.delete_session(selected_id)
            self._refresh_sessions()

    @on(Button.Pressed, "#btn-hist-close")
    def on_btn_close(self) -> None:
        self.dismiss(None)
