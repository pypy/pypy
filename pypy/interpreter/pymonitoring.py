NUM_TOOLS = 6
NUM_EVENTS = 17
LOCAL_EVENTS = 10
UNGROUPED_EVENTS = 15

PY_START = 0
PY_RESUME = 1
PY_RETURN = 2
PY_YIELD = 3
CALL = 4
LINE = 5
INSTRUCTION = 6
JUMP = 7
BRANCH = 8
STOP_ITERATION = 9
RAISE = 10
EXCEPTION_HANDLED = 11
PY_UNWIND = 12
PY_THROW = 13
RERAISE = 14
C_RETURN = 15
C_RAISE = 16

EVENT_NAMES = [
    "PY_START", "PY_RESUME", "PY_RETURN", "PY_YIELD", "CALL", "LINE",
    "INSTRUCTION", "JUMP", "BRANCH", "STOP_ITERATION", "RAISE",
    "EXCEPTION_HANDLED", "PY_UNWIND", "PY_THROW", "RERAISE",
    "C_RETURN", "C_RAISE",
]

C_RETURN_EVENTS = (1 << C_RETURN) | (1 << C_RAISE)
C_CALL_EVENTS = C_RETURN_EVENTS | (1 << CALL)


class MonitoringState(object):
    def __init__(self, space):
        self.tool_names = [None] * NUM_TOOLS
        self.callbacks = [None] * (NUM_TOOLS * NUM_EVENTS)
        self.global_events = [0] * NUM_TOOLS
        self.any_events = 0
        self.local_events = {}   # PyCode -> [event_set per tool]
        self.firing = False      # reentrancy guard, like ExecutionContext.is_tracing

    def recompute_any_events(self):
        any_events = 0
        for tool_id in range(NUM_TOOLS):
            any_events |= self.global_events[tool_id]
        self.any_events = any_events


def fire2(space, event_id, w_code, offset):
    """Fire a (code, instruction_offset) event, e.g. PY_START/PY_RESUME."""
    state = space.fromcache(MonitoringState)
    if state.firing or not (state.any_events >> event_id) & 1:
        return
    w_offset = space.newint(offset)
    for tool_id in range(NUM_TOOLS):
        if (state.global_events[tool_id] >> event_id) & 1:
            w_cb = state.callbacks[tool_id * NUM_EVENTS + event_id]
            if w_cb is not None:
                state.firing = True
                try:
                    space.call_function(w_cb, w_code, w_offset)
                finally:
                    state.firing = False


def fire3(space, event_id, w_code, offset, w_extra):
    """Fire a (code, instruction_offset, extra) event, e.g. PY_RETURN."""
    state = space.fromcache(MonitoringState)
    if state.firing or not (state.any_events >> event_id) & 1:
        return
    w_offset = space.newint(offset)
    for tool_id in range(NUM_TOOLS):
        if (state.global_events[tool_id] >> event_id) & 1:
            w_cb = state.callbacks[tool_id * NUM_EVENTS + event_id]
            if w_cb is not None:
                state.firing = True
                try:
                    space.call_function(w_cb, w_code, w_offset, w_extra)
                finally:
                    state.firing = False
