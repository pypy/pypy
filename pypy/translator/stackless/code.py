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
decode_state.stackless_explicit = True

SWITCH_STATE = lltype.GcStruct('state_switch',
                               ('header', STATE_HEADER),
                               ('c', llmemory.Address))

class Frame(object):
    def __init__(self, state):
        self.state = state
    __init__.stackless_explicit = True
    def switch(self):
        if global_state.restart_substate == 0:
            u = UnwindException()
            s = lltype.malloc(SWITCH_STATE)
            s.header.restartstate = 1
            # the next three lines are pure rtyper-pleasing hacks
            f = Frame.switch
            if global_state.restart_substate:
                f = None
            s.c = llmemory.cast_ptr_to_adr(self.state)
            s.header.function = llmemory.cast_ptr_to_adr(f)
            add_frame_state(u, s.header)
            raise u
        elif global_state.restart_substate == 1:
            top = global_state.top
            state = lltype.cast_pointer(lltype.Ptr(SWITCH_STATE), top)
            u = UnwindException()
            s.header.restartstate = 2
            c = lltype.cast_adr_to_ptr(lltype.Ptr(STATE_HEADER), top)
            s.header.function = c.function
            s.reader.retval_type = RETVAL_VOID_P
            # the next three lines are pure rtyper-pleasing hacks
            f = Frame.switch
            if global_state.restart_substate:
                f = None
            add_frame_state(u, s.header)
            raise u            
        else:
            top = global_state.top
            global_state.restart_substate = 0
            r = top.f_back
            state = lltype.cast_pointer(lltype.Ptr(SWITCH_STATE), top)
            global_state.top = lltype.cast_adr_to_ptr(lltype.Ptr(STATE_HEADER), state.c)
            #global_state.restart_substate = state.header.restartstate
            return r
    switch.stackless_explicit = True

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
        ycftc_state = global_state.top
        our_caller_state = ycftc_state.f_back
        caller_state = our_caller_state.f_back
        cur = caller_state
        while cur.f_back:
            cur = cur.f_back
        bot = cur
        u = UnwindException()
        u.frame_top = caller_state
        u.frame_bottom = bot
        global_state.retval_void_p = llmemory.cast_ptr_to_adr(Frame(ycftc_state))
        global_state.restart_substate = 2
        raise u
    else:
        pass
        
        
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
            u.frame_bottom.f_back = nextframe
            nextframe = u.frame_top
        except Exception, e:
            global_state.exception = e
        else:
            global_state.exception = None

        currentframe = nextframe

    if global_state.exception is not None:
        raise global_state.exception
slp_main_loop.stackless_explicit = True

def add_frame_state(u, frame_state):
    if not u.frame_top:
        u.frame_top = u.frame_bottom = frame_state
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
    if global_state.exception:
        raise global_state.exception
fetch_retval_void.stackless_explicit = True

def fetch_retval_long():
    if global_state.exception:
        raise global_state.exception
    else:
        return global_state.retval_long
fetch_retval_long.stackless_explicit = True

def fetch_retval_longlong():
    if global_state.exception:
        raise global_state.exception
    else:
        return global_state.retval_longlong
fetch_retval_longlong.stackless_explicit = True

def fetch_retval_float():
    if global_state.exception:
        raise global_state.exception
    else:
        return global_state.retval_float
fetch_retval_float.stackless_explicit = True

def fetch_retval_void_p():
    if global_state.exception:
        raise global_state.exception
    else:
        return global_state.retval_void_p
fetch_retval_void_p.stackless_explicit = True
