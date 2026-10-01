from datetime import datetime, timezone
import os
import time
import uuid
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.notifications import SeverityLevel
from textual.widgets import Button, Input, Label
from textual.worker import WorkerState

from .components.prompt.SearchBarView import SearchBarView
from .components.filemanager.FileManagerView import FileManagerView
from .components.filemanager.VaultModal import VaultModal
from .components.filemanager.NotePreviewModal import NotePreviewModal
from .components.filemanager.HorizontalSplitter import HorizontalSplitter
from .components.chat.ChatView import ChatView
from .components.drawer.SideDrawerView import SideDrawerView, PinContextMenuModal, ChatHistoryItem
from .components.settings.SettingsModal import SettingsModal
from .theme import LAZY_OBSIDIAN
from App.DB.storage import AppDatabase, ChatSession
from App.RAG.Chain import Chain
from App.RAG.VectorialTransfer import VectorialTransfer

WIDE_WIDTH = 130
COMPACT_WIDTH = 104
NARROW_WIDTH = 76
MICRO_WIDTH = 52
SHORT_HEIGHT = 20
TINY_HEIGHT = 12

PROMPTS = (
    (COMPACT_WIDTH, "Escribí tu pregunta sobre tus notas…"),
    (MICRO_WIDTH, "Escribí tu pregunta…"),
    (0, "Preguntá…"),
)

LAYOUT_MODES = (
    ("wide", lambda width, height: width >= WIDE_WIDTH),
    ("compact", lambda width, height: NARROW_WIDTH <= width < COMPACT_WIDTH),
    ("narrow", lambda width, height: width < NARROW_WIDTH),
    ("micro", lambda width, height: width < MICRO_WIDTH),
    ("short", lambda width, height: height < SHORT_HEIGHT),
    ("tiny", lambda width, height: height < TINY_HEIGHT),
)


class Myapp(App):

    BINDINGS = [
        Binding("ctrl+m", "toggle_drawer", "Menú lateral / Historial", show=True),
        Binding("ctrl+comma", "open_settings", "Configuración", show=False),
        Binding("ctrl+b", "toggle_sidebar", "Ver/Ocultar archivos", show=True),
        Binding("ctrl+o", "open_change_vault", "Cambiar bóveda", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.db = AppDatabase.get_instance()
        now = datetime.now(timezone.utc).isoformat()
        self.current_session = ChatSession(
            id=str(uuid.uuid4()),
            title="Nueva Conversación",
            model="gemini-2.5-flash",
            created_at=now,
            updated_at=now,
        )
        self._session_is_persisted = False

        self.chain = Chain()
        self._active_ask = None
        self._sidebar_visible = True
        self.register_theme(LAZY_OBSIDIAN)
        self.theme = LAZY_OBSIDIAN.name

    CSS_PATH = [
        "CSS/app.tcss",
        "CSS/ChatView.tcss",
        "CSS/FileManagerView.tcss",
        "CSS/SearchBar.tcss",
        "CSS/VaultModal.tcss",
        "CSS/NotePreviewModal.tcss",
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="main"):
            with Horizontal(id="header"):
                yield Button("☰", id="btn-open-drawer", tooltip="Menú lateral [Ctrl+M]")
                yield Label("LAZY OBSIDIAN", id="brand")
                yield Label("tu bóveda, consultable desde la terminal", id="tagline")
                yield Label("ctrl+m menú lateral · enter enviar · ctrl+b archivos · ctrl+o bóveda", id="key-hints")
            with Horizontal(id="home"):
                yield SideDrawerView(current_session_id=self.current_session.id, id="side-drawer")
                yield ChatView(id="chat")
                yield HorizontalSplitter()
                yield FileManagerView(id="sidebar")
            with Horizontal(id="home-bar"):
                yield SearchBarView(id="search-bar")

    def on_mount(self) -> None:
        chat = self.query_one(ChatView)
        barra = self.query_one(SearchBarView)
        barra.on_send = chat.on_input_submitted

        # Al abrir la app, siempre se muestra el mensaje de bienvenida centrado
        chat.clear_messages()

        self._apply_layout_mode(self.size.width, self.size.height)
        self.query_one("#message", Input).focus()
        self.warm_worker(self.chain.transfer.get_vectorstore)

    def _load_active_session_messages(self) -> None:
        chat = self.query_one(ChatView)
        chat.clear_messages()
        if self._session_is_persisted:
            saved_messages = self.db.get_messages(self.current_session.id)
            if saved_messages:
                chat.load_history(saved_messages, model_name=self.current_session.model)

    def on_resize(self, event: Resize) -> None:
        self._apply_layout_mode(event.size.width, event.size.height)

    def _apply_layout_mode(self, width: int, height: int) -> None:
        """Flag the current terminal size so the stylesheet can adapt the layout."""
        for main in self.query("#main"):
            for name, applies in LAYOUT_MODES:
                main.set_class(applies(width, height), name)
        for prompt in self.query("#message"):
            prompt.placeholder = next(
                text for minimum, text in PROMPTS if width >= minimum
            )

    def notify(
        self,
        message: str,
        *,
        title: str = "",
        severity: SeverityLevel = "information",
        timeout: float | None = None,
        markup: bool = True,
    ) -> None:
        """Emits a notification only if an identical notification is not currently active."""
        for notif in self._notifications:
            if (
                not notif.has_expired
                and notif.message == message
                and notif.title == title
                and notif.severity == severity
            ):
                return
        super().notify(
            message,
            title=title,
            severity=severity,
            timeout=timeout,
            markup=markup,
        )

    # --- Drawer Actions & Handlers -------------------------------------------

    def action_toggle_drawer(self) -> None:
        drawer = self.query_one(SideDrawerView)
        is_open = drawer.toggle()
        state = "abierto" if is_open else "cerrado"
        self.notify(f"Menú lateral {state} (Ctrl+M)", title="Menú", severity="information")

    @on(Button.Pressed, "#btn-open-drawer")
    def on_btn_open_drawer(self) -> None:
        self.action_toggle_drawer()

    @on(SideDrawerView.CloseDrawer)
    def on_drawer_close_requested(self) -> None:
        drawer = self.query_one(SideDrawerView)
        drawer.close()

    @on(SideDrawerView.SessionSelected)
    def on_drawer_session_selected(self, message: SideDrawerView.SessionSelected) -> None:
        self.query_one(SideDrawerView).close()
        selected_id = message.session_id
        if selected_id != self.current_session.id or not self._session_is_persisted:
            sessions = {s.id: s for s in self.db.list_sessions()}
            if selected_id in sessions:
                self.current_session = sessions[selected_id]
                self._session_is_persisted = True
                self._load_active_session_messages()
                self.notify(f"Cargado: {self.current_session.title}", title="Chat Cambiado", severity="information")
        self.query_one("#message", Input).focus()

    @on(ChatHistoryItem.RightClicked)
    def on_history_item_right_clicked(self, message: ChatHistoryItem.RightClicked) -> None:
        """Shows minimal context box adjacent to the right-clicked conversation."""
        session = message.session
        anchor_x = message.screen_x
        anchor_y = message.screen_y

        def _on_context_result(action: str | None) -> None:
            drawer = self.query_one(SideDrawerView)
            if action == "toggle_pin":
                ok, msg = self.db.toggle_pin_session(session.id)
                self.notify(msg, title="Fijar chat", severity="information" if ok else "warning")
                drawer.refresh_history(self.current_session.id)
            elif action == "delete":
                self.db.delete_session(session.id)
                self.notify(f"Conversación '{session.title}' eliminada", title="Eliminado", severity="information")
                if self.current_session.id == session.id:
                    self._start_new_unpersisted_chat()
                else:
                    drawer.refresh_history(self.current_session.id)

        self.push_screen(
            PinContextMenuModal(session, anchor_x=anchor_x, anchor_y=anchor_y),
            _on_context_result,
        )

    @on(SideDrawerView.OpenSettings)
    def on_drawer_open_settings(self) -> None:
        self.query_one(SideDrawerView).close()
        self.action_open_settings()

    @on(SideDrawerView.NewChatRequested)
    def on_drawer_new_chat(self) -> None:
        self.query_one(SideDrawerView).close()
        self._start_new_unpersisted_chat()

    def _start_new_unpersisted_chat(self) -> None:
        """Initializes a new empty chat in memory without saving to SQLite until the first message."""
        now = datetime.now(timezone.utc).isoformat()
        self.current_session = ChatSession(
            id=str(uuid.uuid4()),
            title="Nueva Conversación",
            model="gemini-2.5-flash",
            created_at=now,
            updated_at=now,
        )
        self._session_is_persisted = False
        chat = self.query_one(ChatView)
        chat.clear_messages()
        drawer = self.query_one(SideDrawerView)
        drawer.refresh_history(self.current_session.id)
        self.notify("Nuevo chat listo. Se guardará al enviar tu primer mensaje.", title="Nuevo Chat", severity="information")
        self.query_one("#message", Input).focus()

    def action_open_settings(self) -> None:
        self.push_screen(SettingsModal(), self._on_settings_result)

    def _on_settings_result(self, updated_settings: dict[str, str] | None) -> None:
        if updated_settings and "vault_path" in updated_settings:
            new_vault = updated_settings["vault_path"]
            self.change_vault_path(new_vault)
        self.query_one("#message", Input).focus()

    # --- Sidebar (Vault tree) Actions ----------------------------------------

    def action_toggle_sidebar(self) -> None:
        """Toggles the visibility of the files menu / sidebar and its splitter."""
        sidebar = self.query_one("#sidebar", FileManagerView)
        splitter = self.query_one(HorizontalSplitter)
        self._sidebar_visible = not self._sidebar_visible
        sidebar.display = self._sidebar_visible
        splitter.display = self._sidebar_visible
        state_str = "mostrado" if self._sidebar_visible else "oculto"
        self.notify(f"Panel de notas {state_str} (Ctrl+B)", title="Archivos", severity="information")

    @on(FileManagerView.ToggleSidebarRequested)
    def on_toggle_sidebar_requested(self) -> None:
        self.action_toggle_sidebar()

    @on(Button.Pressed, "#btn-change-vault")
    def on_btn_change_vault(self) -> None:
        self.action_open_change_vault()

    def action_open_change_vault(self) -> None:
        current_path = self.db.get_vault_path()
        self.push_screen(VaultModal(current_path=current_path), self._on_vault_modal_result)

    def _on_vault_modal_result(self, new_path: str | None) -> None:
        if new_path:
            self.change_vault_path(new_path)
        self.query_one("#message", Input).focus()

    @on(FileManagerView.FileSelected)
    def on_file_selected(self, message: FileManagerView.FileSelected) -> None:
        """Handles file selection from the tree and previews markdown files in a modal."""
        file_path = message.path
        if file_path.suffix.lower() == ".md":
            self.push_screen(NotePreviewModal(str(file_path)), self._on_note_modal_closed)
        else:
            self.notify(
                f"El archivo '{file_path.name}' no es Markdown (.md)",
                title="Vista previa no soportada",
                severity="warning",
            )

    def _on_note_modal_closed(self, result: None = None) -> None:
        """Restore focus to the search input when closing the preview modal."""
        self.query_one("#message", Input).focus()

    def change_vault_path(self, new_path: str) -> None:
        abs_path = os.path.abspath(os.path.expanduser(new_path))
        self.db.set_vault_path(abs_path)
        VectorialTransfer.set_obsidian_path(abs_path)
        self.chain.use_vault(abs_path)
        file_manager = self.query_one(FileManagerView)
        file_manager.update_vault_root(abs_path)

        self.notify(f"Bóveda cambiada a: {abs_path}", title="Bóveda actualizada", severity="information")
        chat = self.query_one("#chat", ChatView)
        chat.add_assistant_message(f"📁 Directorio de fuentes actualizado a: [bold]{abs_path}[/bold]")
        self.query_one("#message", Input).focus()

    @on(Input.Submitted, "#message")
    def send(self) -> None:
        input_widget = self.query_one("#message", Input)
        entrada = input_widget.value.strip()
        input_widget.value = ""

        if not entrada:
            return

        lower = entrada.lower()
        if lower.startswith(("/vault", "/dir", "/path")):
            parts = entrada.split(maxsplit=1)
            if len(parts) > 1:
                target_path = os.path.expanduser(parts[1].strip())
                if os.path.isdir(target_path):
                    self.change_vault_path(target_path)
                else:
                    self.notify(f"Directorio no encontrado: {parts[1]}", title="Error", severity="error")
                    chat = self.query_one("#chat", ChatView)
                    chat.add_assistant_message(f"⚠️ El directorio no existe: [bold]{parts[1]}[/bold]")
            else:
                self.action_open_change_vault()
            return

        if not self._session_is_persisted:
            words = entrada.split()
            first_words = " ".join(words[:5])
            title = first_words[:35] + ("…" if len(entrada) > 35 else "")
            persisted_sess = self.db.create_session(
                title=title,
                model="gemini-2.5-flash",
                session_id=self.current_session.id,
            )
            self.current_session = persisted_sess
            self._session_is_persisted = True
            drawer = self.query_one(SideDrawerView)
            drawer.refresh_history(self.current_session.id)

        barra = self.query_one(SearchBarView)
        barra.send(entrada)

        now_iso = datetime.now(timezone.utc).isoformat()
        self.db.add_message(
            session_id=self.current_session.id,
            sender="user",
            content=entrada,
            created_at=now_iso,
        )

        self._ask(entrada)

    def _ask(self, text: str) -> None:
        self._set_busy(True)
        chat = self.query_one("#chat", ChatView)
        chat.start_streaming_assistant_message(
            model_name=self.current_session.model,
        )
        self._active_ask = self.ask_worker(text)

    @work(thread=True, exclusive=True, group="ask", exit_on_error=False)
    def ask_worker(self, question: str) -> str:
        """Transmite la respuesta token a token en un hilo desacoplado."""
        full_text = []
        t0 = time.perf_counter()
        try:
            for chunk in self.chain.stream_search(question):
                full_text.append(chunk)
                self.call_from_thread(self._on_chunk_received, chunk)
            elapsed = time.perf_counter() - t0
            return "".join(full_text)
        except Exception as error:
            err_msg = f"⚠️ No pude responder: {error}"
            self.call_from_thread(self._on_chunk_received, err_msg)
            return err_msg

    def _on_chunk_received(self, chunk: str) -> None:
        chat = self.query_one("#chat", ChatView)
        chat.append_streaming_chunk(chunk)

    @work(thread=True, exclusive=True, group="index", exit_on_error=False)
    def warm_worker(self, open_index) -> None:
        """Abre/sincroniza el indice fuera del event loop."""
        open_index()

    def on_worker_state_changed(self, event) -> None:
        worker = event.worker

        if worker.group == "index":
            self._report_index(worker)
            return

        if worker is not self._active_ask:
            return

        if worker.state == WorkerState.SUCCESS:
            self._set_busy(False)
            answer = worker.result
            now_iso = datetime.now(timezone.utc).isoformat()
            self.db.add_message(
                session_id=self.current_session.id,
                sender="assistant",
                content=answer,
                created_at=now_iso,
            )
            drawer = self.query_one(SideDrawerView)
            drawer.refresh_history(self.current_session.id)
            self.query_one("#message", Input).focus()
        elif worker.state in (WorkerState.ERROR, WorkerState.CANCELLED):
            self._set_busy(False)
            now_iso = datetime.now(timezone.utc).isoformat()
            if worker.state == WorkerState.ERROR:
                err_msg = f"⚠️ No pude responder: {worker.error}"
                self.query_one("#chat", ChatView).append_streaming_chunk(f"\n{err_msg}")
                self.db.add_message(
                    session_id=self.current_session.id,
                    sender="assistant",
                    content=err_msg,
                    created_at=now_iso,
                )
            self.query_one("#message", Input).focus()

    def _report_index(self, worker) -> None:
        if worker.state == WorkerState.ERROR:
            self.query_one("#chat", ChatView).add_assistant_message(
                f"⚠️ No pude leer la bóveda: {worker.error}"
            )
            return
        if worker.state != WorkerState.SUCCESS:
            return

        stats = self.chain.transfer.stats
        if not stats.chunks_written and not stats.changed_files:
            return
        partes = []
        if stats.added_files:
            partes.append(f"{len(stats.added_files)} nuevas")
        if stats.modified_files:
            partes.append(f"{len(stats.modified_files)} modificadas")
        if stats.removed_files:
            partes.append(f"{len(stats.removed_files)} borradas")
        self.query_one("#chat", ChatView).add_assistant_message(
            f"📝 Índice actualizado: {', '.join(partes)} "
            f"({stats.chunks_written} fragmentos)."
        )

    def _set_busy(self, busy: bool) -> None:
        self.query_one("#chat", ChatView).set_status(
            "⏳ Buscando en tus notas…" if busy else None
        )
        self.query_one("#message", Input).disabled = busy
        self.query_one(SearchBarView).border_subtitle = "…" if busy else ""
