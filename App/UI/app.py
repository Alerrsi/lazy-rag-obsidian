from textual.app import App, ComposeResult
from textual.widgets import Welcome, Input, Label, DataTable, RichLog
from textual.containers import Vertical, Horizontal
from textual import on

from .components.prompt.SearchBarView import SearchBarView
from .components.filemanager.FileManagerView import FileManagerView
from .components.chat.ChatView import ChatView



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

    def on_mount(self) -> None:
        chat = self.query_one(ChatView)
        barra = self.query_one(SearchBarView)
        barra.on_send = chat.on_input_submitted  

    @on(Input.Submitted, "#message")
    def send(self) -> None:
        barra = self.query_one(SearchBarView)
        barra.send()
        entrada = self.query_one("#message").value = ""
        




    





