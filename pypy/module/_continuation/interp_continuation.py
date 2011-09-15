from pypy.rlib.rstacklet import StackletThread
from pypy.rlib import jit
from pypy.interpreter.error import OperationError
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.pycode import PyCode


class W_Continulet(Wrappable):
    sthread = None

    def __init__(self, space):
        self.space = space
        # states:
        #  - not init'ed: self.sthread == None
        #  - normal:      self.sthread != None, not is_empty_handle(self.h)
        #  - finished:    self.sthread != None, is_empty_handle(self.h)

    def check_sthread(self):
        ec = self.space.getexecutioncontext()
        if ec.stacklet_thread is not self.sthread:
            global_state.clear()
            raise geterror(self.space, "inter-thread support is missing")
        return ec

    def descr_init(self, w_callable, __args__):
        if self.sthread is not None:
            raise geterror(self.space, "continulet already __init__ialized")
        global_state.origin = self
        global_state.w_callable = w_callable
        global_state.args = __args__
        self.bottomframe = make_fresh_frame(self.space)
        self.sthread = build_sthread(self.space)
        try:
            self.h = self.sthread.new(new_stacklet_callback)
            if self.sthread.is_empty_handle(self.h):    # early return
                raise MemoryError
        except MemoryError:
            self.sthread = None
            global_state.clear()
            raise getmemoryerror(self.space)

    def switch(self, w_to):
        sthread = self.sthread
        if sthread is not None and sthread.is_empty_handle(self.h):
            global_state.clear()
            raise geterror(self.space, "continulet already finished")
        to = self.space.interp_w(W_Continulet, w_to, can_be_None=True)
        if to is not None and to.sthread is None:
            to = None
        if sthread is None:      # if self is non-initialized:
            if to is not None:   #     if we are given a 'to'
                self = to        #         then just use it and ignore 'self'
                sthread = self.sthread
                to = None
            else:
                return get_result()  # else: no-op
        if to is not None:
            if to.sthread is not sthread:
                global_state.clear()
                raise geterror(self.space, "cross-thread double switch")
            if self is to:    # double-switch to myself: no-op
                return get_result()
            if sthread.is_empty_handle(to.h):
                global_state.clear()
                raise geterror(self.space, "continulet already finished")
        ec = self.check_sthread()
        #
        global_state.origin = self
        if to is None:
            # simple switch: going to self.h
            global_state.destination = self
        else:
            # double switch: the final destination is to.h
            global_state.destination = to
        #
        try:
            do_switch(sthread, global_state.destination.h)
        except MemoryError:
            global_state.clear()
            raise getmemoryerror(self.space)
        #
        return get_result()

    def descr_switch(self, w_value=None, w_to=None):
        global_state.w_value = w_value
        return self.switch(w_to)

    def descr_throw(self, w_type, w_val=None, w_tb=None, w_to=None):
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
        global_state.w_value = None
        global_state.propagate_exception = operr
        return self.switch(w_to)

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

# Continulet objects maintain a dummy frame object in order to ensure
# that the 'f_back' chain is consistent.  We hide this dummy frame
# object by giving it a dummy code object with hidden_applevel=True.

class State:
    def __init__(self, space):
        from pypy.interpreter.astcompiler.consts import CO_OPTIMIZED
        self.space = space 
        w_module = space.getbuiltinmodule('_continuation')
        self.w_error = space.getattr(w_module, space.wrap('error'))
        self.w_memoryerror = OperationError(space.w_MemoryError, space.w_None)
        self.dummy_pycode = PyCode(space, 0, 0, 0, CO_OPTIMIZED,
                                   '', [], [], [], '',
                                   '<bottom of continulet>', 0, '', [], [],
                                   hidden_applevel=True)

def geterror(space, message):
    cs = space.fromcache(State)
    return OperationError(cs.w_error, space.wrap(message))

def getmemoryerror(space):
    cs = space.fromcache(State)
    return cs.w_memoryerror

def make_fresh_frame(space):
    cs = space.fromcache(State)
    return space.FrameClass(space, cs.dummy_pycode, None, None)

# ____________________________________________________________


class SThread(StackletThread):

    def __init__(self, space, ec):
        StackletThread.__init__(self, space.config)
        self.space = space
        self.ec = ec

ExecutionContext.stacklet_thread = None

# ____________________________________________________________


class GlobalState:
    def clear(self):
        self.origin = None
        self.destination = None
        self.w_callable = None
        self.args = None
        self.w_value = None
        self.propagate_exception = None
global_state = GlobalState()
global_state.clear()


def new_stacklet_callback(h, arg):
    self       = global_state.origin
    w_callable = global_state.w_callable
    args       = global_state.args
    global_state.clear()
    try:
        do_switch(self.sthread, h)
    except MemoryError:
        return h       # oups!  do an early return in this case
    #
    space = self.space
    try:
        assert self.sthread.ec.topframeref() is None
        self.sthread.ec.topframeref = jit.non_virtual_ref(self.bottomframe)
        if global_state.propagate_exception is not None:
            raise global_state.propagate_exception  # just propagate it further
        if global_state.w_value is not space.w_None:
            raise OperationError(space.w_TypeError, space.wrap(
                "can't send non-None value to a just-started continulet"))

        args = args.prepend(self.space.wrap(self))
        w_result = space.call_args(w_callable, args)
    except Exception, e:
        global_state.propagate_exception = e
    else:
        global_state.w_value = w_result
    self.sthread.ec.topframeref = jit.vref_None
    global_state.origin = self
    global_state.destination = self
    return self.h


def do_switch(sthread, h):
    h = sthread.switch(h)
    origin = global_state.origin
    self = global_state.destination
    global_state.origin = None
    global_state.destination = None
    self.h, origin.h = origin.h, h
    #
    current = sthread.ec.topframeref
    sthread.ec.topframeref = self.bottomframe.f_backref
    self.bottomframe.f_backref = origin.bottomframe.f_backref
    origin.bottomframe.f_backref = current

def get_result():
    if global_state.propagate_exception:
        e = global_state.propagate_exception
        global_state.propagate_exception = None
        raise e
    w_value = global_state.w_value
    global_state.w_value = None
    return w_value

def build_sthread(space):
    ec = space.getexecutioncontext()
    sthread = ec.stacklet_thread
    if not sthread:
        sthread = ec.stacklet_thread = SThread(space, ec)
    return sthread

# ____________________________________________________________

def permute(space, args_w):
    sthread = build_sthread(space)
    #
    contlist = []
    for w_cont in args_w:
        cont = space.interp_w(W_Continulet, w_cont)
        if cont.sthread is not sthread:
            if cont.sthread is None:
                raise geterror(space, "got a non-initialized continulet")
            else:
                raise geterror(space, "inter-thread support is missing")
        elif sthread.is_empty_handle(cont.h):
            raise geterror(space, "got an already-finished continulet")
        contlist.append(cont)
    #
    if len(contlist) > 1:
        otherh = contlist[-1].h
        otherb = contlist[-1].bottomframe.f_backref
        for cont in contlist:
            otherh, cont.h = cont.h, otherh
            b = cont.bottomframe
            otherb, b.f_backref = b.f_backref, otherb
