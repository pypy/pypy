""" PyFrame class implementation with the interpreter main loop.
"""

from pypy.interpreter import eval, baseobjspace, gateway
from pypy.interpreter.miscutils import Stack
from pypy.interpreter.error import OperationError
from pypy.interpreter import pytraceback


class PyFrame(eval.Frame):
    """Represents a frame for a regular Python function
    that needs to be interpreted.

    See also pyopcode.PyStandardFrame and pynestedscope.PyNestedScopeFrame.

    Public fields:
     * 'space' is the object space this frame is running in
     * 'code' is the PyCode object this frame runs
     * 'w_locals' is the locals dictionary to use
     * 'w_globals' is the attached globals dictionary
     * 'w_builtins' is the attached built-ins dictionary
     * 'valuestack', 'blockstack', 'next_instr' control the interpretation
    """

    def __init__(self, space, code, w_globals, closure):
        eval.Frame.__init__(self, space, code, w_globals, code.co_nlocals)
        self.valuestack = Stack()
        self.blockstack = Stack()
        self.last_exception = None
        self.next_instr = 0
        self.w_builtins = self.space.w_builtins
        # regular functions always have CO_OPTIMIZED and CO_NEWLOCALS.
        # class bodies only have CO_NEWLOCALS.
        if code.dictscope_needed():
            self.w_locals = space.newdict([])  # set to None by Frame.__init__

    def getclosure(self):
        return None

    def eval(self, executioncontext):
        "Interpreter main loop!"
        try:
            while True:
                executioncontext.bytecode_trace(self)
                last_instr = self.next_instr
                try:
                    try:
                        # fetch and dispatch the next opcode
                        # dispatch() is abstract, see pyopcode.
                        self.dispatch()
                    except OperationError, e:
                        pytraceback.record_application_traceback(
                            self.space, e, self, last_instr)
                        executioncontext.exception_trace(e)
                        # convert an OperationError into a control flow
                        # exception
                        import sys
                        tb = sys.exc_info()[2]
                        raise SApplicationException(e, tb)
                    # XXX some other exceptions could be caught here too,
                    #     like KeyboardInterrupt

                except ControlFlowException, ctlflowexc:
                    # we have a reason to change the control flow
                    # (typically unroll the stack)
                    ctlflowexc.action(self, last_instr, executioncontext)
            
        except ExitFrame, e:
            # leave that frame
            w_exitvalue = e.args[0]
            return w_exitvalue

    ### exception stack ###

    def clean_exceptionstack(self):
        # remove all exceptions that can no longer be re-raised
        # because the current valuestack is no longer deep enough
        # to hold the corresponding information
        while self.exceptionstack:
            ctlflowexc, valuestackdepth = self.exceptionstack.top()
            if valuestackdepth <= self.valuestack.depth():
                break
            self.exceptionstack.pop()

    ### line numbers ###

    def fget_f_lineno(space, w_self):
        "Returns the line number of the instruction currently being executed."
        self = space.unwrap_builtin(w_self)
        return space.wrap(self.get_last_lineno())

    def get_last_lineno(self):
        "Returns the line number of the instruction currently being executed."
        return pytraceback.offset2lineno(self.code, self.next_instr-1)

    def get_next_lineno(self):
        "Returns the line number of the next instruction to execute."
        return pytraceback.offset2lineno(self.code, self.next_instr)


### Frame Blocks ###

class FrameBlock:

    """Abstract base class for frame blocks from the blockstack,
    used by the SETUP_XXX and POP_BLOCK opcodes."""

    def __init__(self, frame, handlerposition):
        self.handlerposition = handlerposition
        self.valuestackdepth = frame.valuestack.depth()

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.handlerposition == other.handlerposition and
                self.valuestackdepth == other.valuestackdepth)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.handlerposition, self.valuestackdepth))

    def cleanupstack(self, frame):
        for i in range(self.valuestackdepth, frame.valuestack.depth()):
            frame.valuestack.pop()

    def cleanup(self, frame):
        "Clean up a frame when we normally exit the block."
        self.cleanupstack(frame)

    def unroll(self, frame, unroller):
        "Clean up a frame when we abnormally exit the block."
        self.cleanupstack(frame)
        return False  # continue to unroll


class LoopBlock(FrameBlock):
    """A loop block.  Stores the end-of-loop pointer in case of 'break'."""

    def unroll(self, frame, unroller):
        if isinstance(unroller, SContinueLoop):
            # re-push the loop block without cleaning up the value stack,
            # and jump to the beginning of the loop, stored in the
            # exception's argument
            frame.blockstack.push(self)
            jump_to = unroller.args[0]
            frame.next_instr = jump_to
            return True  # stop unrolling
        self.cleanupstack(frame)
        if isinstance(unroller, SBreakLoop):
            # jump to the end of the loop
            frame.next_instr = self.handlerposition
            return True  # stop unrolling
        return False


class ExceptBlock(FrameBlock):
    """An try:except: block.  Stores the position of the exception handler."""

    def unroll(self, frame, unroller):
        self.cleanupstack(frame)
        if isinstance(unroller, SApplicationException):
            # push the exception to the value stack for inspection by the
            # exception handler (the code after the except:)
            operationerr = unroller.args[0]
            w_type  = operationerr.w_type
            w_value = operationerr.w_value
            w_normalized = normalize_exception(frame.space, w_type, w_value,
                                               frame.space.w_None)
            w_type, w_value, w_tb = frame.space.unpacktuple(w_normalized, 3)
            # save the normalized exception back into the OperationError
            # -- in particular it makes sure that sys.exc_info() etc see
            #    normalized exception.
            operationerr.w_type = w_type
            operationerr.w_value = w_value
            # the stack setup is slightly different than in CPython:
            # instead of the traceback, we store the unroller object,
            # wrapped.
            frame.valuestack.push(frame.space.wrap(unroller))
            frame.valuestack.push(w_value)
            frame.valuestack.push(w_type)
            frame.next_instr = self.handlerposition   # jump to the handler
            return True  # stop unrolling
        return False

def app_normalize_exception(etype, value, tb):
    """Normalize an (exc_type, exc_value) pair:
    exc_value will be an exception instance and exc_type its class.
    """
    # mistakes here usually show up as infinite recursion, which is fun.
    while isinstance(etype, tuple):
        etype = etype[0]
    if isinstance(etype, type):
        if not isinstance(value, etype):
            if value is None:
                # raise Type: we assume we have to instantiate Type
                value = etype()
            elif isinstance(value, tuple):
                # raise Type, Tuple: assume Tuple contains the constructor args
                value = etype(*value)
            else:
                # raise Type, X: assume X is the constructor argument
                value = etype(value)
        # raise Type, Instance: let etype be the exact type of value
        etype = value.__class__
    elif type(etype) is str:
        # XXX warn -- deprecated
        if value is not None and type(value) is not str:
            raise TypeError("string exceptions can only have a string value")
    else:
        # raise X: we assume that X is an already-built instance
        if value is not None:
            raise TypeError("instance exception may not have a separate value")
        value = etype
        etype = value.__class__
        # for the sake of language consistency we should not allow
        # things like 'raise 1', but it's probably fine (i.e.
        # not ambiguous) to allow them in the explicit form 'raise int, 1'
        if not hasattr(value, '__dict__') and not hasattr(value, '__slots__'):
            raise TypeError("raising built-in objects can be ambiguous, "
                            "use 'raise type, value' instead")
    return etype, value, tb
normalize_exception = gateway.app2interp(app_normalize_exception)


class FinallyBlock(FrameBlock):
    """A try:finally: block.  Stores the position of the exception handler."""

    def cleanup(self, frame):
        # upon normal entry into the finally: part, the standard Python
        # bytecode pushes a single None for END_FINALLY.  In our case we
        # always push three values into the stack: the wrapped ctlflowexc,
        # the exception value and the exception type (which are all None
        # here).
        self.cleanupstack(frame)
        # one None already pushed by the bytecode
        frame.valuestack.push(frame.space.w_None)
        frame.valuestack.push(frame.space.w_None)

    def unroll(self, frame, unroller):
        # any abnormal reason for unrolling a finally: triggers the end of
        # the block unrolling and the entering the finally: handler.
        # see comments in cleanup().
        self.cleanupstack(frame)
        frame.valuestack.push(frame.space.wrap(unroller))
        frame.valuestack.push(frame.space.w_None)
        frame.valuestack.push(frame.space.w_None)
        frame.next_instr = self.handlerposition   # jump to the handler
        return True  # stop unrolling


### Internal exceptions that change the control flow ###
### and (typically) unroll the block stack           ###

class ControlFlowException(Exception, baseobjspace.BaseWrappable):
    """Abstract base class for interpreter-level exceptions that
    instruct the interpreter to change the control flow and the
    block stack.

    The concrete subclasses correspond to the various values WHY_XXX
    values of the why_code enumeration in ceval.c:

		WHY_NOT,	OK, not this one :-)
		WHY_EXCEPTION,	SApplicationException
		WHY_RERAISE,	we don't think this is needed
		WHY_RETURN,	SReturnValue
		WHY_BREAK,	SBreakLoop
		WHY_CONTINUE,	SContinueLoop
		WHY_YIELD	SYieldValue

    """
    def action(self, frame, last_instr, executioncontext):
        "Default unroller implementation."
        while not frame.blockstack.empty():
            block = frame.blockstack.pop()
            if block.unroll(frame, self):
                break
        else:
            self.emptystack(frame)

    def emptystack(self, frame):
        "Default behavior when the block stack is exhausted."
        # could occur e.g. when a BREAK_LOOP is not actually within a loop
        raise BytecodeCorruption, "block stack exhausted"

    # for the flow object space, a way to "pickle" and "unpickle" the
    # ControlFlowException by enumerating the Variables it contains.
    def state_unpack_variables(self, space):
        return []     # by default, overridden below
    def state_pack_variables(self, space, *values_w):
        assert len(values_w) == 0

class SApplicationException(ControlFlowException):
    """Unroll the stack because of an application-level exception
    (i.e. an OperationException)."""

    def action(self, frame, last_instr, executioncontext):
        e = self.args[0]
        frame.last_exception = e

        ControlFlowException.action(self, frame,
                                    last_instr, executioncontext)

    def emptystack(self, frame):
        # propagate the exception to the caller
        if len(self.args) == 2:
            operationerr, tb = self.args
            raise operationerr.__class__, operationerr, tb
        else:
            operationerr = self.args[0]
            raise operationerr

    def state_unpack_variables(self, space):
        e = self.args[0]
        assert isinstance(e, OperationError)
        return [e.w_type, e.w_value]
    def state_pack_variables(self, space, w_type, w_value):
        self.args = (OperationError(w_type, w_value),)

class SBreakLoop(ControlFlowException):
    """Signals a 'break' statement."""

class SContinueLoop(ControlFlowException):
    """Signals a 'continue' statement.
    Argument is the bytecode position of the beginning of the loop."""

    def state_unpack_variables(self, space):
        jump_to = self.args[0]
        return [space.wrap(jump_to)]
    def state_pack_variables(self, space, w_jump_to):
        self.args = (space.unwrap(w_jump_to),)

class SReturnValue(ControlFlowException):
    """Signals a 'return' statement.
    Argument is the wrapped object to return."""
    def emptystack(self, frame):
        w_returnvalue = self.args[0]
        raise ExitFrame(w_returnvalue)

    def state_unpack_variables(self, space):
        w_returnvalue = self.args[0]
        return [w_returnvalue]
    def state_pack_variables(self, space, w_returnvalue):
        self.args = (w_returnvalue,)

class ExitFrame(Exception):
    """Signals the end of the frame execution.
    The argument is the returned or yielded value, already wrapped."""

class BytecodeCorruption(ValueError):
    """Detected bytecode corruption.  Never caught; it's an error."""
