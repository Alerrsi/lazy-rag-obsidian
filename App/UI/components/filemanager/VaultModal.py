import os
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class VaultModal(ModalScreen[str | None]):
    """Modal dialog to quickly change the Obsidian vault / sources directory."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar"),
    ]

    def __init__(self, current_path: str = "") -> None:
        super().__init__()
        self.current_path = current_path

    def compose(self) -> ComposeResult:
        with Vertical(id="vault-modal-dialog"):
            yield Label("📁 CAMBIAR DIRECTORIO DE FUENTES", id="vault-modal-title")
            yield Label(
                "Ingresa la nueva ruta de tu bóveda (soporta ~ y rutas relativas):",
                id="vault-modal-help",
            )
            yield Input(
                value=self.current_path,
                placeholder="/ruta/a/tu/boveda",
                id="vault-modal-input",
            )
            yield Label("", id="vault-modal-error")
            with Horizontal(id="vault-modal-buttons"):
                yield Button("Cancelar (Esc)", id="btn-modal-cancel", variant="default")
                yield Button("Guardar (Enter)", id="btn-modal-ok", variant="primary")

    def on_mount(self) -> None:
        input_widget = self.query_one("#vault-modal-input", Input)
        input_widget.focus()
        input_widget.action_end()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-modal-ok":
            self._submit()
        elif event.button.id == "btn-modal-cancel":
            self.action_cancel()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        raw_path = self.query_one("#vault-modal-input", Input).value.strip()
        if not raw_path:
            self._set_error("La ruta no puede estar vacía.")
            return

        expanded_path = os.path.expanduser(raw_path)
        abs_path = os.path.abspath(expanded_path)

        if not os.path.exists(abs_path):
            self._set_error(f"No existe el directorio: {raw_path}")
            return

        if not os.path.isdir(abs_path):
            self._set_error(f"La ruta no es un directorio: {raw_path}")
            return

        self.dismiss(abs_path)

    def _set_error(self, message: str) -> None:
        error_label = self.query_one("#vault-modal-error", Label)
        error_label.update(f"⚠️ {message}")
