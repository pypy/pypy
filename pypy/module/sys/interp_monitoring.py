from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.pycode import PyCode

NUM_TOOLS = 6
NUM_EVENTS = 17
LOCAL_EVENTS = 10
UNGROUPED_EVENTS = 15

EVENT_NAMES = [
    "PY_START", "PY_RESUME", "PY_RETURN", "PY_YIELD", "CALL", "LINE",
    "INSTRUCTION", "JUMP", "BRANCH", "STOP_ITERATION", "RAISE",
    "EXCEPTION_HANDLED", "PY_UNWIND", "PY_THROW", "RERAISE",
    "C_RETURN", "C_RAISE",
]

CALL = 4
C_RETURN = 15
C_RAISE = 16
C_RETURN_EVENTS = (1 << C_RETURN) | (1 << C_RAISE)
C_CALL_EVENTS = C_RETURN_EVENTS | (1 << CALL)


class MonitoringState(object):
    def __init__(self, space):
        self.tool_names = [None] * NUM_TOOLS
        self.callbacks = [None] * (NUM_TOOLS * NUM_EVENTS)
        self.global_events = [0] * NUM_TOOLS
        self.local_events = {}   # PyCode -> [event_set per tool]


def _popcount(x):
    count = 0
    while x:
        x &= x - 1
        count += 1
    return count


def _bit_length(x):
    n = 0
    while x:
        x >>= 1
        n += 1
    return n


def check_valid_tool(space, tool_id):
    if tool_id < 0 or tool_id >= NUM_TOOLS:
        raise oefmt(space.w_ValueError,
            "invalid tool %d (must be between 0 and 5)", tool_id)


def _get_code(space, w_code):
    if not isinstance(w_code, PyCode):
        raise oefmt(space.w_TypeError, "code must be a code object")
    return w_code


@unwrap_spec(tool_id=int)
def use_tool_id(space, tool_id, w_name):
    check_valid_tool(space, tool_id)
    if not space.isinstance_w(w_name, space.w_unicode):
        raise oefmt(space.w_ValueError, "tool name must be a str")
    state = space.fromcache(MonitoringState)
    if state.tool_names[tool_id] is not None:
        raise oefmt(space.w_ValueError, "tool %d is already in use", tool_id)
    state.tool_names[tool_id] = w_name


@unwrap_spec(tool_id=int)
def free_tool_id(space, tool_id):
    check_valid_tool(space, tool_id)
    state = space.fromcache(MonitoringState)
    state.tool_names[tool_id] = None


@unwrap_spec(tool_id=int)
def get_tool(space, tool_id):
    check_valid_tool(space, tool_id)
    state = space.fromcache(MonitoringState)
    w_name = state.tool_names[tool_id]
    if w_name is None:
        return space.w_None
    return w_name


@unwrap_spec(tool_id=int, event=int)
def register_callback(space, tool_id, event, w_func):
    check_valid_tool(space, tool_id)
    if _popcount(event) != 1:
        raise oefmt(space.w_ValueError,
            "The callback can only be set for one event at a time")
    event_id = _bit_length(event) - 1
    if event_id < 0 or event_id >= NUM_EVENTS:
        raise oefmt(space.w_ValueError, "invalid event %d", event)
    from pypy.module.sys.vm import audit
    audit(space, "sys.monitoring.register_callback", [w_func])
    state = space.fromcache(MonitoringState)
    idx = tool_id * NUM_EVENTS + event_id
    w_old = state.callbacks[idx]
    state.callbacks[idx] = None if space.is_none(w_func) else w_func
    if w_old is None:
        return space.w_None
    return w_old


@unwrap_spec(tool_id=int)
def get_events(space, tool_id):
    check_valid_tool(space, tool_id)
    state = space.fromcache(MonitoringState)
    return space.newint(state.global_events[tool_id])


@unwrap_spec(tool_id=int, event_set=int)
def set_events(space, tool_id, event_set):
    check_valid_tool(space, tool_id)
    if event_set < 0 or event_set >= (1 << NUM_EVENTS):
        raise oefmt(space.w_ValueError, "invalid event set 0x%x", event_set)
    if (event_set & C_RETURN_EVENTS) and (event_set & C_CALL_EVENTS) != C_CALL_EVENTS:
        raise oefmt(space.w_ValueError,
            "cannot set C_RETURN or C_RAISE events independently")
    event_set &= ~C_RETURN_EVENTS
    state = space.fromcache(MonitoringState)
    state.global_events[tool_id] = event_set
    # Phase 1 (scaffolding): bookkeeping only. Wiring this into the
    # interpreter's dispatch loop so events actually fire is later
    # phases -- see sys.monitoring.md.


@unwrap_spec(tool_id=int)
def get_local_events(space, tool_id, w_code):
    code = _get_code(space, w_code)
    check_valid_tool(space, tool_id)
    state = space.fromcache(MonitoringState)
    per_tool = state.local_events.get(code, None)
    if per_tool is None:
        return space.newint(0)
    return space.newint(per_tool[tool_id])


@unwrap_spec(tool_id=int, event_set=int)
def set_local_events(space, tool_id, w_code, event_set):
    code = _get_code(space, w_code)
    check_valid_tool(space, tool_id)
    if (event_set & C_RETURN_EVENTS) and (event_set & C_CALL_EVENTS) != C_CALL_EVENTS:
        raise oefmt(space.w_ValueError,
            "cannot set C_RETURN or C_RAISE events independently")
    event_set &= ~C_RETURN_EVENTS
    if event_set < 0 or event_set >= (1 << LOCAL_EVENTS):
        raise oefmt(space.w_ValueError, "invalid local event set 0x%x", event_set)
    state = space.fromcache(MonitoringState)
    per_tool = state.local_events.get(code, None)
    if per_tool is None:
        per_tool = [0] * NUM_TOOLS
        state.local_events[code] = per_tool
    per_tool[tool_id] = event_set
    # Phase 1 (scaffolding): bookkeeping only, see set_events above.


def restart_events(space):
    # Phase 1 (scaffolding): no live per-instruction instrumentation
    # exists yet, so there is nothing to re-arm.
    pass


def _all_events(space):
    state = space.fromcache(MonitoringState)
    w_res = space.newdict()
    for e in range(UNGROUPED_EVENTS):
        tools = 0
        for tool_id in range(NUM_TOOLS):
            if (state.global_events[tool_id] >> e) & 1:
                tools |= 1 << tool_id
        if tools:
            space.setitem(w_res, space.newtext(EVENT_NAMES[e]), space.newint(tools))
    return w_res
