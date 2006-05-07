from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.rpython import rarithmetic
from pypy.rpython import extfunctable


def ll_frame_switch(state):
    if global_state.restart_substate == 0:
        u = UnwindException()
        s = lltype.malloc(SWITCH_STATE)
        s.header.restartstate = 1
        # the next three lines are pure rtyper-pleasing hacks
        f = ll_frame_switch
        if global_state.restart_substate:
            f = None
        s.c = llmemory.cast_ptr_to_adr(state)
        s.header.function = llmemory.cast_ptr_to_adr(f)
        add_frame_state(u, s.header)
        raise u
    elif global_state.restart_substate == 1:
        global_state.restart_substate = 0
        top = global_state.top
        s = lltype.cast_pointer(lltype.Ptr(SWITCH_STATE), top)
        top.restartstate = 2
        state = llmemory.cast_adr_to_ptr(s.c, lltype.Ptr(STATE_HEADER))
        global_state.top = state
        global_state.retval_void_p = llmemory.cast_ptr_to_adr(top)
        raise UnwindException()
    else:
        top = global_state.top
        global_state.top = null_state
        global_state.restart_substate = 0
        origin_state = llmemory.cast_adr_to_ptr(fetch_retval_void_p(),
                                                OPAQUE_STATE_HEADER_PTR)
        return origin_state
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
                               ('c', llmemory.Address))

def yield_current_frame_to_caller():
    if global_state.restart_substate == 0:
        u = UnwindException()
        s = lltype.malloc(STATE_HEADER)
        s.restartstate = 1
        # the next three lines are pure rtyper-pleasing hacks
        f = yield_current_frame_to_caller
        if global_state.restart_substate:
            f = None
        s.function = llmemory.cast_ptr_to_adr(f)
        s.retval_type = RETVAL_VOID_P
        add_frame_state(u, s)
        raise u
    elif global_state.restart_substate == 1:
        global_state.restart_substate = 0
        ycftc_state = global_state.top
        ycftc_state.restartstate = 2
        our_caller_state = ycftc_state.f_back
        caller_state = our_caller_state.f_back
        # the next three lines are pure rtyper-pleasing hacks
        f = yield_current_frame_to_caller
        if global_state.restart_substate:
            f = None
        endstate = lltype.malloc(STATE_HEADER)
        endstate.restartstate = 3
        endstate.function = llmemory.cast_ptr_to_adr(f)
        our_caller_state.f_back = endstate
        global_state.top = caller_state
        global_state.retval_void_p = llmemory.cast_ptr_to_adr(ycftc_state)
        raise UnwindException()
    elif global_state.restart_substate == 2:
        top = global_state.top
        global_state.top = null_state
        global_state.restart_substate = 0
        origin_state = llmemory.cast_adr_to_ptr(fetch_retval_void_p(),
                                                OPAQUE_STATE_HEADER_PTR)
        return origin_state
    else:
        global_state.restart_substate = 0
        next_state = llmemory.cast_adr_to_ptr(fetch_retval_void_p(),
                                              lltype.Ptr(STATE_HEADER))
        global_state.top = next_state
        raise UnwindException()

yield_current_frame_to_caller.stackless_explicit = True

def stack_frames_depth():
    if not global_state.restart_substate:
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
        raise u
    else:
        cur = global_state.top
        global_state.restart_substate = 0
        depth = 0
        while cur:
            depth += 1
            cur = cur.f_back
        return depth
stack_frames_depth.stackless_explicit = True

class StacklessData:
    def __init__(self):
        self.top = null_state
        self.restart_substate = 0
        self.retval_long = 0
        self.retval_longlong = rarithmetic.r_longlong(0)
        self.retval_float = 0.0
        self.retval_void_p = llmemory.NULL
        self.exception = None

global_state = StacklessData()

RETVAL_VOID, RETVAL_LONG, RETVAL_LONGLONG, RETVAL_FLOAT, RETVAL_VOID_P = \
             range(5)

def call_function(fn, retval_code):
    if retval_code == RETVAL_VOID:
        lloperation.llop.unsafe_call(lltype.Void, fn)
    elif retval_code == RETVAL_LONG:
        global_state.retval_long = lloperation.llop.unsafe_call(
            lltype.Signed, fn)
    elif retval_code == RETVAL_LONGLONG:
        global_state.retval_longlong = lloperation.llop.unsafe_call(
            lltype.SignedLongLong, fn)
    elif retval_code == RETVAL_FLOAT:
        global_state.retval_float = lloperation.llop.unsafe_call(
            lltype.Float, fn)
    elif retval_code == RETVAL_VOID_P:
        global_state.retval_void_p = lloperation.llop.unsafe_call(
            llmemory.Address, fn)
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

def fetch_retval_void_p():
    e = global_state.exception
    if e:
        global_state.exception = None
        raise e
    else:
        return global_state.retval_void_p
fetch_retval_void_p.stackless_explicit = True
