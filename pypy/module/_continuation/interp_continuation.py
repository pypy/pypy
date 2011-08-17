import sys
from pypy.rpython.lltypesystem import lltype
from pypy.rlib import jit
from pypy.rlib.rstacklet import StackletThread, get_null_handle
from pypy.rlib.objectmodel import we_are_translated
from pypy.interpreter.error import OperationError
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.pycode import PyCode
from pypy.rlib.debug import ll_assert, fatalerror


class W_Continuation(Wrappable):

    def __init__(self, space):
        self.space = space
        self.sthread = None
        self.h = get_null_handle(space.config)

    def build_sthread(self):
        space = self.space
        ec = space.getexecutioncontext()
        sthread = ec.stacklet_thread
        if not sthread:
            sthread = ec.stacklet_thread = SThread(space, ec)
        self.sthread = sthread
        return sthread

    def check_sthread(self):
        ec = self.space.getexecutioncontext()
        if ec.stacklet_thread is not self.sthread:
            raise geterror(self.space, "inter-thread support is missing")

    def descr_init(self, w_callable):
        if self.h:
            raise geterror(self.space, "continuation already filled")
        sthread = self.build_sthread()
        start_state.origin = self
        start_state.w_callable = w_callable
        self.h = self.sthread.new(new_stacklet_callback)
        if not self.h:
            raise getmemoryerror(self.space)

    def descr_switch(self, w_value=None):
        start_state.w_value = w_value
        self.h = self.sthread.switch(self.h)
        w_value = start_state.w_value
        start_state.w_value = None
        return w_value


def W_Continuation___new__(space, w_subtype, __args__):
    r = space.allocate_instance(W_Continuation, w_subtype)
    r.__init__(space)
    return space.wrap(r)


W_Continuation.typedef = TypeDef(
    'continuation',
    __module__ = '_continuation',
    __new__     = interp2app(W_Continuation___new__),
    __init__    = interp2app(W_Continuation.descr_init),
    switch      = interp2app(W_Continuation.descr_switch),
    #is_pending = interp2app(W_Stacklet.is_pending),
    )


# ____________________________________________________________

# Continuation objects maintain a dummy frame object in order to ensure
# that the 'f_back' chain is consistent.  We hide this dummy frame
# object by having a dummy code object with hidden_applevel=True.

class ContinuationState:
    def __init__(self, space):
        self.space = space 
        w_module = space.getbuiltinmodule('_continuation')
        self.w_error = space.getattr(w_module, space.wrap('error'))
        self.dummy_pycode = PyCode(space, 0, 0, 0, 0,
                                   '', [], [], [], '',
                                   '', 0, '', [], [],
                                   hidden_applevel=True)
        self.w_dummy_globals = space.newdict()

def make_fresh_frame(space):
    cs = space.fromcache(ContinuationState)
    return space.FrameClass(space, cs.dummy_pycode,
                            cs.w_dummy_globals, closure=None)

def geterror(space, message):
    cs = space.fromcache(ContinuationState)
    return OperationError(cs.w_error, space.wrap(message))

def getmemoryerror(space):
    return OperationError(space.w_MemoryError, space.w_None)
getmemoryerror._annlowlevel_ = 'specialize:memo'

# ____________________________________________________________


class SThread(StackletThread):

    def __init__(self, space, ec):
        StackletThread.__init__(self, space.config)
        self.space = space
        self.ec = ec

ExecutionContext.stacklet_thread = None

# ____________________________________________________________


class StartState:   # xxx a single global to pass around the function to start
    def clear(self):
        self.origin = None
        self.w_callable = None
        self.args = None
        self.w_value = None
start_state = StartState()
start_state.clear()


def new_stacklet_callback(h, arg):
    self = start_state.origin
    w_callable = start_state.w_callable
    start_state.clear()
    self.h = self.sthread.switch(h)
    #
    space = self.space
    w_result = space.call_function(w_callable, space.wrap(self))
    #
    start_state.w_value = w_result
    return self.h
