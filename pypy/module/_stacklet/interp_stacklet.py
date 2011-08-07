import sys
from pypy.rpython.lltypesystem import lltype
from pypy.rlib import jit
from pypy.rlib.rstacklet import StackletThread
from pypy.rlib.objectmodel import we_are_translated
from pypy.interpreter.error import OperationError
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app


class SThread(StackletThread):

    def __init__(self, space, ec):
        StackletThread.__init__(self, space.config)
        w_module = space.getbuiltinmodule('_stacklet')
        self.space = space
        self.ec = ec
        self.w_error = space.getattr(w_module, space.wrap('error'))
        self.pending_exception = None
        self.main_stacklet = None

    def __del__(self):
        if self.main_stacklet is not None:
            self.main_stacklet.__del__()
        StackletThread.__del__(self)

    def new_stacklet_object(self, h):
        if self.pending_exception is None:
            if self.is_empty_handle(h):
                return self.space.w_None
            else:
                return self.space.wrap(W_Stacklet(self, h))
        else:
            e = self.pending_exception
            self.pending_exception = None
            if not self.is_empty_handle(h):
                self.destroy(h)
            if we_are_translated():
                raise e
            else:
                tb = self.pending_tb
                del self.pending_tb
                raise e.__class__, e, tb

ExecutionContext.stacklet_thread = None


class W_Stacklet(Wrappable):
    def __init__(self, sthread, h):
        self.sthread = sthread
        self.h = h

    def __del__(self):
        h = self.h
        if h:
            self.h = self.sthread.get_null_handle()
            self.sthread.destroy(h)

    def consume_handle(self):
        h = self.h
        if h:
            self.h = self.sthread.get_null_handle()
            if self is self.sthread.main_stacklet:
                self.sthread.main_stacklet = None
            return h
        else:
            space = self.sthread.space
            raise OperationError(
                self.sthread.w_error,
                space.wrap("stacklet has already been resumed"))

    def switch(self, space):
        h = self.consume_handle()
        sthread = self.sthread
        ec = sthread.ec
        saved_frame_top = ec.topframeref
        try:
            h = sthread.switch(h)
        finally:
            ec.topframeref = saved_frame_top
        return sthread.new_stacklet_object(h)

    def is_pending(self, space):
        return space.newbool(bool(self.h))

W_Stacklet.typedef = TypeDef(
    'Stacklet',
    __module__ = '_stacklet',
    switch     = interp2app(W_Stacklet.switch),
    is_pending = interp2app(W_Stacklet.is_pending),
    )
W_Stacklet.acceptable_as_base_class = False


class StartState:
    sthread = None  # xxx a single global to pass around the function to start
    w_callable = None
    args = None
start_state = StartState()

def new_stacklet_callback(h, arg):
    sthread = start_state.sthread
    w_callable = start_state.w_callable
    args = start_state.args
    start_state.sthread = None
    start_state.w_callable = None
    start_state.args = None
    #
    try:
        space = sthread.space
        stacklet = W_Stacklet(sthread, h)
        if sthread.main_stacklet is None:
            sthread.main_stacklet = stacklet
        args = args.prepend(space.wrap(stacklet))
        w_result = space.call_args(w_callable, args)
        #
        result = space.interp_w(W_Stacklet, w_result)
        return result.consume_handle()
    #
    except Exception, e:
        sthread.pending_exception = e
        if not we_are_translated():
            sthread.pending_tb = sys.exc_info()[2]
        if sthread.main_stacklet is None:
            main_stacklet_handle = h
        else:
            main_stacklet_handle = sthread.main_stacklet.h
            sthread.main_stacklet.h = sthread.get_null_handle()
            sthread.main_stacklet = None
        assert main_stacklet_handle
        return main_stacklet_handle

def stacklet_new(space, w_callable, __args__):
    ec = space.getexecutioncontext()
    sthread = ec.stacklet_thread
    if not sthread:
        sthread = ec.stacklet_thread = SThread(space, ec)
    start_state.sthread = sthread
    start_state.w_callable = w_callable
    start_state.args = __args__
    saved_frame_top = ec.topframeref
    try:
        ec.topframeref = jit.vref_None
        h = sthread.new(new_stacklet_callback)
    finally:
        ec.topframeref = saved_frame_top
    return sthread.new_stacklet_object(h)
