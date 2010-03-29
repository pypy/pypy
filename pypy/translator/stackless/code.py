import sys
from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib import rarithmetic, objectmodel, rstackovf
from pypy.translator.stackless import frame
from pypy.translator.stackless.frame import STATE_HEADER, SAVED_REFERENCE, STORAGE_TYPES_AND_FIELDS

EMPTY_STATE = frame.make_state_header_type('empty_state')

def check_can_raise_unwind():
    if objectmodel.is_in_callback():
        raise RuntimeError

# ____________________________________________________________

SWITCH_STATE = frame.make_state_header_type('switch_state',
                                            ('c', SAVED_REFERENCE))

def ll_frame_switch(targetstate):
    if global_state.restart_substate == -1:
        # normal entry point for a call to state.switch()
        # first unwind the stack
        u = UnwindException()
        s = lltype.malloc(SWITCH_STATE)
        s.header.f_restart = INDEX_SWITCH
        s.c = lltype.cast_opaque_ptr(SAVED_REFERENCE, targetstate)
        add_frame_state(u, s.header)
        raise u
    elif global_state.restart_substate == 0:
        # STATE 0: we didn't do anything so far, but the stack is unwound
        global_state.restart_substate = -1
        # grab the frame corresponding to ourself
        # the 'targetstate' local is garbage here, it must be read back from
        # 's.c' where we saved it by the normal entry point above
        mystate = global_state.top
        s = lltype.cast_pointer(lltype.Ptr(SWITCH_STATE), mystate)
        targetstate = lltype.cast_opaque_ptr(lltype.Ptr(STATE_HEADER), s.c)
        # prepare a new saved state for the future switch() back,
        # which will go to STATE 1 below
        sourcestate = lltype.malloc(EMPTY_STATE).header
        sourcestate.f_back = mystate.f_back
        sourcestate.f_restart = INDEX_SWITCH + 1
        sourcestate.f_depth = mystate.f_depth
        global_state.top = targetstate
        global_state.retval_ref = lltype.cast_opaque_ptr(SAVED_REFERENCE,
                                                         sourcestate)
        raise SwitchException()   # this jumps to targetstate
    else:
        # STATE 1: switching back into a tasklet suspended by
        # a call to switch()
        global_state.top = frame.null_state
        global_state.restart_substate = -1
        origin_state = lltype.cast_opaque_ptr(frame.OPAQUE_STATE_HEADER_PTR,
                                              fetch_retval_ref())
        return origin_state    # a normal return into the current tasklet,
                               # with the source state as return value
ll_frame_switch.stackless_explicit = True

INDEX_SWITCH = frame.RestartInfo.add_prebuilt(ll_frame_switch,
                                              [SWITCH_STATE, EMPTY_STATE])

# ____________________________________________________________

def yield_current_frame_to_caller():
    if global_state.restart_substate == -1:
        # normal entry point for yield_current_frame_to_caller()
        # first unwind the stack
        u = UnwindException()
        s = lltype.malloc(EMPTY_STATE).header
        s.f_restart = INDEX_YCFTC
        add_frame_state(u, s)
        raise u   # this goes to 'STATE 0' below

    elif global_state.restart_substate == 0:
        # STATE 0: we didn't do anything so far, but the stack is unwound
        global_state.restart_substate = -1
        ycftc_state = global_state.top
        our_caller_state = ycftc_state.f_back
        caller_state = our_caller_state.f_back
        caller_state.f_depth = ycftc_state.f_depth - 2
        # when our immediate caller finishes (which is later, when the
        # tasklet finishes), then we will jump to 'STATE 1' below
        endstate = lltype.malloc(EMPTY_STATE).header
        endstate.f_restart = INDEX_YCFTC + 1
        our_caller_state.f_back = endstate
        our_caller_state.f_depth = 1
        global_state.top = caller_state
        global_state.retval_ref = lltype.cast_opaque_ptr(SAVED_REFERENCE,
                                                         our_caller_state)
        raise SwitchException()  # this goes to the caller's caller

    elif global_state.restart_substate == 1:
        # STATE 1: this is a slight abuse of yield_current_frame_to_caller(),
        # as we return here when our immediate caller returns (and thus the
        # new tasklet finishes).
        global_state.restart_substate = -1
        next_state = lltype.cast_opaque_ptr(lltype.Ptr(STATE_HEADER),
                                            fetch_retval_ref())
        # return a NULL state pointer to the target of the implicit switch
        global_state.top = next_state
        global_state.retval_ref = frame.null_saved_ref
        raise SwitchException()  # this goes to the switch target given by
                                 # the 'return' at the end of our caller

    else:
        # this is never reached!  But the annotator doesn't know it,
        # so it makes the whole function be annotated as returning a random
        # non-constant STATE_HEADER pointer.
        return lltype.cast_opaque_ptr(frame.OPAQUE_STATE_HEADER_PTR,
                                      global_state.top)

yield_current_frame_to_caller.stackless_explicit = True

INDEX_YCFTC = frame.RestartInfo.add_prebuilt(yield_current_frame_to_caller,
                                             [EMPTY_STATE, EMPTY_STATE])

# ____________________________________________________________

def stack_frames_depth():
    if global_state.restart_substate == -1:
        # normal entry point for stack_frames_depth()
        # first unwind the stack
        u = UnwindException()
        s = lltype.malloc(EMPTY_STATE).header
        s.f_restart = INDEX_DEPTH
        add_frame_state(u, s)
        raise u    # goes to STATE 0 below
    else:
        # STATE 0: now the stack is unwound, and we can count the frames
        # in the heap
        cur = global_state.top
        global_state.top = frame.null_state
        global_state.restart_substate = -1
        return cur.f_depth
stack_frames_depth.stackless_explicit = True

INDEX_DEPTH = frame.RestartInfo.add_prebuilt(stack_frames_depth,
                                             [EMPTY_STATE])

# ____________________________________________________________

def ll_stack_unwind():
    if global_state.restart_substate == -1:
        # normal entry point for stack_frames_depth()
        # first unwind the stack in the usual way
        u = UnwindException()
        s = lltype.malloc(EMPTY_STATE).header
        s.f_restart = INDEX_UNWIND
        add_frame_state(u, s)
        raise u    # goes to STATE 0 below
    else:
        # STATE 0: now the stack is unwound.  That was the goal.
        # Return to caller.
        global_state.top = frame.null_state
        global_state.restart_substate = -1
        
ll_stack_unwind.stackless_explicit = True

INDEX_UNWIND = frame.RestartInfo.add_prebuilt(ll_stack_unwind,
                                               [EMPTY_STATE])

# ____________________________________________________________

def ll_stack_capture():
    if global_state.restart_substate == -1:
        # normal entry point for ll_stack_capture()
        # first unwind the stack in the usual way
        u = UnwindException()
        s = lltype.malloc(EMPTY_STATE).header
        s.f_restart = INDEX_CAPTURE
        add_frame_state(u, s)
        raise u    # goes to STATE 0 below
    else:
        # STATE 0: now the stack is unwound.  That was the goal.
        # Return to caller.
        cur = global_state.top
        global_state.top = frame.null_state
        global_state.restart_substate = -1
        # Pass the caller's own saved state back to it.
        # The StacklessFrameworkGCTransformer uses this for introspection.
        return lltype.cast_opaque_ptr(frame.OPAQUE_STATE_HEADER_PTR,
                                      cur.f_back)
ll_stack_capture.stackless_explicit = True

INDEX_CAPTURE = frame.RestartInfo.add_prebuilt(ll_stack_capture,
                                               [EMPTY_STATE])

def resume_after_void(state, retvalue):
    if global_state.restart_substate == -1:
        # normal entry point for a call to state.switch()
        # first unwind the stack
        u = UnwindException()
        s = lltype.malloc(SWITCH_STATE)
        s.header.f_restart = INDEX_RESUME_AFTER_VOID
        s.c = lltype.cast_opaque_ptr(SAVED_REFERENCE, state)
        add_frame_state(u, s.header)
        raise u
    elif global_state.restart_substate == 0:
        # STATE 0: we didn't do anything so far, but the stack is unwound
        global_state.restart_substate = -1
        # grab the frame corresponding to ourself
        # the 'targetstate' local is garbage here, it must be read back from
        # 's.c' where we saved it by the normal entry point above
        mystate = global_state.top
        s = lltype.cast_pointer(lltype.Ptr(SWITCH_STATE), mystate)
        targetstate = lltype.cast_opaque_ptr(lltype.Ptr(STATE_HEADER), s.c)
        resume_bottom = targetstate
        while resume_bottom.f_back:
             resume_bottom = resume_bottom.f_back
        resume_bottom.f_back = mystate.f_back
        global_state.top = targetstate
        raise SwitchException()

resume_after_void.stackless_explicit = True
INDEX_RESUME_AFTER_VOID = frame.RestartInfo.add_prebuilt(resume_after_void,
                                                         [SWITCH_STATE,
                                                          EMPTY_STATE])


def resume_after_raising(state, exception):
    if global_state.restart_substate == -1:
        # normal entry point for a call to state.switch()
        # first unwind the stack
        u = UnwindException()
        s = lltype.malloc(SWITCH_STATE)
        s.header.f_restart = INDEX_RESUME_AFTER_RAISING
        s.c = lltype.cast_opaque_ptr(SAVED_REFERENCE, state)
        add_frame_state(u, s.header)
        global_state.exception = exception
        raise u
    elif global_state.restart_substate == 0:
        # STATE 0: we didn't do anything so far, but the stack is unwound
        global_state.restart_substate = -1
        # grab the frame corresponding to ourself
        # the 'targetstate' local is garbage here, it must be read back from
        # 's.c' where we saved it by the normal entry point above
        mystate = global_state.top
        s = lltype.cast_pointer(lltype.Ptr(SWITCH_STATE), mystate)
        targetstate = lltype.cast_opaque_ptr(lltype.Ptr(STATE_HEADER), s.c)
        resume_bottom = targetstate
        while resume_bottom.f_back:
             resume_bottom = resume_bottom.f_back
        resume_bottom.f_back = mystate.f_back
        global_state.top = targetstate
        raise SwitchException()

resume_after_raising.stackless_explicit = True
INDEX_RESUME_AFTER_RAISING = frame.RestartInfo.add_prebuilt(resume_after_raising,
                                                            [SWITCH_STATE,
                                                             EMPTY_STATE])

template = """\
def resume_after_%(typename)s(state, retvalue):
    if global_state.restart_substate == -1:
        # normal entry point for a call to state.switch()
        # first unwind the stack
        u = UnwindException()
        s = lltype.malloc(SWITCH_STATE)
        s.header.f_restart = INDEX_RESUME_AFTER_%(TYPENAME)s
        s.c = lltype.cast_opaque_ptr(SAVED_REFERENCE, state)
        global_state.retval_%(typename)s = retvalue
        add_frame_state(u, s.header)
        raise u
    elif global_state.restart_substate == 0:
        # STATE 0: we didn't do anything so far, but the stack is unwound
        global_state.restart_substate = -1
        # grab the frame corresponding to ourself
        # the 'targetstate' local is garbage here, it must be read back from
        # 's.c' where we saved it by the normal entry point above
        mystate = global_state.top
        s = lltype.cast_pointer(lltype.Ptr(SWITCH_STATE), mystate)
        targetstate = lltype.cast_opaque_ptr(lltype.Ptr(STATE_HEADER), s.c)
        resume_bottom = targetstate
        while resume_bottom.f_back:
             resume_bottom = resume_bottom.f_back
        resume_bottom.f_back = mystate.f_back
        global_state.top = targetstate
        raise SwitchException()


resume_after_%(typename)s.stackless_explicit = True
INDEX_RESUME_AFTER_%(TYPENAME)s = frame.RestartInfo.add_prebuilt(resume_after_%(typename)s,
                                                         [SWITCH_STATE,
                                                          EMPTY_STATE])
"""

for _lltype, typename in STORAGE_TYPES_AND_FIELDS:
    if typename == 'void': continue
    exec template%dict(typename=typename, TYPENAME=typename.upper())

# ____________________________________________________________

def ll_get_stack_depth_limit():
    return global_state.stack_depth_limit

def ll_set_stack_depth_limit(limit):
    global_state.stack_depth_limit = limit

# ____________________________________________________________

class StacklessData:
    def __init__(self):
        self.top = frame.null_state
        self.restart_substate = -1
        self.retval_long = 0
        self.retval_longlong = rarithmetic.r_longlong(0)
        self.retval_float = 0.0
        self.retval_addr = llmemory.NULL
        self.retval_ref = frame.null_saved_ref
        self.exception = None
        self.masterarray = lltype.malloc(frame.FRAME_INFO_ARRAY, 0,
                                         immortal=True)
        self.stack_depth_limit = 100000    # default limit

global_state = StacklessData()

# the following functions are patched by transform.py in finish()
# so that they don't really do what they appear to - we discovered
# that it was not safe at all to produce this kind of C code
def define_call_function_retval(TYPE, typename):
    FUNCTYPE = lltype.Ptr(lltype.FuncType([], TYPE))
    def call_function_retval_xyz(fnaddr, signature_index):
        fn = llmemory.cast_adr_to_ptr(fnaddr, FUNCTYPE)
        return fn()
    call_function_retval_xyz.stackless_explicit = True
    call_function_retval_xyz._dont_inline_ = True
    fnname = 'call_function_retval_' + typename
    fn = func_with_new_name(call_function_retval_xyz, fnname)
    globals()[fnname] = fn
for _lltype, _typename in STORAGE_TYPES_AND_FIELDS:
    define_call_function_retval(_lltype, _typename)


def call_function(fn, signature_index):
    retval_code = signature_index & frame.storage_type_bitmask
    if retval_code == frame.RETVAL_VOID:
        call_function_retval_void(fn, signature_index)
    elif retval_code == frame.RETVAL_REF:
        global_state.retval_ref = (
            call_function_retval_ref(fn, signature_index))
    elif retval_code == frame.RETVAL_ADDR:
        global_state.retval_addr = (
            call_function_retval_addr(fn, signature_index))
    elif retval_code == frame.RETVAL_LONG:
        global_state.retval_long = (
            call_function_retval_long(fn, signature_index))
    elif retval_code == frame.RETVAL_FLOAT:
        global_state.retval_float = (
            call_function_retval_float(fn, signature_index))
    elif retval_code == frame.RETVAL_LONGLONG:
        global_state.retval_longlong = (
            call_function_retval_longlong(fn, signature_index))
    else:
        assert False
call_function.stackless_explicit = True

class UnwindException(lloperation.StackException):
    def __init__(self):
        # during unwind, global_state.top points to frame that first caught
        # the UnwindException, whilst frame_bottom points to the frame
        # that most recently caught the UnwindException.  In a normal
        # situation, frame_bottom is global_state.top.f_back.f_back.etc...
        # To switch manually to a different frame, code issues a regular
        # UnwindException first, to empty the C stack, and then issues a
        # (XXX complete this comment)
        check_can_raise_unwind()
        self.frame_bottom = frame.null_state
        self.depth = 0
    __init__.stackless_explicit = True

class SwitchException(lloperation.StackException):
    pass

def slp_main_loop(depth):
    """
    slp_main_loop() keeps resuming...
    """
    while True:
        pending = global_state.top
        pending.f_depth = depth        # this starts after the first Unwind
        if pending.f_depth > global_state.stack_depth_limit:
            # uncommon case: exceed the limit
            pending = pending.f_back
            pending.f_depth = depth - 1
            e = rstackovf._StackOverflow()
            if not pending:
                raise e
            global_state.exception = e
            global_state.top = pending

        while True:
            prevdepth = pending.f_depth - 1
            back = pending.f_back
            decoded = frame.decodestate(pending.f_restart)
            (fn, global_state.restart_substate, signature_index) = decoded
            try:
                call_function(fn, signature_index)
            except UnwindException, u:   #XXX annotation support needed
                u.frame_bottom.f_back = back
                depth = prevdepth + u.depth
                break
            except SwitchException:
                pending = global_state.top
                continue
            except Exception, e:
                if not back:
                    raise
                global_state.exception = e
            else:
                if not back:
                    return
            global_state.top = pending = back
            pending.f_depth = prevdepth

slp_main_loop.stackless_explicit = True

def add_frame_state(u, frame_state):
    if not u.frame_bottom:
        global_state.top = u.frame_bottom = frame_state
    else:
        u.frame_bottom.f_back = frame_state
        u.frame_bottom = frame_state
    u.depth += 1
add_frame_state.stackless_explicit = True

def fetch_retval_void():
    e = global_state.exception
    if e:
        global_state.exception = None
        raise e
fetch_retval_void.stackless_explicit = True

def fetch_retval_long():
    e = global_state.exception
    if e:
        global_state.exception = None
        raise e
    else:
        return global_state.retval_long
fetch_retval_long.stackless_explicit = True

def fetch_retval_longlong():
    e = global_state.exception
    if e:
        global_state.exception = None
        raise e
    else:
        return global_state.retval_longlong
fetch_retval_longlong.stackless_explicit = True

def fetch_retval_float():
    e = global_state.exception
    if e:
        global_state.exception = None
        raise e
    else:
        return global_state.retval_float
fetch_retval_float.stackless_explicit = True

def fetch_retval_addr():
    e = global_state.exception
    if e:
        global_state.exception = None
        raise e
    else:
        res = global_state.retval_addr
        global_state.retval_addr = llmemory.NULL
        return res
fetch_retval_addr.stackless_explicit = True

def fetch_retval_ref():
    e = global_state.exception
    if e:
        global_state.exception = None
        raise e
    else:
        res = global_state.retval_ref
        global_state.retval_ref = frame.null_saved_ref
        return res
fetch_retval_ref.stackless_explicit = True
