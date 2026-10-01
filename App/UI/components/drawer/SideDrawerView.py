"""Collapsible side drawer widget for navigation to settings and chat history."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label


class SideDrawerView(Widget):
    """Collapsible lateral drawer on the left side of the screen."""

    DEFAULT_CSS = """
    SideDrawerView {
        width: 28;
        min-width: 24;
        max-width: 32;
        height: 1fr;
        background: $panel;
        border-right: thick $line-strong;
        padding: 1 1;
        layout: vertical;
        display: none;
    }

    SideDrawerView.-open {
        display: block;
    }

    #drawer-title-bar {
        width: 100%;
        height: 3;
        margin-bottom: 1;
        border-bottom: solid $line;
        padding: 0 1;
    }

    #drawer-title {
        color: $brand-bright;
        text-style: bold;
        width: 1fr;
    }

    #drawer-subtitle {
        color: $ink-faint;
        text-style: italic;
    }

    .drawer-btn {
        width: 100%;
        height: 3;
        margin-bottom: 1;
        background: $boost;
        color: $ink;
        border: none;
        text-align: left;
        padding: 0 1;
    }

    .drawer-btn:hover {
        background: $brand 30%;
        color: $brand-bright;
        text-style: bold;
    }

    #btn-close-drawer {
        width: 100%;
        height: 2;
        dock: bottom;
        background: transparent;
        color: $ink-faint;
        border: none;
        text-align: center;
    }

    #btn-close-drawer:hover {
        color: $error;
        text-style: bold;
    }
    """

    class OpenSettings(Message):
        """Dispatched when the user clicks the Settings option."""
        pass

    class OpenChatHistory(Message):
        """Dispatched when the user clicks the Chat History option."""
        pass

    class NewChatRequested(Message):
        """Dispatched when the user clicks to start a new chat."""
        pass

    class CloseDrawer(Message):
        """Dispatched when user requests closing the drawer."""
        pass

    def compose(self) -> ComposeResult:
        with Vertical(id="drawer-title-bar"):
            yield Label("✦ MENÚ PRINCIPAL", id="drawer-title")
            yield Label("Lazy Obsidian", id="drawer-subtitle")

        yield Button("💬 Historial de Chats", id="btn-drawer-history", classes="drawer-btn")
        yield Button("➕ Nueva Conversación", id="btn-drawer-new-chat", classes="drawer-btn")
        yield Button("⚙️ Configuración", id="btn-drawer-settings", classes="drawer-btn")

        yield Button("◀ Cerrar menú [Ctrl+M]", id="btn-close-drawer")

    def toggle(self) -> bool:
        """Toggles drawer visibility. Returns True if now open, False if closed."""
        if "-open" in self.classes:
            self.remove_class("-open")
            return False
        else:
            self.add_class("-open")
            return True

    def open(self) -> None:
        self.add_class("-open")

    def close(self) -> None:
        self.remove_class("-open")

    @property
    def is_open(self) -> bool:
        return "-open" in self.classes

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        btn_id = event.button.id
        if btn_id == "btn-drawer-history":
            self.post_message(self.OpenChatHistory())
        elif btn_id == "btn-drawer-new-chat":
            self.post_message(self.NewChatRequested())
        elif btn_id == "btn-drawer-settings":
            self.post_message(self.OpenSettings())
        elif btn_id == "btn-close-drawer":
            self.post_message(self.CloseDrawer())
