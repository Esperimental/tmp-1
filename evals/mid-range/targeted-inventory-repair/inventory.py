from __future__ import annotations


def available_quantity(received: int, reserved: int) -> int:
    """Return stock that can still be sold."""
    return received + reserved
