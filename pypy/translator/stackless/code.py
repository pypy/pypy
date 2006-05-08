from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.rpython import rarithmetic
from pypy.rpython import extfunctable

SAVED_REFERENCE = lltype.Ptr(lltype.GcOpaqueType('stackless.saved_ref'))
null_saved_ref = lltype.nullptr(SAVED_REFERENCE.TO)

STORAGE_TYPES = [lltype.Void, SAVED_REFERENCE, llmemory.Address,
                 lltype.Signed, lltype.Float, lltype.SignedLongLong]

STORAGE_FIELDS = {SAVED_REFERENCE: 'ref',
                  llmemory.Address: 'addr',
                  lltype.Signed: 'long',
                  lltype.Float: 'float',
                  lltype.SignedLongLong: 'longlong',
                  }

RETVAL_VOID = 0
for _key, _value in STORAGE_FIELDS.items():
    globals()['RETVAL_' + _value.upper()] = STORAGE_TYPES.index(_key)

# ____________________________________________________________

def ll_frame_switch(targetstate):
    if global_state.restart_substate == 0:
        # normal entry point for a call to state.switch()
        # first unwind the stack
        u = UnwindException()
        s = lltype.malloc(SWITCH_STATE)
        s.header.restartstate = 1
        # the next three lines are pure rtyper-pleasing hacks
        f = ll_frame_switch
        if global_state.restart_substate:
            f = None
        s.c = lltype.cast_opaque_ptr(SAVED_REFERENCE, targetstate)
        s.header.function = llmemory.cast_ptr_to_adr(f)
        s.header.retval_type = RETVAL_REF
        add_frame_state(u, s.header)
        raise u
    elif global_state.restart_substate == 1:
        # STATE 1: we didn't do anything so far, but the stack is unwound
        global_state.restart_substate = 0
        # grab the frame corresponding to ourself, and prepare it for
        # the future switch() back, which will go to STATE 2 below
        sourcestate = global_state.top
        sourcestate.restartstate = 2
        # the 'targetstate' local is garbage here, it must be read back from
        # 's.c' where we saved it by STATE 0 above
        s = lltype.cast_pointer(lltype.Ptr(SWITCH_STATE), sourcestate)
        targetstate = lltype.cast_opaque_ptr(lltype.Ptr(STATE_HEADER), s.c)
        global_state.top = targetstate
        global_state.retval_ref = lltype.cast_opaque_ptr(SAVED_REFERENCE,
                                                         sourcestate)
        raise UnwindException()   # this jumps to targetstate
    else:
        # STATE 2: switching back into a tasklet suspended by
        # a call to switch()
        global_state.top = null_state
        global_state.restart_substate = 0
        origin_state = lltype.cast_opaque_ptr(OPAQUE_STATE_HEADER_PTR,
                                              fetch_retval_ref())
        return origin_state    # a normal return into the current tasklet,
                               # with the source state as return value
ll_frame_switch.stackless_explicit = True

STATE_HEADER = lltype.GcStruct('state_header',
                               ('f_back',       lltype.Ptr(lltype.GcForwardReference())),
                               ('restartstate', lltype.Signed),
                               ('function',     llmemory.Address),
                               ('retval_type',  lltype.Signed),
                               adtmeths={'switch': ll_frame_switch})
STATE_HEADER.f_back.TO.become(STATE_HEADER)

null_state = lltype.nullptr(STATE_HEADER)

OPAQUE_STATE_HEADER_PTR = lltype.Ptr(
    extfunctable.frametop_type_info.get_lltype())

##def decode_state(currentframe): 
##    return (currentframe.function,
##            currentframe.retval_type,
##            currentframe.restartstate)
##decode_state.stackless_explicit = True

SWITCH_STATE = lltype.GcStruct('state_switch',
                               ('header', STATE_HEADER),
                               ('c', SAVED_REFERENCE))

def yield_current_frame_to_caller():
    if global_state.restart_substate == 0:
        # normal entry point for yield_current_frame_to_caller()
        # first unwind the stack
        u = UnwindException()
        s = lltype.malloc(STATE_HEADER)
        s.restartstate = 1
        # the next three lines are pure rtyper-pleasing hacks
        f = yield_current_frame_to_caller
        if global_state.restart_substate:
            f = None
        s.function = llmemory.cast_ptr_to_adr(f)
        s.retval_type = RETVAL_REF
        add_frame_state(u, s)
        raise u   # this goes to 'STATE 1' below

    elif global_state.restart_substate == 1:
        # STATE 1: we didn't do anything so far, but the stack is unwound
        global_state.restart_substate = 0
        ycftc_state = global_state.top
        our_caller_state = ycftc_state.f_back
        caller_state = our_caller_state.f_back
        # the next three lines are pure rtyper-pleasing hacks
        f = yield_current_frame_to_caller
        if global_state.restart_substate:
            f = None
        # when our immediate caller finishes (which is later, when the
        # tasklet finishes), then we will jump to 'STATE 2' below
        endstate = lltype.malloc(STATE_HEADER)
        endstate.restartstate = 2
        endstate.function = llmemory.cast_ptr_to_adr(f)
        our_caller_state.f_back = endstate
        global_state.top = caller_state
        global_state.retval_ref = lltype.cast_opaque_ptr(SAVED_REFERENCE,
                                                         our_caller_state)
        raise UnwindException()  # this goes to the caller's caller

    else:
        # STATE 2: this is a slight abuse of yield_current_frame_to_caller(),
        # as we return here when our immediate caller returns (and thus the
        # new tasklet finishes).
        global_state.restart_substate = 0
        next_state = lltype.cast_opaque_ptr(lltype.Ptr(STATE_HEADER),
                                            fetch_retval_ref())
        # return a NULL state pointer to the target of the implicit switch
        global_state.top = next_state
        global_state.retval_ref = null_saved_ref
        raise UnwindException()  # this goes to the switch target given by
                                 # the 'return' at the end of our caller

yield_current_frame_to_caller.stackless_explicit = True

def stack_frames_depth():
    if not global_state.restart_substate:
        # normal entry point for stack_frames_depth()
        # first unwind the stack
        u = UnwindException()
        s = lltype.malloc(STATE_HEADER)
        s.restartstate = 1
        # the next three lines are pure rtyper-pleasing hacks
        f = stack_frames_depth
        if global_state.restart_substate:
            f = None
        s.function = llmemory.cast_ptr_to_adr(f)
        s.retval_type = RETVAL_LONG
        add_frame_state(u, s)
        raise u    # goes to STATE 1 below
    else:
        # STATE 1: now the stack is unwound, and we can count the frames
        # in the heap
        cur = global_state.top
        global_state.restart_substate = 0
        depth = 0
        while cur:
            depth += 1
            cur = cur.f_back
        return depth
stack_frames_depth.stackless_explicit = True

def ll_stack_unwind():
    if not global_state.restart_substate:
        # normal entry point for stack_frames_depth()
        # first unwind the stack in the usual way
        u = UnwindException()
        s = lltype.malloc(STATE_HEADER)
        s.restartstate = 1
        # the next three lines are pure rtyper-pleasing hacks
        f = ll_stack_unwind
        if global_state.restart_substate:
            f = None
        s.function = llmemory.cast_ptr_to_adr(f)
        s.retval_type = RETVAL_VOID
        add_frame_state(u, s)
        raise u    # goes to STATE 1 below
    else:
        # STATE 1: now the stack is unwound.  That was the goal.
        # Return to caller.
        global_state.restart_substate = 0
ll_stack_unwind.stackless_explicit = True

class StacklessData:
    def __init__(self):
        self.top = null_state
        self.restart_substate = 0
        self.retval_long = 0
        self.retval_longlong = rarithmetic.r_longlong(0)
        self.retval_float = 0.0
        self.retval_addr = llmemory.NULL
        self.retval_ref = null_saved_ref
        self.exception = None

global_state = StacklessData()

def call_function(fn, retval_code):
    if retval_code == RETVAL_VOID:
        lloperation.llop.unsafe_call(lltype.Void, fn)
    elif retval_code == RETVAL_REF:
        global_state.retval_ref = lloperation.llop.unsafe_call(
            SAVED_REFERENCE, fn)
    elif retval_code == RETVAL_ADDR:
        global_state.retval_addr = lloperation.llop.unsafe_call(
            llmemory.Address, fn)
    elif retval_code == RETVAL_LONG:
        global_state.retval_long = lloperation.llop.unsafe_call(
            lltype.Signed, fn)
    elif retval_code == RETVAL_FLOAT:
        global_state.retval_float = lloperation.llop.unsafe_call(
            lltype.Float, fn)
    elif retval_code == RETVAL_LONGLONG:
        global_state.retval_longlong = lloperation.llop.unsafe_call(
            lltype.SignedLongLong, fn)
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
        self.frame_bottom = null_state

def slp_main_loop():
    """
    slp_main_loop() keeps resuming...
    """
    pending = global_state.top
    
    while True:
        back                          = pending.f_back
        fn                            = pending.function
        signature                     = pending.retval_type
        global_state.restart_substate = pending.restartstate
        try:
            call_function(fn, signature)
        except UnwindException, u:   #XXX annotation support needed
            if u.frame_bottom:
                u.frame_bottom.f_back = back
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

slp_main_loop.stackless_explicit = True

def add_frame_state(u, frame_state):
    if not u.frame_bottom:
        global_state.top = u.frame_bottom = frame_state
    else:
        u.frame_bottom.f_back = frame_state
        u.frame_bottom = frame_state
add_frame_state.stackless_explicit = True

def resume_state():
    """Return and zero the 'restart_substate', the index of the resume
    point to jump to or zero for the not resuming case."""
    x = global_state.restart_substate
    global_state.restart_substate = 0
    return x 
resume_state.stackless_explicit = True

# XXX would like to be able to say
#def resume_header():
#    x = global_state.restart_substate
#    if x:
#        top = global_state.top
#        global_state.top = None
# XXX and then insert the rtyped graph of this into functions
        
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
        global_state.retval_ref = null_saved_ref
        return res
fetch_retval_ref.stackless_explicit = True
