from textual.app import App, ComposeResult
from textual.widgets import Welcome, Input, Label, DataTable
from textual.containers import Vertical, Horizontal
from textual import events
from random import randint


from components.prompt.SearchBarView import SearchBarView
from components.filemanager.FileManagerView import FileManagerView
from components.chat.ChatView import ChatView


class Myapp(App):
    CSS_PATH = "CSS/app.tcss"

    def compose(self):
        with Vertical(id="main"):
            with Horizontal(id= "header"):
                yield Label("LAZY OBSIDIAN")
            with Horizontal(id = "home"):
                yield ChatView()
                yield FileManagerView()
            with Horizontal(id="home-bar"):
                yield SearchBarView()



# run de lazy app
if __name__ == "__main__":
    app = Myapp()
    app.run()


