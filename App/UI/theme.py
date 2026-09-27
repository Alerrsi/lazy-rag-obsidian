"""Design tokens for Lazy Obsidian.

A calm, low-contrast dark palette: the app is a reading surface, so the chrome
stays quiet and only the active element (the prompt) gets a bright accent.
"""

from textual.theme import Theme

LAZY_OBSIDIAN = Theme(
    name="lazy-obsidian",
    primary="#8b7bf7",
    secondary="#4ecdc4",
    accent="#f5c451",
    success="#5fd68a",
    warning="#f5a35c",
    error="#f07178",
    foreground="#dfe3ea",
    background="#0e1014",
    surface="#161920",
    panel="#1b1f27",
    boost="#232935",
    dark=True,
    luminosity_spread=0.12,
    text_alpha=0.95,
    variables={
        # Chrome
        "line": "#2a3040",
        "line-soft": "#20242e",
        "line-strong": "#3a4256",
        # Ink
        "ink": "#dfe3ea",
        "ink-dim": "#7d879c",
        "ink-faint": "#565f72",
        "brand": "#8b7bf7",
        "brand-bright": "#a99bff",
    },
)
