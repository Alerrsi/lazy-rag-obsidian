"""Interactive divider widget that enables horizontal resizing between panes with mouse drag."""

import sys
from textual.events import Enter, Leave, MouseDown, MouseMove, MouseUp
from textual.widget import Widget


class HorizontalSplitter(Widget):
    """A vertical separator handle that can be dragged horizontally with the mouse."""

    DEFAULT_CSS = """
    HorizontalSplitter {
        width: 1;
        height: 1fr;
        background: transparent;
        color: $line;
        pointer: ew-resize;
    }

    HorizontalSplitter:hover {
        background: $brand 25%;
        color: $brand-bright;
        pointer: ew-resize;
    }

    HorizontalSplitter.-dragging {
        background: $brand 50%;
        color: $brand-bright;
        pointer: ew-resize;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._dragging = False

    def render(self) -> str:
        # Subtle dotted or vertical line indicator
        return "│"

    @staticmethod
    def _set_terminal_mouse_cursor(cursor_shape: str) -> None:
        """Emits standard OSC 22 escape sequence to set the hardware terminal mouse cursor shape."""
        try:
            # OSC 22 ; <shape> ST  (ESC ] 22 ; <shape> ESC \)
            sys.stdout.write(f"\x1b]22;{cursor_shape}\x1b\\")
            sys.stdout.flush()
        except OSError:
            pass

    def on_enter(self, event: Enter) -> None:
        """When mouse enters the splitter, change cursor to ew-resize via OSC 22."""
        self._set_terminal_mouse_cursor("ew-resize")

    def on_leave(self, event: Leave) -> None:
        """When mouse leaves the splitter, restore cursor to default unless currently dragging."""
        if not self._dragging:
            self._set_terminal_mouse_cursor("default")

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.button == 1:  # Left click
            self.capture_mouse()
            self._dragging = True
            self.add_class("-dragging")
            self._set_terminal_mouse_cursor("ew-resize")
            event.stop()

    def on_mouse_move(self, event: MouseMove) -> None:
        if self._dragging:
            home = self.app.query_one("#home")
            # Calculate width from the right boundary of the #home container
            right_boundary = home.region.x + home.region.width
            new_sidebar_width = right_boundary - event.screen_x

            # Clamp sidebar width so neither chat nor sidebar collapses completely
            min_width = 18
            max_width = max(24, home.region.width - 28)
            new_sidebar_width = max(min_width, min(new_sidebar_width, max_width))

            sidebar = self.app.query_one("#sidebar")
            sidebar.styles.width = new_sidebar_width
            event.stop()

    def on_mouse_up(self, event: MouseUp) -> None:
        if self._dragging:
            self.release_mouse()
            self._dragging = False
            self.remove_class("-dragging")
            self._set_terminal_mouse_cursor("default")
            event.stop()
