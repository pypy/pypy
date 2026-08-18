from rpython.rlib import jit
from pypy.interpreter.baseobjspace import W_Root
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
    _immutable_fields_ = ['any_events?']

    def __init__(self, space):
        self.tool_names = [None] * NUM_TOOLS
        self.callbacks = [None] * (NUM_TOOLS * NUM_EVENTS)
        self.global_events = [0] * NUM_TOOLS
        self.any_events = 0
        self.local_events = {}   # PyCode -> [event_set per tool]
        self.disabled_codes = {}   # PyCode -> True, for restart_events()
        self.firing = False      # reentrancy guard, like ExecutionContext.is_tracing

    def recompute_any_events(self):
        any_events = 0
        for tool_id in range(NUM_TOOLS):
            any_events |= self.global_events[tool_id]
        self.any_events = any_events


def _event_bit(event_id):
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


def should_fire(space, event_id):
    """JIT-foldable check: does any tool want this event globally?

    Callers must check this *before* calling fire2/fire3/fire4, not rely
    on the (non-promoted) check inside those functions -- promoting here
    lets the JIT constant-fold away the call and its argument setup
    entirely when nobody is listening, the same way gettrace() promotes
    ExecutionContext.w_tracefunc.
    """
    state = space.fromcache(MonitoringState)
    any_events = jit.promote(state.any_events)
    return (any_events >> _event_bit(event_id)) & 1


def should_fire_any(space, event_mask):
    """Like should_fire, but for a bitmask of several plain event ids at
    once (e.g. FRAME_ENTRY_EVENTS). Not used for C_RETURN/C_RAISE, whose
    bit-mapping is handled by should_fire/fire4 individually."""
    state = space.fromcache(MonitoringState)
    any_events = jit.promote(state.any_events)
    return any_events & event_mask


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


LOCAL_LINE_INSTRUCTION_MASK = (1 << LINE) | (1 << INSTRUCTION)


def should_fire_local_any(space, pycode, event_mask):
    """JIT-foldable check: does any tool want any event in event_mask for
    this code object, either globally or via set_local_events (local
    events add to global, never mask them -- see sys.monitoring.rst
    "Per code object events"). Used to gate dispatch_bytecode's per-
    bytecode LINE/INSTRUCTION check; folds to nothing when neither is
    active for this code, the same way should_fire folds the coarse
    events away when nobody's monitoring at all.
    """
    state = space.fromcache(MonitoringState)
    global_bits = jit.promote(state.any_events)
    local_bits = jit.promote(pycode.monitoring_local_flags)
    return (global_bits | local_bits) & event_mask


def should_fire_local(space, pycode, event_id):
    """Single-event version of should_fire_local_any."""
    state = space.fromcache(MonitoringState)
    global_bits = jit.promote(state.any_events)
    local_bits = jit.promote(pycode.monitoring_local_flags)
    return ((global_bits | local_bits) >> event_id) & 1


def fire_local(space, event_id, w_code, pycode, offset):
    """Fire a (code, offset) local event that supports DISABLE, e.g.
    LINE (offset is actually a line number, but the wire shape is the
    same: two positional args after the callback lookup) / INSTRUCTION.

    Unlike fire2/fire3/fire4, this is only reached once
    should_fire_local_any has already said *something* wants this event
    for this code, so it doesn't need its own promoted fast-reject path
    -- the per-tool loop below re-derives each tool's *combined*
    (global | local) bit because a tool can supply either independently.
    """
    state = space.fromcache(MonitoringState)
    if state.firing:
        return
    per_code_local = state.local_events.get(pycode, None)
    w_offset = space.newint(offset)
    for tool_id in range(NUM_TOOLS):
        tool_bits = state.global_events[tool_id]
        if per_code_local is not None:
            tool_bits |= per_code_local[tool_id]
        if not (tool_bits >> event_id) & 1:
            continue
        w_cb = state.callbacks[tool_id * NUM_EVENTS + event_id]
        if w_cb is None:
            continue
        if pycode.monitoring_is_disabled(tool_id, offset, event_id):
            continue
        state.firing = True
        try:
            w_result = space.call_function(w_cb, w_code, w_offset)
        finally:
            state.firing = False
        if space.is_w(w_result, w_disable(space)):
            pycode.monitoring_disable(tool_id, offset, event_id)
            state.disabled_codes[pycode] = True


def fire4(space, event_id, w_code, offset, w_callable, w_arg0):
    """Fire a (code, instruction_offset, callable, arg0) event, e.g.
    CALL/C_RETURN/C_RAISE.  See _event_bit for why C_RETURN/C_RAISE check
    the CALL bit for "is this enabled", while still looking up (and
    guarding on) each tool's own C_RETURN/C_RAISE callback slot."""
    state = space.fromcache(MonitoringState)
    check_id = _event_bit(event_id)
    if state.firing or not (state.any_events >> check_id) & 1:
        return
    w_offset = space.newint(offset)
    for tool_id in range(NUM_TOOLS):
        if (state.global_events[tool_id] >> check_id) & 1:
            w_cb = state.callbacks[tool_id * NUM_EVENTS + event_id]
            if w_cb is not None:
                state.firing = True
                try:
                    space.call_function(w_cb, w_code, w_offset, w_callable, w_arg0)
                finally:
                    state.firing = False
