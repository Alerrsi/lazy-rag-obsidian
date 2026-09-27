from textual.widget import Widget
from textual.widgets import DirectoryTree

VAULT_ROOT = "/home/alerrsi/Documents"


class FileManagerView(Widget):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "ARCHIVOS"

    def compose(self):
        yield DirectoryTree(path=VAULT_ROOT, id="vault-tree")
