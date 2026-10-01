"""Modal dialog for application configurations stored in SQLite."""

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from App.DB.storage import AppDatabase


class SettingsModal(ModalScreen[dict[str, str] | None]):
    """Modal screen allowing the user to view and modify application settings."""

    DEFAULT_CSS = """
    SettingsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #settings-dialog {
        width: 72;
        max-width: 90%;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
        layout: vertical;
    }

    #settings-title {
        width: 100%;
        height: 1;
        text-style: bold;
        color: $brand-bright;
        margin-bottom: 1;
    }

    .settings-field {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    .settings-label {
        color: $ink;
        text-style: bold;
        margin-bottom: 0;
    }

    .settings-hint {
        color: $ink-faint;
        text-style: italic;
        margin-bottom: 1;
    }

    #settings-actions {
        width: 100%;
        height: 3;
        layout: horizontal;
        align: right middle;
        margin-top: 1;
    }

    #settings-actions > Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Cerrar", show=True),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = AppDatabase.get_instance()

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-dialog"):
            yield Label("⚙️ CONFIGURACIÓN DEL SISTEMA", id="settings-title")

            with Vertical(classes="settings-field"):
                yield Label("Directorio de la Bóveda Obsidian (vault_path):", classes="settings-label")
                yield Input(
                    value=self.db.get_vault_path(),
                    placeholder="/ruta/a/tu/boveda",
                    id="input-setting-vault",
                )
                yield Label("Ruta en disco analizada para embeddings y árbol de archivos.", classes="settings-hint")

            with Horizontal(id="settings-actions"):
                yield Button("Guardar", id="btn-settings-save", variant="primary")
                yield Button("Cancelar [Esc]", id="btn-settings-cancel")

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#btn-settings-save")
    def on_btn_save(self) -> None:
        vault_input = self.query_one("#input-setting-vault", Input).value.strip()
        if vault_input:
            self.db.set_vault_path(vault_input)
            self.dismiss({"vault_path": vault_input})
        else:
            self.dismiss(None)

    @on(Button.Pressed, "#btn-settings-cancel")
    def on_btn_cancel(self) -> None:
        self.dismiss(None)
