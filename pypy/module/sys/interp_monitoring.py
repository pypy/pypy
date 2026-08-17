from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.pymonitoring import (
    MonitoringState, NUM_TOOLS, NUM_EVENTS, LOCAL_EVENTS, UNGROUPED_EVENTS,
    EVENT_NAMES, C_RETURN_EVENTS, C_CALL_EVENTS)


class W_MonitoringSentinel(W_Root):
    def __init__(self, name):
        self.name = name

    def descr_repr(self, space):
        return space.newtext("<%s>" % self.name)


W_MonitoringSentinel.typedef = TypeDef("sys.monitoring.sentinel",
    __repr__=interp2app(W_MonitoringSentinel.descr_repr),
)


class W_EventsNamespace(W_Root):
    def __init__(self):
        self.NO_EVENTS = 0
        self.PY_START = 1 << 0
        self.PY_RESUME = 1 << 1
        self.PY_RETURN = 1 << 2
        self.PY_YIELD = 1 << 3
        self.CALL = 1 << 4
        self.LINE = 1 << 5
        self.INSTRUCTION = 1 << 6
        self.JUMP = 1 << 7
        self.BRANCH = 1 << 8
        self.STOP_ITERATION = 1 << 9
        self.RAISE = 1 << 10
        self.EXCEPTION_HANDLED = 1 << 11
        self.PY_UNWIND = 1 << 12
        self.PY_THROW = 1 << 13
        self.RERAISE = 1 << 14
        self.C_RETURN = 1 << 15
        self.C_RAISE = 1 << 16


W_EventsNamespace.typedef = TypeDef("sys.monitoring.events", **{
    name: interp_attrproperty(name, W_EventsNamespace, wrapfn="newint")
    for name in EVENT_NAMES + ["NO_EVENTS"]
})


class Singletons(object):
    def __init__(self, space):
        self.w_disable = W_MonitoringSentinel("DISABLE")
        self.w_missing = W_MonitoringSentinel("MISSING")
        self.w_events = W_EventsNamespace()


def w_disable(space):
    return space.fromcache(Singletons).w_disable


def w_missing(space):
    return space.fromcache(Singletons).w_missing


def w_events(space):
    return space.fromcache(Singletons).w_events


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


def check_tool_in_use(space, tool_id):
    state = space.fromcache(MonitoringState)
    if state.tool_names[tool_id] is None:
        raise oefmt(space.w_ValueError, "tool %d is not in use", tool_id)


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
        raise oefmt(space.w_ValueError, "invalid event set %s", hex(event_set))
    if (event_set & C_RETURN_EVENTS) and (event_set & C_CALL_EVENTS) != C_CALL_EVENTS:
        raise oefmt(space.w_ValueError,
            "cannot set C_RETURN or C_RAISE events independently")
    event_set &= ~C_RETURN_EVENTS
    check_tool_in_use(space, tool_id)
    state = space.fromcache(MonitoringState)
    old_any_events = state.any_events
    state.global_events[tool_id] = event_set
    state.recompute_any_events()
    if state.any_events != old_any_events:
        # any_events is quasi-immutable/promoted at every fire2/fire3 call
        # site (see pymonitoring.should_fire); writing it already
        # invalidates compiled loops that folded in the old value, but
        # force_all_frames() additionally kicks frames *currently*
        # executing already-compiled assembly out to the interpreter, the
        # same way ExecutionContext.settrace() does for w_tracefunc.
        space.getexecutioncontext().force_all_frames()
    # Local (per-code) events and DISABLE/JUMP/BRANCH/LINE/INSTRUCTION
    # instrumentation are later phases -- see sys.monitoring.md.


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
        raise oefmt(space.w_ValueError, "invalid local event set %s", hex(event_set))
    check_tool_in_use(space, tool_id)
    state = space.fromcache(MonitoringState)
    per_tool = state.local_events.get(code, None)
    if per_tool is None:
        per_tool = [0] * NUM_TOOLS
        state.local_events[code] = per_tool
    per_tool[tool_id] = event_set
    # Bookkeeping only for now, see set_events above.


def restart_events(space):
    # No live per-instruction instrumentation exists yet (see
    # set_local_events above), so there is nothing to re-arm.
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
