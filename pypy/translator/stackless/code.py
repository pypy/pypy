from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.rpython import rarithmetic

STATE_HEADER = lltype.GcStruct('state_header',
                               ('f_back',       lltype.Ptr(lltype.GcForwardReference())),
                               ('restartstate', lltype.Signed),
                               ('function',     llmemory.Address),
                               ('retval_type',  lltype.Signed))
STATE_HEADER.f_back.TO.become(STATE_HEADER)

null_state = lltype.nullptr(STATE_HEADER)

def decode_state(currentframe): 
    return (currentframe.function,
            currentframe.retval_type,
            currentframe.restartstate)

SWITCH_STATE = lltype.GcStruct('state_switch',
                               ('header', STATE_HEADER),
                               ('c', llmemory.Address))

def switch(c):
    if not global_state.restartstate:
        u = UnwindException()
        s = lltype.malloc(SWITCH_STATE)
        s.c = llmemory.cast_ptr_to_adr(c)
        s.header.restartstate = 1
        s.header.function = llmemory.cast_ptr_to_adr(switch)
        s.header.retval_type = RETVAL_VOID_P
        add_frame_state(u, s.header)
        raise u
    else:
        top = global_state.top
        s = lltype.cast_pointer(lltype.Ptr(SWITCH_STATE), top)
        global_state.top = s.c
        return top.f_back

def stack_frames_depth():
    if not global_state.restartstate:
        u = UnwindException()
        s = lltype.malloc(STATE_HEADER)
        s.restartstate = 1
        s.function = llmemory.cast_ptr_to_adr(count_stack_depth)
        s.retval_type = RETVAL_VOID
        add_frame_state(u, s.header)
        raise u
    else:
        cur = global_state.top
        global_state.restartstate = 0
        depth = 0
        while cur:
            depth += 1
            cur = cur.f_back
        return depth

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

class UnwindException(Exception):
    def __init__(self):
        # frame_top points to frame that first caught the
        # UnwindException, whilst frame_bottom points to the frame
        # that most recently caught the UnwindException.  frame_bottom
        # is only needed to efficiently tack frames on to the end of
        # the stack.  walking frame_top.f_back.f_back... goes to
        # frame_bottom
        self.frame_top = null_state
        self.frame_bottom = null_state

def slp_main_loop():
    """
    slp_main_loop() keeps resuming...
    """
    currentframe = global_state.top
    
    while currentframe:
        global_state.top = currentframe
        nextframe = currentframe.f_back
        fn, signature, global_state.restart_substate = decode_state(currentframe)
        try:
            call_function(fn, signature)
        except UnwindException, u:   #XXX annotation support needed
            nextframe = u.frame_top 
        except Exception, e:
            global_state.exception = e
        else:
            global_state.exception = None

        currentframe = nextframe

    if global_state.exception is not None:
        raise global_state.exception


def add_frame_state(u, frame_state):
    if not u.frame_top:
        u.frame_top = u.frame_bottom = frame_state
    else:
        u.frame_bottom.f_back = frame_state
        u.frame_bottom = frame_state

def resume_state():
    """Return and zero the 'restart_substate', the index of the resume
    point to jump to or zero for the not resuming case."""
    x = global_state.restart_substate
    global_state.restart_substate = 0
    return x 

# XXX would like to be able to say
#def resume_header():
#    x = global_state.restart_substate
#    if x:
#        top = global_state.top
#        global_state.top = None
# XXX and then insert the rtyped graph of this into functions
        
def fetch_retval_void():
    if global_state.exception:
        raise global_state.exception

def fetch_retval_long():
    if global_state.exception:
        raise global_state.exception
    else:
        return global_state.retval_long

def fetch_retval_longlong():
    if global_state.exception:
        raise global_state.exception
    else:
        return global_state.retval_longlong

def fetch_retval_float():
    if global_state.exception:
        raise global_state.exception
    else:
        return global_state.retval_float

def fetch_retval_void_p():
    if global_state.exception:
        raise global_state.exception
    else:
        return global_state.retval_void_p

