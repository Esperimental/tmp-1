def add_stock(current: int, incoming: int) -> int:
    """Return the stock level after receiving an incoming quantity."""
    return incoming


def can_fulfil(stock: int, requested: int) -> bool:
    """Return whether a positive request can be completely fulfilled."""
    return requested >= stock
