import sys
from pypy.interpreter.miscutils import Stack
from pypy.interpreter.error import OperationError
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib import jit

TICK_COUNTER_STEP = 100

def app_profile_call(space, w_callable, frame, event, w_arg):
    space.call_function(w_callable,
                        space.wrap(frame),
                        space.wrap(event), w_arg)

class ExecutionContext(object):
    """An ExecutionContext holds the state of an execution thread
    in the Python interpreter."""

    # XXX JIT: when tracing (but not when blackholing!), the following
    # XXX fields should be known to a constant None or False:
    # XXX   self.w_tracefunc, self.profilefunc
    # XXX   frame.is_being_profiled

    # XXX [fijal] but they're not. is_being_profiled is guarded a bit all
    #     over the place as well as w_tracefunc

    _immutable_fields_ = ['profilefunc?', 'w_tracefunc?']

    def __init__(self, space):
        self.space = space
        self.topframeref = jit.vref_None
        # tracing: space.frame_trace_action.fire() must be called to ensure
        # that tracing occurs whenever self.w_tracefunc or self.is_tracing
        # is modified.
        self.w_tracefunc = None        # if not None, no JIT
        self.is_tracing = 0
        self.compiler = space.createcompiler()
        self.profilefunc = None        # if not None, no JIT
        self.w_profilefuncarg = None

    def gettopframe(self):
        return self.topframeref()

    def gettopframe_nohidden(self):
        frame = self.topframeref()
        while frame and frame.hide():
            frame = frame.f_backref()
        return frame

    @staticmethod
    def getnextframe_nohidden(frame):
        frame = frame.f_backref()
        while frame and frame.hide():
            frame = frame.f_backref()
        return frame

    def enter(self, frame):
        frame.f_backref = self.topframeref
        self.topframeref = jit.virtual_ref(frame)

    def leave(self, frame, w_exitvalue, got_exception):
        try:
            if self.profilefunc:
                self._trace(frame, 'leaveframe', w_exitvalue)
        finally:
            frame_vref = self.topframeref
            self.topframeref = frame.f_backref
            if frame.escaped or got_exception:
                # if this frame escaped to applevel, we must ensure that also
                # f_back does
                f_back = frame.f_backref()
                if f_back:
                    f_back.mark_as_escaped()
                # force the frame (from the JIT point of view), so that it can
                # be accessed also later
                frame_vref()
            jit.virtual_ref_finish(frame_vref, frame)

        if self.w_tracefunc is not None and not frame.hide():
            self.space.frame_trace_action.fire()

    # ________________________________________________________________


    class Subcontext(object):
        # coroutine: subcontext support

        def __init__(self):
            self.topframe = None
            self.w_tracefunc = None
            self.profilefunc = None
            self.w_profilefuncarg = None
            self.is_tracing = 0

        def enter(self, ec):
            ec.topframeref = jit.non_virtual_ref(self.topframe)
            ec.w_tracefunc = self.w_tracefunc
            ec.profilefunc = self.profilefunc
            ec.w_profilefuncarg = self.w_profilefuncarg
            ec.is_tracing = self.is_tracing
            ec.space.frame_trace_action.fire()

        def leave(self, ec):
            self.topframe = ec.gettopframe()
            self.w_tracefunc = ec.w_tracefunc
            self.profilefunc = ec.profilefunc
            self.w_profilefuncarg = ec.w_profilefuncarg
            self.is_tracing = ec.is_tracing

        def clear_framestack(self):
            self.topframe = None

        # the following interface is for pickling and unpickling
        def getstate(self, space):
            # XXX we could just save the top frame, which brings
            # the whole frame stack, but right now we get the whole stack
            items = [space.wrap(f) for f in self.getframestack()]
            return space.newtuple(items)

        def setstate(self, space, w_state):
            from pypy.interpreter.pyframe import PyFrame
            frames_w = space.unpackiterable(w_state)
            if len(frames_w) > 0:
                self.topframe = space.interp_w(PyFrame, frames_w[-1])
            else:
                self.topframe = None

        def getframestack(self):
            lst = []
            f = self.topframe
            while f is not None:
                lst.append(f)
                f = f.f_backref()
            lst.reverse()
            return lst
        # coroutine: I think this is all, folks!

    def c_call_trace(self, frame, w_func, args=None):
        "Profile the call of a builtin function"
        self._c_call_return_trace(frame, w_func, args, 'c_call')

    def c_return_trace(self, frame, w_func, args=None):
        "Profile the return from a builtin function"
        self._c_call_return_trace(frame, w_func, args, 'c_return')

    def _c_call_return_trace(self, frame, w_func, args, event):
        if self.profilefunc is None:
            frame.is_being_profiled = False
        else:
            # undo the effect of the CALL_METHOD bytecode, which would be
            # that even on a built-in method call like '[].append()',
            # w_func is actually the unbound function 'append'.
            from pypy.interpreter.function import FunctionWithFixedCode
            if isinstance(w_func, FunctionWithFixedCode) and args is not None:
                w_firstarg = args.firstarg()
                if w_firstarg is not None:
                    from pypy.interpreter.function import descr_function_get
                    w_func = descr_function_get(self.space, w_func, w_firstarg,
                                                self.space.type(w_firstarg))
            #
            self._trace(frame, event, w_func)

    def c_exception_trace(self, frame, w_exc):
        "Profile function called upon OperationError."
        if self.profilefunc is None:
            frame.is_being_profiled = False
        else:
            self._trace(frame, 'c_exception', w_exc)

    def call_trace(self, frame):
        "Trace the call of a function"
        if self.w_tracefunc is not None or self.profilefunc is not None:
            self._trace(frame, 'call', self.space.w_None)
            if self.profilefunc:
                frame.is_being_profiled = True

    def return_trace(self, frame, w_retval):
        "Trace the return from a function"
        if self.w_tracefunc is not None:
            return_from_hidden = self._trace(frame, 'return', w_retval)
            # special case: if we are returning from a hidden function,
            # then maybe we have to fire() the action again; otherwise
            # it will not be called.  See test_trace_hidden_prints.
            if return_from_hidden:
                self.space.frame_trace_action.fire()

    def bytecode_trace(self, frame, decr_by=TICK_COUNTER_STEP):
        "Trace function called before each bytecode."
        # this is split into a fast path and a slower path that is
        # not invoked every time bytecode_trace() is.
        actionflag = self.space.actionflag
        if actionflag.decrement_ticker(decr_by) < 0:
            actionflag.action_dispatcher(self, frame)     # slow path
    bytecode_trace._always_inline_ = True

    def bytecode_trace_after_exception(self, frame):
        "Like bytecode_trace(), but without increasing the ticker."
        actionflag = self.space.actionflag
        if actionflag.get_ticker() < 0:
            actionflag.action_dispatcher(self, frame)     # slow path
    bytecode_trace_after_exception._always_inline_ = True

    def exception_trace(self, frame, operationerr):
        "Trace function called upon OperationError."
        operationerr.record_interpreter_traceback()
        if self.w_tracefunc is not None:
            self._trace(frame, 'exception', None, operationerr)
        #operationerr.print_detailed_traceback(self.space)

    def _convert_exc(self, operr):
        return operr

    def sys_exc_info(self): # attn: the result is not the wrapped sys.exc_info() !!!
        """Implements sys.exc_info().
        Return an OperationError instance or None."""
        frame = self.gettopframe_nohidden()
        while frame:
            if frame.last_exception is not None:
                return self._convert_exc(frame.last_exception)
            frame = self.getnextframe_nohidden(frame)
        return None

    def settrace(self, w_func):
        """Set the global trace function."""
        if self.space.is_w(w_func, self.space.w_None):
            self.w_tracefunc = None
        else:
            self.force_all_frames()
            self.w_tracefunc = w_func
            self.space.frame_trace_action.fire()

    def setprofile(self, w_func):
        """Set the global trace function."""
        if self.space.is_w(w_func, self.space.w_None):
            self.profilefunc = None
            self.w_profilefuncarg = None
        else:
            self.setllprofile(app_profile_call, w_func)

    def getprofile(self):
        return self.w_profilefuncarg

    def setllprofile(self, func, w_arg):
        if func is not None:
            if w_arg is None:
                raise ValueError("Cannot call setllprofile with real None")
            self.force_all_frames(is_being_profiled=True)
        self.profilefunc = func
        self.w_profilefuncarg = w_arg

    def force_all_frames(self, is_being_profiled=False):
        # "Force" all frames in the sense of the jit, and optionally
        # set the flag 'is_being_profiled' on them.  A forced frame is
        # one out of which the jit will exit: if it is running so far,
        # in a piece of assembler currently running a CALL_MAY_FORCE,
        # then being forced means that it will fail the following
        # GUARD_NOT_FORCED operation, and so fall back to interpreted
        # execution.  (We get this effect simply by reading the f_back
        # field of all frames, during the loop below.)
        frame = self.gettopframe_nohidden()
        while frame:
            if is_being_profiled:
                frame.is_being_profiled = True
            frame = self.getnextframe_nohidden(frame)

    def call_tracing(self, w_func, w_args):
        is_tracing = self.is_tracing
        self.is_tracing = 0
        try:
            self.space.frame_trace_action.fire()
            return self.space.call(w_func, w_args)
        finally:
            self.is_tracing = is_tracing

    def _trace(self, frame, event, w_arg, operr=None):
        if self.is_tracing or frame.hide():
            return True

        space = self.space

        # Tracing cases
        if event == 'call':
            w_callback = self.w_tracefunc
        else:
            w_callback = frame.w_f_trace

        if w_callback is not None and event != "leaveframe":
            if operr is not None:
                w_value = operr.get_w_value(space)
                w_arg = space.newtuple([operr.w_type, w_value,
                                     space.wrap(operr.get_traceback())])

            frame.fast2locals()
            self.is_tracing += 1
            try:
                try:
                    w_result = space.call_function(w_callback, space.wrap(frame), space.wrap(event), w_arg)
                    if space.is_w(w_result, space.w_None):
                        frame.w_f_trace = None
                    else:
                        frame.w_f_trace = w_result
                except:
                    self.settrace(space.w_None)
                    frame.w_f_trace = None
                    raise
            finally:
                self.is_tracing -= 1
                frame.locals2fast()
                space.frame_trace_action.fire()

        # Profile cases
        if self.profilefunc is not None:
            if not (event == 'leaveframe' or
                    event == 'call' or
                    event == 'c_call' or
                    event == 'c_return' or
                    event == 'c_exception'):
                return False

            last_exception = frame.last_exception
            if event == 'leaveframe':
                event = 'return'

            assert self.is_tracing == 0
            self.is_tracing += 1
            try:
                try:
                    self.profilefunc(space, self.w_profilefuncarg,
                                     frame, event, w_arg)
                except:
                    self.profilefunc = None
                    self.w_profilefuncarg = None
                    raise

            finally:
                frame.last_exception = last_exception
                self.is_tracing -= 1
        return False

    def checksignals(self):
        """Similar to PyErr_CheckSignals().  If called in the main thread,
        and if signals are pending for the process, deliver them now
        (i.e. call the signal handlers)."""
        if self.space.check_signal_action is not None:
            self.space.check_signal_action.perform(self, None)

    def _freeze_(self):
        raise Exception("ExecutionContext instances should not be seen during"
                        " translation.  Now is a good time to inspect the"
                        " traceback and see where this one comes from :-)")


class AbstractActionFlag(object):
    """This holds in an integer the 'ticker'.  If threads are enabled,
    it is decremented at each bytecode; when it reaches zero, we release
    the GIL.  And whether we have threads or not, it is forced to zero
    whenever we fire any of the asynchronous actions.
    """
    def __init__(self):
        self._periodic_actions = []
        self._nonperiodic_actions = []
        self.has_bytecode_counter = False
        self.fired_actions = None
        self.checkinterval_scaled = 100 * TICK_COUNTER_STEP
        self._rebuild_action_dispatcher()

    def fire(self, action):
        """Request for the action to be run before the next opcode."""
        if not action._fired:
            action._fired = True
            if self.fired_actions is None:
                self.fired_actions = []
            self.fired_actions.append(action)
            # set the ticker to -1 in order to force action_dispatcher()
            # to run at the next possible bytecode
            self.reset_ticker(-1)

    def register_periodic_action(self, action, use_bytecode_counter):
        """NOT_RPYTHON:
        Register the PeriodicAsyncAction action to be called whenever the
        tick counter becomes smaller than 0.  If 'use_bytecode_counter' is
        True, make sure that we decrease the tick counter at every bytecode.
        This is needed for threads.  Note that 'use_bytecode_counter' can be
        False for signal handling, because whenever the process receives a
        signal, the tick counter is set to -1 by C code in signals.h.
        """
        assert isinstance(action, PeriodicAsyncAction)
        self._periodic_actions.append(action)
        if use_bytecode_counter:
            self.has_bytecode_counter = True
        self._rebuild_action_dispatcher()

    def getcheckinterval(self):
        return self.checkinterval_scaled // TICK_COUNTER_STEP

    def setcheckinterval(self, interval):
        MAX = sys.maxint // TICK_COUNTER_STEP
        if interval < 1:
            interval = 1
        elif interval > MAX:
            interval = MAX
        self.checkinterval_scaled = interval * TICK_COUNTER_STEP

    def _rebuild_action_dispatcher(self):
        periodic_actions = unrolling_iterable(self._periodic_actions)

        @jit.dont_look_inside
        def action_dispatcher(ec, frame):
            # periodic actions (first reset the bytecode counter)
            self.reset_ticker(self.checkinterval_scaled)
            for action in periodic_actions:
                action.perform(ec, frame)

            # nonperiodic actions
            list = self.fired_actions
            if list is not None:
                self.fired_actions = None
                for action in list:
                    action._fired = False
                    action.perform(ec, frame)

        action_dispatcher._dont_inline_ = True
        self.action_dispatcher = action_dispatcher


class ActionFlag(AbstractActionFlag):
    """The normal class for space.actionflag.  The signal module provides
    a different one."""
    _ticker = 0

    def get_ticker(self):
        return self._ticker

    def reset_ticker(self, value):
        self._ticker = value

    def decrement_ticker(self, by):
        value = self._ticker
        if self.has_bytecode_counter:    # this 'if' is constant-folded
            value -= by
            self._ticker = value
        return value


class AsyncAction(object):
    """Abstract base class for actions that must be performed
    asynchronously with regular bytecode execution, but that still need
    to occur between two opcodes, not at a completely random time.
    """
    _fired = False

    def __init__(self, space):
        self.space = space

    def fire(self):
        """Request for the action to be run before the next opcode.
        The action must have been registered at space initalization time."""
        self.space.actionflag.fire(self)

    def fire_after_thread_switch(self):
        """Bit of a hack: fire() the action but only the next time the GIL
        is released and re-acquired (i.e. after a potential thread switch).
        Don't call this if threads are not enabled.  Currently limited to
        one action (i.e. reserved for CheckSignalAction from module/signal).
        """
        from pypy.module.thread.gil import spacestate
        spacestate.action_after_thread_switch = self

    def perform(self, executioncontext, frame):
        """To be overridden."""


class PeriodicAsyncAction(AsyncAction):
    """Abstract base class for actions that occur automatically
    every sys.checkinterval bytecodes.
    """


class UserDelAction(AsyncAction):
    """An action that invokes all pending app-level __del__() method.
    This is done as an action instead of immediately when the
    interp-level __del__() is invoked, because the latter can occur more
    or less anywhere in the middle of code that might not be happy with
    random app-level code mutating data structures under its feet.
    """

    def __init__(self, space):
        AsyncAction.__init__(self, space)
        self.dying_objects_w = []
        self.weakrefs_w = []
        self.finalizers_lock_count = 0

    def register_dying_object(self, w_obj):
        self.dying_objects_w.append(w_obj)
        self.fire()

    def register_weakref_callback(self, w_ref):
        self.weakrefs_w.append(w_ref)
        self.fire()

    def perform(self, executioncontext, frame):
        if self.finalizers_lock_count > 0:
            return
        # Each call to perform() first grabs the self.dying_objects_w
        # and replaces it with an empty list.  We do this to try to
        # avoid too deep recursions of the kind of __del__ being called
        # while in the middle of another __del__ call.
        pending_w = self.dying_objects_w
        self.dying_objects_w = []
        space = self.space
        for i in range(len(pending_w)):
            w_obj = pending_w[i]
            pending_w[i] = None
            try:
                space.userdel(w_obj)
            except OperationError, e:
                e.write_unraisable(space, 'method __del__ of ', w_obj)
                e.clear(space)   # break up reference cycles
            # finally, this calls the interp-level destructor for the
            # cases where there is both an app-level and a built-in __del__.
            w_obj._call_builtin_destructor()
        pending_w = self.weakrefs_w
        self.weakrefs_w = []
        for i in range(len(pending_w)):
            w_ref = pending_w[i]
            w_ref.activate_callback()

class FrameTraceAction(AsyncAction):
    """An action that calls the local trace functions (w_f_trace)."""

    def perform(self, executioncontext, frame):
        if (frame.w_f_trace is None or executioncontext.is_tracing or
            executioncontext.w_tracefunc is None):
            return
        code = frame.pycode
        if frame.instr_lb <= frame.last_instr < frame.instr_ub:
            if frame.last_instr < frame.instr_prev_plus_one:
                # We jumped backwards in the same line.
                executioncontext._trace(frame, 'line', self.space.w_None)
        else:
            size = len(code.co_lnotab) / 2
            addr = 0
            line = code.co_firstlineno
            p = 0
            lineno = code.co_lnotab
            while size > 0:
                c = ord(lineno[p])
                if (addr + c) > frame.last_instr:
                    break
                addr += c
                if c:
                    frame.instr_lb = addr

                line += ord(lineno[p + 1])
                p += 2
                size -= 1

            if size > 0:
                while True:
                    size -= 1
                    if size < 0:
                        break
                    addr += ord(lineno[p])
                    if ord(lineno[p + 1]):
                        break
                    p += 2
                frame.instr_ub = addr
            else:
                frame.instr_ub = sys.maxint

            if frame.instr_lb == frame.last_instr: # At start of line!
                frame.f_lineno = line
                executioncontext._trace(frame, 'line', self.space.w_None)

        frame.instr_prev_plus_one = frame.last_instr + 1
        self.space.frame_trace_action.fire()     # continue tracing
