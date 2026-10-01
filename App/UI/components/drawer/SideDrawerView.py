"""Collapsible side drawer widget displaying direct chat history, new chat and settings."""

from datetime import datetime
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Click
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Label, Static

from App.DB.storage import AppDatabase, ChatSession


def _format_time_display(timestamp: str | None) -> str:
    """Formats an ISO timestamp into a readable HH:MM or DD/MM string."""
    if not timestamp:
        return ""
    try:
        dt = datetime.fromisoformat(timestamp)
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        now = datetime.now(dt.tzinfo)
        if dt.date() == now.date():
            return dt.strftime("%H:%M")
        return dt.strftime("%d/%m")
    except Exception:
        if "T" in timestamp and len(timestamp) >= 16:
            return timestamp.split("T")[1][:5]
        return timestamp[:5]


class ContextAction(Static):
    """Clean, flat interactive menu item designed for popup context menus without button chrome."""

    can_focus = True

    DEFAULT_CSS = """
    ContextAction {
        width: 100%;
        height: 1;
        padding: 0 1;
        margin-bottom: 1;
        background: #232935;
        color: #dfe3ea;
    }

    ContextAction:hover, ContextAction:focus {
        background: #8b7bf7;
        color: #ffffff;
        text-style: bold;
    }

    ContextAction.-danger {
        color: #f07178;
    }

    ContextAction.-danger:hover, ContextAction.-danger:focus {
        background: #f07178;
        color: #0e1014;
        text-style: bold;
    }

    ContextAction.-dim {
        color: #7d879c;
        margin-bottom: 0;
    }

    ContextAction.-dim:hover, ContextAction.-dim:focus {
        background: #2a3040;
        color: #dfe3ea;
    }
    """

    class Pressed(Message):
        def __init__(self, action: str) -> None:
            super().__init__()
            self.action = action

    def __init__(self, label: str, action: str, classes: str = "", **kwargs) -> None:
        super().__init__(label, classes=classes, **kwargs)
        self.action = action

    def on_click(self, event: Click) -> None:
        event.stop()
        self.post_message(self.Pressed(self.action))


class PinContextMenuModal(ModalScreen[str | None]):
    """Minimal anchored context box shown right next to the clicked conversation.
    
    Subtly dims the background with a soft translucent overlay without obscuring or blacking it out.
    """

    DEFAULT_CSS = """
    PinContextMenuModal {
        background: rgba(0,0,0,0.30);
        align: left top;
    }

    #pin-context-box {
        width: 26;
        height: auto;
        background: #161920;
        border: solid #8b7bf7;
        padding: 1 1;
        layout: vertical;
    }

    #pin-context-title {
        width: 100%;
        height: auto;
        color: #a99bff;
        text-style: bold;
        text-align: center;
        border-bottom: solid #2a3040;
        padding-bottom: 1;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        session: ChatSession,
        anchor_x: int = 32,
        anchor_y: int = 10,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.session = session
        self.anchor_x = anchor_x
        self.anchor_y = anchor_y

    def compose(self) -> ComposeResult:
        pin_label = "Desfijar conversación" if self.session.is_pinned else "✦ Fijar conversación"
        with Vertical(id="pin-context-box"):
            disp_title = self.session.title if len(self.session.title) <= 18 else self.session.title[:17] + "…"
            yield Label(disp_title, id="pin-context-title")
            yield ContextAction(pin_label, action="toggle_pin", id="act-ctx-pin")
            yield ContextAction("✕ Eliminar chat", action="delete", classes="-danger", id="act-ctx-delete")
            yield ContextAction("Cerrar", action="cancel", classes="-dim", id="act-ctx-cancel")

    def on_mount(self) -> None:
        """Positions the context box directly next to the clicked conversation and softly dims background."""
        self.styles.background = "rgba(0,0,0,0.30)"
        box = self.query_one("#pin-context-box")
        box_width = 26
        box_height = 8
        max_x = max(0, self.app.size.width - box_width - 1)
        max_y = max(0, self.app.size.height - box_height - 1)

        x = min(self.anchor_x, max_x)
        y = min(self.anchor_y, max_y)
        box.styles.offset = (x, y)

    def on_click(self, event: Click) -> None:
        """Dismiss if clicking anywhere outside the context box."""
        try:
            box = self.query_one("#pin-context-box")
            if not box.region.contains(event.screen_x, event.screen_y):
                self.dismiss(None)
        except Exception:
            self.dismiss(None)

    @on(ContextAction.Pressed)
    def on_action_pressed(self, event: ContextAction.Pressed) -> None:
        if event.action == "cancel":
            self.dismiss(None)
        else:
            self.dismiss(event.action)


class ChatHistoryItem(Vertical):
    """Minimalist chat session entry displaying title, clean terminal pin glyph, and last activity time."""

    DEFAULT_CSS = """
    ChatHistoryItem {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
        background: transparent;
        border-left: solid transparent;
    }

    ChatHistoryItem:hover {
        background: $boost;
        border-left: solid $brand;
    }

    ChatHistoryItem.-active {
        background: $panel;
        border-left: thick $primary;
    }

    .history-item-top {
        width: 100%;
        height: 1;
        layout: horizontal;
    }

    .history-item-title {
        width: 1fr;
        color: $ink;
        text-style: none;
    }

    ChatHistoryItem.-active .history-item-title {
        color: $brand-bright;
        text-style: bold;
    }

    .history-item-time {
        width: auto;
        color: $ink-faint;
        text-style: none;
        text-align: right;
    }

    .history-item-pin {
        width: auto;
        color: $accent;
        margin-right: 1;
        text-style: bold;
    }
    """

    class Selected(Message):
        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    class RightClicked(Message):
        def __init__(self, session: ChatSession, screen_x: int, screen_y: int) -> None:
            super().__init__()
            self.session = session
            self.screen_x = screen_x
            self.screen_y = screen_y

    def __init__(self, session: ChatSession, is_active: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.session = session
        self.is_active = is_active
        if is_active:
            self.add_class("-active")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="history-item-top"):
            # Icono sobrio y elegante acorde a la estética TUI (no emoji genérico)
            if self.session.is_pinned:
                label_pin = Label("▲", classes="history-item-pin")
                label_pin.tooltip = "Fijado"
                yield label_pin
            disp_title = self.session.title if len(self.session.title) <= 18 else self.session.title[:17] + "…"
            yield Label(disp_title, classes="history-item-title")
            time_str = _format_time_display(self.session.updated_at)
            yield Label(time_str, classes="history-item-time")

    def on_click(self, event: Click) -> None:
        if event.button == 3:  # Right-click
            event.stop()
            # Calculate position to anchor popup right next to this item
            target_x = self.region.x + self.region.width
            target_y = self.region.y
            self.post_message(self.RightClicked(self.session, target_x, target_y))
        elif event.button == 1:  # Left-click
            event.stop()
            self.post_message(self.Selected(self.session.id))


class SideDrawerView(Widget):
    """Collapsible lateral drawer on the left side of the screen with direct chat history."""

    DEFAULT_CSS = """
    SideDrawerView {
        width: 32;
        min-width: 28;
        max-width: 36;
        height: 1fr;
        background: $panel;
        border-right: solid $line;
        padding: 1 1;
        layout: vertical;
        display: none;
    }

    SideDrawerView.-open {
        display: block;
    }

    #drawer-title-bar {
        width: 100%;
        height: auto;
        margin-bottom: 1;
        border-bottom: solid $line;
        padding-bottom: 1;
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
        background: $surface;
        color: $brand-bright;
        border-left: solid $brand;
    }

    #drawer-section-pinned {
        width: 100%;
        height: 1;
        color: $accent;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
        border-bottom: solid $line;
        display: none;
    }

    #drawer-pinned-list {
        width: 100%;
        height: auto;
        layout: vertical;
        margin-bottom: 1;
        display: none;
    }

    #drawer-section-history {
        width: 100%;
        height: 1;
        color: $ink-faint;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
        border-bottom: solid $line;
    }

    #drawer-history-list {
        width: 100%;
        height: 1fr;
        layout: vertical;
        overflow-y: auto;
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

    class SessionSelected(Message):
        """Dispatched when user clicks a chat in the sidebar history."""
        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    class NewChatRequested(Message):
        """Dispatched when the user clicks to start a new chat."""
        pass

    class CloseDrawer(Message):
        """Dispatched when user requests closing the drawer."""
        pass

    def __init__(self, current_session_id: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.current_session_id = current_session_id
        self.db = AppDatabase.get_instance()

    def compose(self) -> ComposeResult:
        with Vertical(id="drawer-title-bar"):
            yield Label("✦ LAZY OBSIDIAN", id="drawer-title")
            yield Label("Historial y navegación", id="drawer-subtitle")

        yield Button("➕ Nueva Conversación", id="btn-drawer-new-chat", classes="drawer-btn")
        yield Button("⚙️ Configuración", id="btn-drawer-settings", classes="drawer-btn")

        yield Label("FIJADOS", id="drawer-section-pinned")
        yield Vertical(id="drawer-pinned-list")

        yield Label("HISTORIAL RECIENTE", id="drawer-section-history")
        yield VerticalScroll(id="drawer-history-list")

        yield Button("◀ Cerrar menú [Ctrl+M]", id="btn-close-drawer")

    def on_mount(self) -> None:
        self.refresh_history()

    def refresh_history(self, current_session_id: str | None = None) -> None:
        """Reloads the list of persisted real sessions into the sidebar directly."""
        if current_session_id:
            self.current_session_id = current_session_id

        try:
            pinned_sec = self.query_one("#drawer-section-pinned", Label)
            pinned_list = self.query_one("#drawer-pinned-list", Vertical)
            list_container = self.query_one("#drawer-history-list", VerticalScroll)
        except Exception:
            return

        for child in list(pinned_list.children):
            child.remove()
        for child in list(list_container.children):
            child.remove()

        sessions = self.db.list_sessions(require_messages=True)
        if not sessions:
            pinned_sec.display = False
            pinned_list.display = False
            list_container.mount(Label("Sin chats guardados", classes="history-item-time"))
            return

        pinned_sessions = [s for s in sessions if s.is_pinned]
        unpinned_sessions = [s for s in sessions if not s.is_pinned]

        # Si no hay chats fijados no poner nada hasta que se fijen
        if pinned_sessions:
            pinned_sec.display = True
            pinned_list.display = True
            for s in pinned_sessions:
                is_active = (s.id == self.current_session_id)
                pinned_list.mount(ChatHistoryItem(session=s, is_active=is_active))
        else:
            pinned_sec.display = False
            pinned_list.display = False

        # Lista de historial regular
        if unpinned_sessions:
            for s in unpinned_sessions:
                is_active = (s.id == self.current_session_id)
                list_container.mount(ChatHistoryItem(session=s, is_active=is_active))
        elif not pinned_sessions:
            list_container.mount(Label("Sin chats guardados", classes="history-item-time"))

    def toggle(self) -> bool:
        """Toggles drawer visibility. Returns True if now open, False if closed."""
        if "-open" in self.classes:
            self.remove_class("-open")
            return False
        else:
            self.refresh_history()
            self.add_class("-open")
            return True

    def open(self) -> None:
        self.refresh_history()
        self.add_class("-open")

    def close(self) -> None:
        self.remove_class("-open")

    @on(Button.Pressed, "#btn-drawer-new-chat")
    def on_new_chat(self) -> None:
        self.post_message(self.NewChatRequested())

    @on(Button.Pressed, "#btn-drawer-settings")
    def on_settings(self) -> None:
        self.post_message(self.OpenSettings())

    @on(Button.Pressed, "#btn-close-drawer")
    def on_close(self) -> None:
        self.post_message(self.CloseDrawer())

    @on(ChatHistoryItem.Selected)
    def on_chat_selected(self, event: ChatHistoryItem.Selected) -> None:
        self.post_message(self.SessionSelected(event.session_id))
