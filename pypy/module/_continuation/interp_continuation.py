from pypy.rlib.rstacklet import StackletThread
from pypy.rlib import jit
from pypy.interpreter.error import OperationError
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app


class W_Continulet(Wrappable):
    sthread = None

    def __init__(self, space):
        self.space = space
        # states:
        #  - not init'ed: self.sthread == None
        #  - normal:      self.sthread != None, not is_empty_handle(self.h)
        #  - finished:    self.sthread != None, is_empty_handle(self.h)

    def build_sthread(self):
        space = self.space
        ec = space.getexecutioncontext()
        sthread = ec.stacklet_thread
        if not sthread:
            sthread = ec.stacklet_thread = SThread(space, ec)
        self.sthread = sthread

    def check_sthread(self):
        ec = self.space.getexecutioncontext()
        if ec.stacklet_thread is not self.sthread:
            start_state.clear()
            raise geterror(self.space, "inter-thread support is missing")
        return ec

    def descr_init(self, w_callable, __args__):
        if self.sthread is not None:
            raise geterror(self.space, "continulet already __init__ialized")
        start_state.origin = self
        start_state.w_callable = w_callable
        start_state.args = __args__
        self.build_sthread()
        try:
            self.h = self.sthread.new(new_stacklet_callback)
            if self.sthread.is_empty_handle(self.h):    # early return
                raise MemoryError
        except MemoryError:
            self.sthread = None
            start_state.clear()
            raise getmemoryerror(self.space)

    def switch(self, to=None):
        if self.sthread is None:
            start_state.clear()
            raise geterror(self.space, "continulet not initialized yet")
        if self.sthread.is_empty_handle(self.h):
            start_state.clear()
            raise geterror(self.space, "continulet already finished")
        ec = self.check_sthread()
        saved_topframeref = ec.topframeref
        #
        start_state.origin = self
        if to is None:
            # simple switch: going to self.h
            start_state.destination = self
        else:
            # double switch: the final destination is to.h
            start_state.destination = to
        #
        try:
            sthread = self.sthread
            do_switch(sthread, start_state.destination.h)
        except MemoryError:
            start_state.clear()
            raise getmemoryerror(self.space)
        #
        ec = sthread.ec
        ec.topframeref = saved_topframeref
        if start_state.propagate_exception:
            e = start_state.propagate_exception
            start_state.propagate_exception = None
            raise e
        w_value = start_state.w_value
        start_state.w_value = None
        return w_value

    def descr_switch(self, w_value=None, w_to=None):
        to = self.space.interp_w(W_Continulet, w_to, can_be_None=True)
        if self is to:    # double-switch to myself: no-op
            return w_value
        start_state.w_value = w_value
        return self.switch(to)

    def descr_throw(self, w_type, w_val=None, w_tb=None):
        from pypy.interpreter.pytraceback import check_traceback
        space = self.space
        #
        msg = "throw() third argument must be a traceback object"
        if space.is_w(w_tb, space.w_None):
            tb = None
        else:
            tb = check_traceback(space, w_tb, msg)
        #
        operr = OperationError(w_type, w_val, tb)
        operr.normalize_exception(space)
        start_state.propagate_exception = operr
        return self.switch()

    def descr_is_pending(self):
        valid = (self.sthread is not None
                 and not self.sthread.is_empty_handle(self.h))
        return self.space.newbool(valid)


def W_Continulet___new__(space, w_subtype, __args__):
    r = space.allocate_instance(W_Continulet, w_subtype)
    r.__init__(space)
    return space.wrap(r)


W_Continulet.typedef = TypeDef(
    'continulet',
    __module__ = '_continuation',
    __new__     = interp2app(W_Continulet___new__),
    __init__    = interp2app(W_Continulet.descr_init),
    switch      = interp2app(W_Continulet.descr_switch),
    throw       = interp2app(W_Continulet.descr_throw),
    is_pending  = interp2app(W_Continulet.descr_is_pending),
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
        self.destination = None
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
        do_switch(self.sthread, h)
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
                "can't send non-None value to a just-started continulet"))

        args = args.prepend(self.space.wrap(self))
        w_result = space.call_args(w_callable, args)
    except Exception, e:
        start_state.propagate_exception = e
    else:
        start_state.w_value = w_result
    start_state.origin = self
    start_state.destination = self
    return self.h


def do_switch(sthread, h):
    h = sthread.switch(h)
    origin = start_state.origin
    self = start_state.destination
    start_state.origin = None
    start_state.destination = None
    self.h, origin.h = origin.h, h
