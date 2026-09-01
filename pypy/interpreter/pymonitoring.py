from rpython.rlib import jit
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef

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

FRAME_ENTRY_EVENTS = (1 << PY_START) | (1 << PY_RESUME) | (1 << PY_THROW)


class W_MonitoringSentinel(W_Root):
    """DISABLE/MISSING.  Lives here (interpreter core) rather than under
    pypy/module/sys, because call sites in pyopcode.py/baseobjspace.py need
    to produce MISSING for the CALL/C_RETURN/C_RAISE arg0 slot, and the
    interpreter core must not import from pypy/module/*."""
    def __init__(self, name):
        self.name = name

    def descr_repr(self, space):
        return space.newtext("<%s>" % self.name)


W_MonitoringSentinel.typedef = TypeDef("sys.monitoring.sentinel",
    __repr__=interp2app(W_MonitoringSentinel.descr_repr),
)


class Singletons(object):
    def __init__(self, space):
        self.w_disable = W_MonitoringSentinel("DISABLE")
        self.w_missing = W_MonitoringSentinel("MISSING")


def w_disable(space):
    return space.fromcache(Singletons).w_disable


def w_missing(space):
    return space.fromcache(Singletons).w_missing


class MonitoringState(object):
    _immutable_fields_ = ['any_events?', 'callbacks_version?']

    def __init__(self, space):
        self.tool_names = [None] * NUM_TOOLS
        self.callbacks = [None] * (NUM_TOOLS * NUM_EVENTS)
        self.callbacks_version = VersionTag()
        self.global_events = [0] * NUM_TOOLS
        self.any_events = 0
        self.disabled_codes = {}   # PyCode -> True, for restart_events()
        self.firing = False      # reentrancy guard, like ExecutionContext.is_tracing

    def recompute_any_events(self):
        any_events = 0
        for tool_id in range(NUM_TOOLS):
            any_events |= self.global_events[tool_id]
        self.any_events = any_events

    @jit.elidable
    def _get_callback(self, version_tag, index):
        assert version_tag is self.callbacks_version
        return self.callbacks[index]

    def get_callback(self, tool_id, event_id):
        version_tag = jit.promote(self.callbacks_version)
        index = callback_index(tool_id, event_id)
        return self._get_callback(version_tag, index)

    def set_callback(self, tool_id, event_id, w_callback):
        index = callback_index(tool_id, event_id)
        w_old = self.callbacks[index]
        if w_old is not w_callback:
            self.callbacks[index] = w_callback
            self.callbacks_version = VersionTag()
        return w_old


def _event_is_set(event_set, event_id):
    return (event_set >> event_id) & 1


def _control_event_id(event_id):
    """C_RETURN/C_RAISE are never actually stored in global_events (see
    set_events: their bits are always stripped before storing). Per PEP
    669, "C_RETURN and C_RAISE events will only be seen if the
    corresponding CALL event is being monitored", i.e. they ride on the
    CALL bit rather than having independent on/off state: registering
    only a C_RETURN callback and enabling just CALL (not C_RETURN) still
    fires C_RETURN. So any enabled-ness check for these two must test the
    CALL bit instead of their own."""
    if event_id == C_RETURN or event_id == C_RAISE:
        return CALL
    return event_id


def _event_can_be_disabled(event_id):
    return event_id < LOCAL_EVENTS


def callback_index(tool_id, event_id):
    return tool_id * NUM_EVENTS + event_id


def should_fire(space, event_id):
    """JIT-foldable check: does any tool want this event globally?

    Callers must check this *before* calling dispatch_global_event or
    dispatch_code_event, not rely
    on the (non-promoted) check inside those functions -- promoting here
    lets the JIT constant-fold away the call and its argument setup
    entirely when nobody is listening, the same way gettrace() promotes
    ExecutionContext.w_tracefunc.
    """
    state = space.fromcache(MonitoringState)
    any_events = jit.promote(state.any_events)
    return _event_is_set(any_events, _control_event_id(event_id))


def should_fire_any(space, event_mask):
    """Like should_fire, but for a bitmask of several plain event ids at
    once (e.g. FRAME_ENTRY_EVENTS). Not used for C_RETURN/C_RAISE, whose
    bit-mapping is handled by should_fire/dispatch_code_event individually."""
    state = space.fromcache(MonitoringState)
    any_events = jit.promote(state.any_events)
    return any_events & event_mask


def dispatch_global_event(space, event_id, w_code, offset, w_extra):
    """Fire a (code, instruction_offset, extra) event for a non-local
    event, e.g. PY_UNWIND/PY_THROW/RAISE/RERAISE/EXCEPTION_HANDLED --
    these aren't in LOCAL_EVENTS, so returning DISABLE from their
    callback is illegal.
    """
    if w_code.hidden_applevel:
        return
    state = space.fromcache(MonitoringState)
    if state.firing or not _event_is_set(state.any_events, event_id):
        return
    w_offset = space.newint(offset)
    for tool_id in range(NUM_TOOLS):
        if _event_is_set(state.global_events[tool_id], event_id):
            w_cb = state.get_callback(tool_id, event_id)
            if w_cb is not None:
                state.firing = True
                try:
                    w_result = space.call_function(w_cb, w_code, w_offset, w_extra)
                finally:
                    state.firing = False
                if space.is_w(w_result, w_disable(space)):
                    state.set_callback(tool_id, event_id, None)
                    raise oefmt(space.w_ValueError,
                        "Cannot disable %s events. Callback removed.",
                        EVENT_NAMES[event_id])


LOCAL_LINE_INSTRUCTION_MASK = (1 << LINE) | (1 << INSTRUCTION)


class VersionTag(object):
    """Identifies one "world state" of a PyCode's sys.monitoring
    bookkeeping. Replaced (never mutated) whenever that bookkeeping
    changes, so it's safe to promote and read inside @jit.elidable code."""


class CodeMonitoringState(object):
    _immutable_fields_ = ['version?']

    def __init__(self):
        self.version = VersionTag()
        self.local_events = None
        self.local_flags = 0
        self.disabled = None

    def changed(self):
        self.version = VersionTag()

    @jit.elidable
    def _get_local_flags(self, version_tag):
        assert version_tag is self.version
        return self.local_flags

    def get_local_flags(self):
        version_tag = jit.promote(self.version)
        return self._get_local_flags(version_tag)

    @jit.elidable
    def _tool_has_local_event(self, version_tag, tool_id, event_id):
        assert version_tag is self.version
        per_tool = self.local_events
        if per_tool is None:
            return 0
        return _event_is_set(per_tool[tool_id], event_id)

    def tool_has_local_event(self, tool_id, event_id):
        version_tag = jit.promote(self.version)
        return self._tool_has_local_event(version_tag, tool_id, event_id)

    @jit.elidable
    def _is_disabled(self, version_tag, tool_id, offset, event_id):
        assert version_tag is self.version
        per_event = self.disabled
        if per_event is None:
            return False
        disabled_tools = per_event[event_id]
        if disabled_tools is None:
            return False
        assert offset >= 0 and offset & 1 == 0
        tools = ord(disabled_tools[offset >> 1])
        return tools & (1 << tool_id)

    def is_disabled(self, tool_id, offset, event_id):
        version_tag = jit.promote(self.version)
        return self._is_disabled(version_tag, tool_id, offset, event_id)

    def disable(self, tool_id, offset, event_id, codeunit_count):
        assert offset >= 0 and offset & 1 == 0
        per_event = self.disabled
        if per_event is None:
            per_event = self.disabled = [None] * LOCAL_EVENTS
        disabled_tools = per_event[event_id]
        if disabled_tools is None:
            disabled_tools = per_event[event_id] = ['\x00'] * codeunit_count
        index = offset >> 1
        tools = ord(disabled_tools[index]) | (1 << tool_id)
        disabled_tools[index] = chr(tools)
        self.changed()


def is_disabled(pycode, tool_id, offset, event_id):
    monitoring = jit.promote(pycode.monitoring_state)
    if monitoring is None:
        return False
    return monitoring.is_disabled(tool_id, offset, event_id)


def should_fire_local_any(space, pycode, event_mask):
    """Does any tool want any event in event_mask for this code, globally
    or locally (local events add to global, never mask them)."""
    state = space.fromcache(MonitoringState)
    global_bits = jit.promote(state.any_events)
    monitoring = jit.promote(pycode.monitoring_state)
    if monitoring is None:
        local_bits = 0
    else:
        local_bits = monitoring.get_local_flags()
    return (global_bits | local_bits) & event_mask


def should_fire_local(space, pycode, event_id):
    """Single-event version of should_fire_local_any. Applies
    _control_event_id, so C_RETURN/C_RAISE correctly check CALL's bit."""
    state = space.fromcache(MonitoringState)
    global_bits = jit.promote(state.any_events)
    monitoring = jit.promote(pycode.monitoring_state)
    if monitoring is None:
        local_bits = 0
    else:
        local_bits = monitoring.get_local_flags()
    return _event_is_set(
        global_bits | local_bits, _control_event_id(event_id))


def dispatch_code_event(space, event_id, pycode, offset, *args_w):
    _dispatch_code_event(space, event_id, pycode, offset, offset, *args_w)


def dispatch_line_event(space, pycode, instruction_offset, line):
    _dispatch_code_event(
        space, LINE, pycode, line, instruction_offset)


@jit.unroll_safe
def _dispatch_code_event(space, event_id, pycode, callback_offset,
                         instruction_offset, *args_w):
    """Fire an event whose enabled state is local to a code object.

    The callback receives (code, offset, *args_w). C_RETURN/C_RAISE use
    CALL's enabled and disabled state, but select their own callback and
    cannot be disabled themselves.
    """
    if pycode.hidden_applevel:
        return
    state = space.fromcache(MonitoringState)
    if state.firing:
        return
    monitoring = jit.promote(pycode.monitoring_state)
    control_event_id = _control_event_id(event_id)
    any_global = _event_is_set(
        jit.promote(state.any_events), control_event_id)
    w_offset = space.newint(callback_offset)
    for tool_id in range(NUM_TOOLS):
        if monitoring is None:
            local_enabled = 0
        else:
            local_enabled = monitoring.tool_has_local_event(
                tool_id, control_event_id)
        if any_global:
            global_enabled = _event_is_set(
                state.global_events[tool_id], control_event_id)
        else:
            global_enabled = 0
        if not (local_enabled | global_enabled):
            continue
        if (monitoring is not None and
                monitoring.is_disabled(
                    tool_id, instruction_offset, control_event_id)):
            continue
        w_cb = state.get_callback(tool_id, event_id)
        if w_cb is None:
            continue
        state.firing = True
        try:
            w_result = space.call_function(w_cb, pycode, w_offset, *args_w)
        finally:
            state.firing = False
        if (_event_can_be_disabled(event_id) and
                space.is_w(w_result, w_disable(space))):
            pycode.monitoring_disable(
                tool_id, instruction_offset, event_id)
            state.disabled_codes[pycode] = True
