import os
from textual.widget import Widget
from textual.widgets import Button, DirectoryTree

VAULT_ROOT = "/home/alerrsi/Documents"


class FileManagerView(Widget):

    VAULT_ROOT = VAULT_ROOT

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

    def update_vault_root(self, new_path: str) -> None:
        global VAULT_ROOT
        VAULT_ROOT = new_path
        FileManagerView.VAULT_ROOT = new_path
        self._update_subtitle(new_path)
        tree = self.query_one("#vault-tree", DirectoryTree)
        tree.path = new_path
        tree.reload()
