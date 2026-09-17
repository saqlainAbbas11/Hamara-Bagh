"""Small request-parsing helpers shared by the route modules."""
from flask import abort, request


def int_arg(name, default, minimum=None, maximum=None):
    """Read an integer query parameter safely.

    A bare int(request.args.get(...)) crashes with a 500 on garbage input
    like ?limit=abc; this returns a clean 400 instead, and clamps the result
    to [minimum, maximum] so callers never get absurd values.
    """
    raw = request.args.get(name)
    if raw is None or raw == "":
        value = default
    else:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            abort(400, description=f"Query parameter '{name}' must be a whole number.")
    if minimum is not None and value < minimum:
        value = minimum
    if maximum is not None and value > maximum:
        value = maximum
    return value
