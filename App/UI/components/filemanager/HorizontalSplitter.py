"""Interactive divider widget that enables horizontal resizing between panes with mouse drag."""

from textual.events import MouseDown, MouseMove, MouseUp
from textual.widget import Widget


class HorizontalSplitter(Widget):
    """A vertical separator handle that can be dragged horizontally with the mouse."""

    DEFAULT_CSS = """
    HorizontalSplitter {
        width: 1;
        height: 1fr;
        background: transparent;
        color: $line;
    }

    HorizontalSplitter:hover {
        background: $brand 25%;
        color: $brand-bright;
    }

    HorizontalSplitter.-dragging {
        background: $brand 50%;
        color: $brand-bright;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._dragging = False

    def render(self) -> str:
        # Subtle dotted or vertical line indicator
        return "│"

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.button == 1:  # Left click
            self.capture_mouse()
            self._dragging = True
            self.add_class("-dragging")
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
            event.stop()
