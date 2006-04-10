from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.rpython import rarithmetic

STATE_HEADER = lltype.GcStruct('state_header',
                             ('f_back', lltype.Ptr(lltype.GcForwardReference())),
                             ('restartstate', lltype.Signed),
                             ('function', llmemory.Address),)
STATE_HEADER.f_back.TO.become(STATE_HEADER)

null_state = lltype.nullptr(STATE_HEADER)

def decode_state(currentframe): 
    return currentframe.function, "long", currentframe.restartstate

class StacklessData:
    def __init__(self):
        self.top = null_state
        self.bottom = null_state
        self.restart_substate = 0
        self.retval_long = 0
        self.retval_longlong = rarithmetic.r_longlong(0)
        self.retval_double = 0.0
        self.retval_void_p = llmemory.fakeaddress(None)
        self.exception = None

global_state = StacklessData()

def call_function(fn, signature):
    if signature == 'void':
        lloperation.llop.unsafe_call(lltype.Void, fn)
    elif signature == 'long':
        global_state.retval_long = lloperation.llop.unsafe_call(
            lltype.Signed, fn)
    elif signature == 'longlong':
        global_state.retval_longlong = lloperation.llop.unsafe_call(
            lltype.SignedLongLong, fn)
    elif signature == 'float':
        global_state.retval_double = lloperation.llop.unsafe_call(
            lltype.Float, fn)
    elif signature == 'pointer':
        global_state.retval_void_p = lloperation.llop.unsafe_call(
            llmemory.Address, fn)

null_address = llmemory.fakeaddress(None)

class UnwindException(Exception):
    def __init__(self):
        self.frame_top = null_state   # points to frame that first caught 
                                      # the UnwindException 
        self.frame_bottom = null_state 
        # walking frame_top.f_back.f_back... goes to frame_bottom 
        #

def slp_main_loop():
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
        
def fetch_retval_long():
    if global_state.exception:
        raise global_state.exception
    else:
        return global_state.retval_long
