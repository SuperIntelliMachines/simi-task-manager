"""Do-not-disturb window helpers for policy reminder delivery."""

from __future__ import annotations

from datetime import time


def is_within_dnd_window(
    current: time,
    dnd_start: time | None,
    dnd_end: time | None,
) -> bool:
    """Return True when `current` falls inside the configured DND window."""
    if dnd_start is None or dnd_end is None:
        return False
    if dnd_start == dnd_end:
        return False

    if dnd_start < dnd_end:
        return dnd_start <= current < dnd_end

    # Overnight window, e.g. 21:00 → 08:00
    return current >= dnd_start or current < dnd_end
