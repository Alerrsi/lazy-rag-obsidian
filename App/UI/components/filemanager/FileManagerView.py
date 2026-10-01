from pathlib import Path
import os
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DirectoryTree

VAULT_ROOT = "/home/alerrsi/Documents"


class FileManagerView(Widget):

    VAULT_ROOT = VAULT_ROOT

    class FileSelected(Message):
        """Dispatched when a file node is selected in the directory tree."""

        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "ARCHIVOS"
        self._update_subtitle(VAULT_ROOT)

    def _update_subtitle(self, path: str) -> None:
        folder_name = os.path.basename(os.path.abspath(path))
        self.border_subtitle = folder_name or path

    def compose(self):
        yield Button("📁 Cambiar [Ctrl+O]", id="btn-change-vault")
        yield DirectoryTree(path=VAULT_ROOT, id="vault-tree")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Propagate file selection event to the parent app."""
        event.stop()
        self.post_message(self.FileSelected(event.path))

    def update_vault_root(self, new_path: str) -> None:
        global VAULT_ROOT
        VAULT_ROOT = new_path
        FileManagerView.VAULT_ROOT = new_path
        self._update_subtitle(new_path)
        tree = self.query_one("#vault-tree", DirectoryTree)
        tree.path = new_path
        tree.reload()
