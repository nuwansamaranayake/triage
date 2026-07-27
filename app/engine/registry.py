"""The issue registry state machine. Deterministic, loud, append-only history.

States move forward one step only:

    new -> triaged -> in_progress -> fixed -> verified

Anything else — backward, skipping, self-loops, unknown states — raises IllegalTransition,
a typed error that carries the offending pair. The API maps it to 409; nothing is ever
silently coerced into a legal state.
"""
from __future__ import annotations

STATES = ("new", "triaged", "in_progress", "fixed", "verified")
INITIAL_STATE = "new"
ALLOWED_TRANSITIONS = {
    ("new", "triaged"),
    ("triaged", "in_progress"),
    ("in_progress", "fixed"),
    ("fixed", "verified"),
}


class IllegalTransition(Exception):
    """Typed rejection: carries the offending pair so callers render facts, not vibes."""

    def __init__(self, from_state: str, to_state: str, reason: str):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        super().__init__(f"illegal transition {from_state} -> {to_state}: {reason}")


def validate_transition(from_state: str, to_state: str) -> None:
    """Raise IllegalTransition unless from_state -> to_state is an allowed single step."""
    if from_state not in STATES:
        raise IllegalTransition(from_state, to_state, f"unknown from-state {from_state!r}")
    if to_state not in STATES:
        raise IllegalTransition(from_state, to_state, f"unknown to-state {to_state!r}")
    if (from_state, to_state) not in ALLOWED_TRANSITIONS:
        raise IllegalTransition(
            from_state, to_state,
            "states advance one step: new -> triaged -> in_progress -> fixed -> verified")
