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
from pypy.rlib.debug import ll_assert, fatalerror

#
# Note: a "continuation" at app-level is called a "stacklet" here.
#

class SThread(StackletThread):

    def __init__(self, space, ec):
        StackletThread.__init__(self, space.config)
        w_module = space.getbuiltinmodule('_continuation')
        self.space = space
        self.ec = ec
        self.w_error = space.getattr(w_module, space.wrap('error'))
        self.pending_exception = None
        self.current_stack = StackTreeNode(None)

    def new_stacklet_object(self, h, in_new_stack):
        # Called when we switched somewhere else.  'h' is the handle of
        # the new stacklet, i.e. what we just switched away from.
        # (Important: only called when the switch was successful, not
        # when it raises MemoryError.)
        #
        # Update self.current_stack.
        in_old_stack = self.current_stack
        ll_assert(in_old_stack.current_stacklet is None,
                  "in_old_stack should not have a current_stacklet")
        ll_assert(in_new_stack is not in_old_stack,
                  "stack switch: switch to itself")
        in_new_stack.current_stacklet = None
        self.current_stack = in_new_stack
        #
        if self.pending_exception is None:
            #
            # Normal case.
            if self.is_empty_handle(h):
                return self.space.w_None
            else:
                res = W_Stacklet(self, h)
                in_old_stack.current_stacklet = res
                return self.space.wrap(res)
        else:
            # Got an exception; re-raise it.
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


class StackTreeNode(object):
    # When one stacklet gets an exception, it is propagated to the
    # "parent" stacklet.  Parents make a tree.  Each stacklet is
    # conceptually part of a stack that doesn't change when we switch
    # away and back.  The "parent stack" is the stack from which we
    # created the new() stack.  (This part works like greenlets.)
    #
    # It is important that we have *no* app-level access to this tree.
    # It would break the 'composability' of stacklets.
    #
    def __init__(self, parent):
        self.parent = parent
        self.current_stacklet = None

    def raising_exception(self):
        while self.current_stacklet is None:
            self = self.parent
            if self is None:
                fatalerror("StackTreeNode chain is empty!")
        res = self.current_stacklet
        self.current_stacklet = None
        try:
            return res.consume_handle()
        except OperationError:
            fatalerror("StackTreeNode contains an empty stacklet")
            raise ValueError    # annotator hack, but cannot return

    def __repr__(self):
        s = '|>'
        k = self
        while k:
            s = hex(id(k)) + ' ' + s
            k = k.parent
        s = '<StackTreeNode |' + s
        return s


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
            return h
        else:
            space = self.sthread.space
            raise OperationError(
                self.sthread.w_error,
                space.wrap("continuation has already been resumed"))

    def switch(self, space):
        sthread = self.sthread
        ec = sthread.ec
        stack = sthread.current_stack
        saved_frame_top = ec.topframeref
        try:
            h1 = self.consume_handle()
            try:
                h = sthread.switch(h1)
            except MemoryError:
                self.h = h1    # try to restore
                raise
        finally:
            ec.topframeref = saved_frame_top
        return sthread.new_stacklet_object(h, stack)

    def is_pending(self, space):
        return space.newbool(bool(self.h))

W_Stacklet.typedef = TypeDef(
    'Continuation',
    __module__ = '_continuation',
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
    ready = False
    parentstacknode = sthread.current_stack
    #
    try:
        space = sthread.space
        stacknode = StackTreeNode(parentstacknode)
        stacklet = sthread.new_stacklet_object(h, stacknode)
        ready = True
        args = args.prepend(stacklet)
        w_result = space.call_args(w_callable, args)
        #
        try:
            result = space.interp_w(W_Stacklet, w_result)
            return result.consume_handle()
        except OperationError, e:
            w_value = e.get_w_value(space)
            msg = 'returning from _continuation.new: ' + space.str_w(w_value)
            raise OperationError(e.w_type, space.wrap(msg))
    #
    except Exception, e:
        sthread.pending_exception = e
        if not we_are_translated():
            print >> sys.stderr
            print >> sys.stderr, '*** exception in stacklet ***'
            sthread.pending_tb = sys.exc_info()[2]
            import traceback
            traceback.print_exc(sthread.pending_tb)
            print >> sys.stderr, '***'
            #import pdb; pdb.post_mortem(sthread.pending_tb)
        if ready:
            return parentstacknode.raising_exception()
        else:
            return h      # corner case, try with just returning h...

def stacklet_new(space, w_callable, __args__):
    ec = space.getexecutioncontext()
    sthread = ec.stacklet_thread
    if not sthread:
        sthread = ec.stacklet_thread = SThread(space, ec)
    start_state.sthread = sthread
    start_state.w_callable = w_callable
    start_state.args = __args__
    stack = sthread.current_stack
    saved_frame_top = ec.topframeref
    try:
        ec.topframeref = jit.vref_None
        h = sthread.new(new_stacklet_callback)
    finally:
        ec.topframeref = saved_frame_top
    return sthread.new_stacklet_object(h, stack)
