import sys
from pypy.interpreter.miscutils import Stack
from pypy.interpreter.error import OperationError
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rlib.unroll import unrolling_iterable

def new_framestack():
    return Stack()

def app_profile_call(space, w_callable, frame, event, w_arg):
    space.call_function(w_callable,
                        space.wrap(frame),
                        space.wrap(event), w_arg)

class ExecutionContext:
    """An ExecutionContext holds the state of an execution thread
    in the Python interpreter."""

    def __init__(self, space):
        self.space = space
        self.framestack = new_framestack()
        # tracing: space.frame_trace_action.fire() must be called to ensure
        # that tracing occurs whenever self.w_tracefunc or self.is_tracing
        # is modified.
        self.w_tracefunc = None
        self.is_tracing = 0
        self.compiler = space.createcompiler()
        self.profilefunc = None
        self.w_profilefuncarg = None

    def enter(self, frame):
        if self.framestack.depth() > self.space.sys.recursionlimit:
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("maximum recursion depth exceeded"))
        try:
            frame.f_back = self.framestack.top()
        except IndexError:
            frame.f_back = None

        if not frame.hide():
            self.framestack.push(frame)

    def leave(self, frame):
        if self.profilefunc:
            self._trace(frame, 'leaveframe', None)
                
        if not frame.hide():
            self.framestack.pop()
            if self.w_tracefunc is not None:
                self.space.frame_trace_action.fire()


    class Subcontext(object):
        # coroutine: subcontext support

        def __init__(self):
            self.framestack = new_framestack()
            self.w_tracefunc = None
            self.profilefunc = None
            self.w_profilefuncarg = None
            self.is_tracing = 0

        def enter(self, ec):
            ec.framestack = self.framestack
            ec.w_tracefunc = self.w_tracefunc
            ec.profilefunc = self.profilefunc
            ec.w_profilefuncarg = self.w_profilefuncarg
            ec.is_tracing = self.is_tracing
            ec.space.frame_trace_action.fire()

        def leave(self, ec):
            self.framestack = ec.framestack
            self.w_tracefunc = ec.w_tracefunc
            self.profilefunc = ec.profilefunc
            self.w_profilefuncarg = ec.w_profilefuncarg
            self.is_tracing = ec.is_tracing

        # the following interface is for pickling and unpickling
        def getstate(self, space):
            # we just save the framestack
            items = [space.wrap(item) for item in self.framestack.items]
            return space.newtuple(items)

        def setstate(self, space, w_state):
            from pypy.interpreter.pyframe import PyFrame
            items = [space.interp_w(PyFrame, w_item)
                     for w_item in space.unpackiterable(w_state)]
            self.framestack.items = items
        # coroutine: I think this is all, folks!


    def get_builtin(self):
        try:
            return self.framestack.top().builtin
        except IndexError:
            return self.space.builtin

    # XXX this one should probably be dropped in favor of a module
    def make_standard_w_globals(self):
        "Create a new empty 'globals' dictionary."
        w_key = self.space.wrap("__builtins__")
        w_value = self.space.wrap(self.get_builtin())
        w_globals = self.space.newdict()
        space.setitem(w_globals, w_key, w_value)
        return w_globals

    def call_trace(self, frame):
        "Trace the call of a function"
        if self.w_tracefunc is not None or self.profilefunc is not None:
            self._trace(frame, 'call', self.space.w_None)

    def return_trace(self, frame, w_retval):
        "Trace the return from a function"
        if self.w_tracefunc is not None:
            self._trace(frame, 'return', w_retval)

    def bytecode_trace(self, frame):
        "Trace function called before each bytecode."
        # this is split into a fast path and a slower path that is
        # not invoked every time bytecode_trace() is.
        actionflag = self.space.actionflag
        ticker = actionflag.get()
        if actionflag.has_bytecode_counter:    # this "if" is constant-folded
            ticker += 1
            actionflag.set(ticker)
        if ticker & actionflag.interesting_bits:  # fast check
            actionflag.action_dispatcher(self)        # slow path
    bytecode_trace._always_inline_ = True

    def exception_trace(self, frame, operationerr):
        "Trace function called upon OperationError."
        operationerr.record_interpreter_traceback()
        if self.w_tracefunc is not None:
            self._trace(frame, 'exception', None, operationerr)
        #operationerr.print_detailed_traceback(self.space)

    def sys_exc_info(self): # attn: the result is not the wrapped sys.exc_info() !!!
        """Implements sys.exc_info().
        Return an OperationError instance or None."""
        for i in range(self.framestack.depth()):
            frame = self.framestack.top(i)
            if frame.last_exception is not None:
                return frame.last_exception
        return None

    def settrace(self, w_func):
        """Set the global trace function."""
        if self.space.is_w(w_func, self.space.w_None):
            self.w_tracefunc = None
        else:
            self.w_tracefunc = w_func
            self.space.frame_trace_action.fire()

    def setprofile(self, w_func):
        """Set the global trace function."""
        if self.space.is_w(w_func, self.space.w_None):
            self.profilefunc = None
            self.w_profilefuncarg = None
        else:
            self.w_profilefuncarg = w_func
            self.profilefunc = app_profile_call

    def setllprofile(self, func, w_arg):
        self.profilefunc = func
        if func is not None and w_arg is None:
            raise ValueError("Cannot call setllprofile with real None")
        self.w_profilefuncarg = w_arg

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
            return

        space = self.space
        
        # Tracing cases
        if event == 'call':
            w_callback = self.w_tracefunc
        else:
            w_callback = frame.w_f_trace

        if w_callback is not None and event != "leaveframe":
            if operr is not None:
                w_arg =  space.newtuple([operr.w_type, operr.w_value,
                                     space.wrap(operr.application_traceback)])

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
            if event not in ['leaveframe', 'call']:
                return

            last_exception = None
            if event == 'leaveframe':
                last_exception = frame.last_exception
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

    def _freeze_(self):
        raise Exception("ExecutionContext instances should not be seen during"
                        " translation.  Now is a good time to inspect the"
                        " traceback and see where this one comes from :-)")


class AbstractActionFlag:
    """This holds the global 'action flag'.  It is a single bitfield
    integer, with bits corresponding to AsyncAction objects that need to
    be immediately triggered.  The correspondance from bits to
    AsyncAction instances is built at translation time.  We can quickly
    check if there is anything at all to do by checking if any of the
    relevant bits is set.  If threads are enabled, they consume the 20
    lower bits to hold a counter incremented at each bytecode, to know
    when to release the GIL.
    """
    def __init__(self):
        self._periodic_actions = []
        self._nonperiodic_actions = []
        self.unused_bits = self.FREE_BITS[:]
        self.has_bytecode_counter = False
        self.interesting_bits = 0
        self._rebuild_action_dispatcher()

    def fire(self, action):
        """Request for the action to be run before the next opcode.
        The action must have been registered at space initalization time."""
        ticker = self.get()
        self.set(ticker | action.bitmask)

    def register_action(self, action):
        "NOT_RPYTHON"
        assert isinstance(action, AsyncAction)
        if action.bitmask == 0:
            while True:
                action.bitmask = self.unused_bits.pop(0)
                if not (action.bitmask & self.interesting_bits):
                    break
        self.interesting_bits |= action.bitmask
        if action.bitmask & self.BYTECODE_COUNTER_OVERFLOW_BIT:
            assert action.bitmask == self.BYTECODE_COUNTER_OVERFLOW_BIT
            self._periodic_actions.append(action)
            self.has_bytecode_counter = True
            self.force_tick_counter()
        else:
            self._nonperiodic_actions.append((action, action.bitmask))
        self._rebuild_action_dispatcher()

    def setcheckinterval(self, space, interval):
        if interval < self.CHECK_INTERVAL_MIN:
            interval = self.CHECK_INTERVAL_MIN
        elif interval > self.CHECK_INTERVAL_MAX:
            interval = self.CHECK_INTERVAL_MAX
        space.sys.checkinterval = interval
        self.force_tick_counter()

    def force_tick_counter(self):
        # force the tick counter to a valid value -- this actually forces
        # it to reach BYTECODE_COUNTER_OVERFLOW_BIT at the next opcode.
        ticker = self.get()
        ticker &= ~ self.BYTECODE_COUNTER_OVERFLOW_BIT
        ticker |= self.BYTECODE_COUNTER_MASK
        self.set(ticker)

    def _rebuild_action_dispatcher(self):
        periodic_actions = unrolling_iterable(self._periodic_actions)
        nonperiodic_actions = unrolling_iterable(self._nonperiodic_actions)
        has_bytecode_counter = self.has_bytecode_counter

        def action_dispatcher(ec):
            # periodic actions
            if has_bytecode_counter:
                ticker = self.get()
                if ticker & self.BYTECODE_COUNTER_OVERFLOW_BIT:
                    # We must run the periodic actions now, but first
                    # reset the bytecode counter (the following line
                    # works by assuming that we just overflowed the
                    # counter, i.e. BYTECODE_COUNTER_OVERFLOW_BIT is
                    # set but none of the BYTECODE_COUNTER_MASK bits
                    # are).
                    ticker -= ec.space.sys.checkinterval
                    self.set(ticker)
                    for action in periodic_actions:
                        action.perform(ec)

            # nonperiodic actions
            for action, bitmask in nonperiodic_actions:
                ticker = self.get()
                if ticker & bitmask:
                    self.set(ticker & ~ bitmask)
                    action.perform(ec)

        action_dispatcher._dont_inline_ = True
        self.action_dispatcher = action_dispatcher

    # Bits reserved for the bytecode counter, if used
    BYTECODE_COUNTER_MASK = (1 << 20) - 1
    BYTECODE_COUNTER_OVERFLOW_BIT = (1 << 20)

    # Free bits
    FREE_BITS = [1 << _b for _b in range(21, LONG_BIT-1)]

    # The acceptable range of values for sys.checkinterval, so that
    # the bytecode_counter fits in 20 bits
    CHECK_INTERVAL_MIN = 1
    CHECK_INTERVAL_MAX = BYTECODE_COUNTER_OVERFLOW_BIT


class ActionFlag(AbstractActionFlag):
    """The normal class for space.actionflag.  The signal module provides
    a different one."""
    _flags = 0

    def get(self):
        return self._flags

    def set(self, value):
        self._flags = value


class AsyncAction(object):
    """Abstract base class for actions that must be performed
    asynchronously with regular bytecode execution, but that still need
    to occur between two opcodes, not at a completely random time.
    """
    bitmask = 0      # means 'please choose one bit automatically'

    def __init__(self, space):
        self.space = space

    def fire(self):
        """Request for the action to be run before the next opcode.
        The action must have been registered at space initalization time."""
        self.space.actionflag.fire(self)

    def fire_after_thread_switch(self):
        """Bit of a hack: fire() the action but only the next time the GIL
        is released and re-acquired (i.e. after a portential thread switch).
        Don't call this if threads are not enabled.
        """
        from pypy.module.thread.gil import spacestate
        spacestate.set_actionflag_bit_after_thread_switch |= self.bitmask

    def perform(self, executioncontext):
        """To be overridden."""


class PeriodicAsyncAction(AsyncAction):
    """Abstract base class for actions that occur automatically
    every sys.checkinterval bytecodes.
    """
    bitmask = ActionFlag.BYTECODE_COUNTER_OVERFLOW_BIT


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
        self.finalizers_lock_count = 0

    def register_dying_object(self, w_obj):
        self.dying_objects_w.append(w_obj)
        self.fire()

    def perform(self, executioncontext):
        if self.finalizers_lock_count > 0:
            return
        # Each call to perform() first grabs the self.dying_objects_w
        # and replaces it with an empty list.  We do this to try to
        # avoid too deep recursions of the kind of __del__ being called
        # while in the middle of another __del__ call.
        pending_w = self.dying_objects_w
        self.dying_objects_w = []
        space = self.space
        for w_obj in pending_w:
            try:
                space.userdel(w_obj)
            except OperationError, e:
                e.write_unraisable(space, 'method __del__ of ', w_obj)
                e.clear(space)   # break up reference cycles
            # finally, this calls the interp-level destructor for the
            # cases where there is both an app-level and a built-in __del__.
            w_obj._call_builtin_destructor()


class FrameTraceAction(AsyncAction):
    """An action that calls the local trace functions (w_f_trace)."""

    def perform(self, executioncontext):
        frame = executioncontext.framestack.top()
        if frame.w_f_trace is None or executioncontext.is_tracing:
            return
        code = frame.pycode
        if frame.instr_lb <= frame.last_instr < frame.instr_ub:
            if frame.last_instr <= frame.instr_prev:
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

        frame.instr_prev = frame.last_instr
        self.space.frame_trace_action.fire()     # continue tracing
