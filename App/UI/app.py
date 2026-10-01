import os
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.widgets import Button, Input, Label
from textual.worker import WorkerState

from .components.prompt.SearchBarView import SearchBarView
from .components.filemanager.FileManagerView import FileManagerView
from .components.filemanager.VaultModal import VaultModal
from .components.filemanager.NotePreviewModal import NotePreviewModal
from .components.filemanager.HorizontalSplitter import HorizontalSplitter
from .components.chat.ChatView import ChatView
from .theme import LAZY_OBSIDIAN
from App.RAG.Chain import Chain
from App.RAG.VectorialTransfer import VectorialTransfer

# Breakpoints, in cells. The TUI is a fluid surface, so instead of relying on
# percentages (which round to nothing on small terminals and overflow on large
# ones) the layout switches modes and every size is driven by 1fr plus fixed wells.
WIDE_WIDTH = 130
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
    ("wide", lambda width, height: width >= WIDE_WIDTH),
    ("compact", lambda width, height: NARROW_WIDTH <= width < COMPACT_WIDTH),
    ("narrow", lambda width, height: width < NARROW_WIDTH),
    ("micro", lambda width, height: width < MICRO_WIDTH),
    ("short", lambda width, height: height < SHORT_HEIGHT),
    ("tiny", lambda width, height: height < TINY_HEIGHT),
)


class Myapp(App):

    BINDINGS = [
        Binding("ctrl+o", "open_change_vault", "Cambiar bóveda", show=True),
        Binding("ctrl+b", "toggle_sidebar", "Ver/Ocultar archivos", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
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
                yield Label("LAZY OBSIDIAN", id="brand")
                yield Label("tu bóveda, consultable desde la terminal", id="tagline")
                yield Label("enter enviar · ctrl+b archivos · ctrl+o cambiar bóveda", id="key-hints")
            with Horizontal(id="home"):
                yield ChatView(id="chat")
                yield HorizontalSplitter()
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
        # Abrir el indice en background: si la boveda cambio desde la ultima
        # corrida, la primera pregunta no tiene que pagar ese costo.
        self.warm_worker(self.chain.transfer.get_vectorstore)

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
        current_path = getattr(VectorialTransfer, "OBSIDIAN_PATH", FileManagerView.VAULT_ROOT)
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

        # 1. Cambiar OBSIDIAN_PATH de la clase VectorialTransfer y en la instancia
        VectorialTransfer.OBSIDIAN_PATH = abs_path
        self.chain.use_vault(abs_path)

        # 2. Cambiar VAULT_ROOT dentro de FileManagerView
        import App.UI.components.filemanager.FileManagerView as fmv_module
        fmv_module.VAULT_ROOT = abs_path
        FileManagerView.VAULT_ROOT = abs_path
        file_manager = self.query_one(FileManagerView)
        file_manager.update_vault_root(abs_path)

        # Notificación y mensaje de confirmación
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

        # Comando rápido de cambio de directorio: /vault [ruta], /dir [ruta] o /path [ruta]
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

        barra = self.query_one(SearchBarView)
        barra.send(entrada)
        self._ask(entrada)

    def _ask(self, text: str) -> None:
        self._set_busy(True)
        self._active_ask = self.ask_worker(self.chain.search, text)

    @work(thread=True, exclusive=True, group="ask", exit_on_error=False)
    def ask_worker(self, search, question: str) -> str:
        """Corre la consulta en un hilo.

        Antes era una llamada directa desde el handler de Input.Submitted:
        retrieval y Gemini corrian en el event loop de Textual, asi que la TUI
        entera se quedaba pegada, sin repintar y sin responder ctrl+c.
        """
        try:
            return search(question)
        except Exception as error:
            return f"⚠️ No pude responder: {error}"

    @work(thread=True, exclusive=True, group="index", exit_on_error=False)
    def warm_worker(self, open_index) -> None:
        """Abre/sincroniza el indice fuera del event loop."""
        open_index()

    def on_worker_state_changed(self, event) -> None:
        # Unico mensaje de estado de los workers: se llama Worker.StateChanged y
        # lleva namespace "worker", asi que el handler va con el prefijo entero.
        # Con "on_work_state_changed" no se dispara nunca.
        worker = event.worker

        if worker.group == "index":
            self._report_index(worker)
            return

        # exclusive=True cancela la pregunta anterior al mandar otra: su
        # CANCELLED no debe apagar el spinner de la que esta corriendo.
        if worker is not self._active_ask:
            return

        if worker.state == WorkerState.SUCCESS:
            self._set_busy(False)
            self.query_one("#chat", ChatView).add_assistant_message(worker.result)
            self.query_one("#message", Input).focus()
        elif worker.state in (WorkerState.ERROR, WorkerState.CANCELLED):
            self._set_busy(False)
            if worker.state == WorkerState.ERROR:
                self.query_one("#chat", ChatView).add_assistant_message(
                    f"⚠️ No pude responder: {worker.error}"
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
