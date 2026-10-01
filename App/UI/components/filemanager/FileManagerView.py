from pathlib import Path
import os
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DirectoryTree
from App.DB.storage import AppDatabase


class FileManagerView(Widget):

    class FileSelected(Message):
        """Dispatched when a file node is selected in the directory tree."""

        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    class ToggleSidebarRequested(Message):
        """Dispatched when user clicks the hide/collapse button."""
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "ARCHIVOS"
        # Always fetch current vault path from SQLite
        self.vault_root = AppDatabase.get_instance().get_vault_path()
        self._update_subtitle(self.vault_root)

    @property
    def VAULT_ROOT(self) -> str:
        return self.vault_root

    def _update_subtitle(self, path: str) -> None:
        folder_name = os.path.basename(os.path.abspath(path))
        self.border_subtitle = folder_name or path

    def compose(self) -> ComposeResult:
        with Horizontal(id="sidebar-top-bar"):
            yield Button("📁 Cambiar [Ctrl+O]", id="btn-change-vault")
            yield Button("✕", id="btn-close-sidebar", tooltip="Ocultar menú [Ctrl+B]")
        yield DirectoryTree(path=self.vault_root, id="vault-tree")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-sidebar":
            event.stop()
            self.post_message(self.ToggleSidebarRequested())

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Propagate file selection event to the parent app."""
        event.stop()
        self.post_message(self.FileSelected(event.path))

    def update_vault_root(self, new_path: str) -> None:
        self.vault_root = new_path
        self._update_subtitle(new_path)
        tree = self.query_one("#vault-tree", DirectoryTree)
        tree.path = new_path
        tree.reload()
