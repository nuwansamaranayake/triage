import pytest

from app.engine.registry import (
    ALLOWED_TRANSITIONS,
    INITIAL_STATE,
    STATES,
    IllegalTransition,
    validate_transition,
)


def test_every_legal_single_step_is_accepted():
    for frm, to in ALLOWED_TRANSITIONS:
        validate_transition(frm, to)  # must not raise


def test_the_legal_chain_covers_all_states_in_order():
    assert STATES == ("new", "triaged", "in_progress", "fixed", "verified")
    assert INITIAL_STATE == "new"
    assert ALLOWED_TRANSITIONS == {(STATES[i], STATES[i + 1]) for i in range(len(STATES) - 1)}


@pytest.mark.parametrize("frm,to", [
    ("new", "fixed"),            # skip forward
    ("new", "verified"),         # skip to end
    ("triaged", "new"),          # backward
    ("verified", "fixed"),       # backward from terminal
    ("fixed", "in_progress"),    # backward
    ("new", "new"),              # self-loop
])
def test_illegal_transitions_raise_typed_error(frm, to):
    with pytest.raises(IllegalTransition) as exc:
        validate_transition(frm, to)
    assert exc.value.from_state == frm
    assert exc.value.to_state == to
    assert "illegal transition" in str(exc.value)


def test_unknown_states_raise_typed_error():
    with pytest.raises(IllegalTransition):
        validate_transition("new", "reopened")
    with pytest.raises(IllegalTransition):
        validate_transition("bogus", "triaged")
