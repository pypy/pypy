from types import SimpleNamespace

DISABLE = object()
MISSING = object()

events = SimpleNamespace(
    NO_EVENTS=0,
    PY_START=1 << 0,
    PY_RESUME=1 << 1,
    PY_RETURN=1 << 2,
    PY_YIELD=1 << 3,
    CALL=1 << 4,
    LINE=1 << 5,
    INSTRUCTION=1 << 6,
    JUMP=1 << 7,
    BRANCH=1 << 8,
    STOP_ITERATION=1 << 9,
    RAISE=1 << 10,
    EXCEPTION_HANDLED=1 << 11,
    PY_UNWIND=1 << 12,
    PY_THROW=1 << 13,
    RERAISE=1 << 14,
    C_RETURN=1 << 15,
    C_RAISE=1 << 16,
)
