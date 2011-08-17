from pypy.rlib.rstacklet import StackletThread, get_null_handle
from pypy.rlib import jit
from pypy.interpreter.error import OperationError
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app


class W_Continuation(Wrappable):
    sthread = None

    def __init__(self, space):
        self.space = space
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
        return ec

    def descr_init(self, w_callable, __args__):
        if self.h:
            raise geterror(self.space, "continuation already __init__ialized")
        sthread = self.build_sthread()
        start_state.origin = self
        start_state.w_callable = w_callable
        start_state.args = __args__
        try:
            self.h = sthread.new(new_stacklet_callback)
            if sthread.is_empty_handle(self.h):    # early return
                raise MemoryError
        except MemoryError:
            start_state.clear()
            raise getmemoryerror(self.space)

    def descr_switch(self, w_value=None):
        if not self.h:
            raise geterror(self.space, "continuation not initialized yet")
        if self.sthread.is_empty_handle(self.h):
            raise geterror(self.space, "continuation already finished")
        ec = self.check_sthread()
        saved_topframeref = ec.topframeref
        start_state.w_value = w_value
        try:
            self.h = self.sthread.switch(self.h)
        except MemoryError:
            start_state.clear()
            raise getmemoryerror(self.space)
        ec = self.sthread.ec
        ec.topframeref = saved_topframeref
        if start_state.propagate_exception:
            e = start_state.propagate_exception
            start_state.propagate_exception = None
            raise e
        w_value = start_state.w_value
        start_state.w_value = None
        return w_value

    def descr_is_pending(self):
        valid = bool(self.h) and not self.sthread.is_empty_handle(self.h)
        return self.space.newbool(valid)


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
    is_pending  = interp2app(W_Continuation.descr_is_pending),
    )


# ____________________________________________________________


class State:
    def __init__(self, space):
        self.space = space 
        w_module = space.getbuiltinmodule('_continuation')
        self.w_error = space.getattr(w_module, space.wrap('error'))
        self.w_memoryerror = OperationError(space.w_MemoryError, space.w_None)

def geterror(space, message):
    cs = space.fromcache(State)
    return OperationError(cs.w_error, space.wrap(message))

def getmemoryerror(space):
    cs = space.fromcache(State)
    return cs.w_memoryerror

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
        self.propagate_exception = None
start_state = StartState()
start_state.clear()


def new_stacklet_callback(h, arg):
    self       = start_state.origin
    w_callable = start_state.w_callable
    args       = start_state.args
    start_state.clear()
    try:
        self.h = self.sthread.switch(h)
    except MemoryError:
        return h       # oups!  do an early return in this case
    #
    space = self.space
    try:
        ec = self.sthread.ec
        ec.topframeref = jit.vref_None

        # I think we can't have start_state.propagate_exception here for
        # now, but in order to be future-proof...
        if start_state.propagate_exception is not None:
            return self.h    # just propagate it further
        if start_state.w_value is not space.w_None:
            raise OperationError(space.w_TypeError, space.wrap(
                "can't send non-None value to a just-started continuation"))

        args = args.prepend(space.wrap(self))
        w_result = space.call_args(w_callable, args)
    except Exception, e:
        start_state.propagate_exception = e
        return self.h
    else:
        start_state.w_value = w_result
        return self.h
