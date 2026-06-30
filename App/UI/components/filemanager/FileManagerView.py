from textual.widget import Widget
from textual.containers import Vertical
from textual.widgets import Label, DirectoryTree
from os import listdir




class FileManagerView(Widget):

    DEFAULT_CSS = """
    FilemanagerView {
    width: 30%;
    height: 1fr;
    color: white;
    background: green;
    
    }

    #big-files {
    color: white;
    
    border: solid white;
    width: 30%;
    height: 1fr;
    }
    """
    def compose(self):
        with Vertical(id="big-files"):
            yield DirectoryTree(path="/home/alerrsi/Documents")
        