""" PyFrame class implementation with the interpreter main loop.
"""
import opcode
# XXX this is probably a Python bug:
# circular import doesn't work if we spell this
# from pypy.interpreter import opcode
# report this to python-dev
from executioncontext import OperationError, Stack
import baseobjspace
from appfile import AppFile

appfile = AppFile(__name__, ["interpreter"])

CO_VARARGS     = 0x0004
CO_VARKEYWORDS = 0x0008


class PyFrame:
    """Represents a frame for a regular Python function
    that needs to be interpreted.

    Public fields:
     * 'space' is the object space this frame is running in
     * 'w_locals' is the locals dictionary to use
     * 'w_globals' is the attached globals dictionary
     * 'w_builtins' is the attached built-ins dictionary
     * 'valuestack', 'blockstack', 'next_instr' control the interpretation
    """

    def __init__(self, space, bytecode, w_globals, w_locals):
        self.space = space
        self.bytecode = bytecode
        self.w_globals = w_globals
        self.w_locals = w_locals
        self.load_builtins()
        self.valuestack = Stack()
        self.blockstack = Stack()
        self.last_exception = None
        self.next_instr = 0

    def eval(self, executioncontext):
        "Interpreter main loop!"
        try:
            while True:
                try:
                    last_instr = self.next_instr
                    try:
                        # fetch and dispatch the next opcode
                        op = self.nextop()
                        if opcode.has_arg(op):
                            oparg = self.nextarg()
                            opcode.dispatch_arg(self, op, oparg)
                        else:
                            opcode.dispatch_noarg(self, op)

                    except OperationError, e:
                        e.record_application_traceback(self, last_instr)
                        self.last_exception = e
                        executioncontext.exception_trace(e)
                        # convert an OperationError into a reason to unroll
                        # the stack
                        raise SApplicationException(e)
                    # XXX some other exceptions could be caught here too,
                    #     like KeyboardInterrupt

                except StackUnroller, unroller:
                    # we have a reason to unroll the stack
                    unroller.unrollstack(self)
            
        except ExitFrame, e:
            # leave that frame
            w_exitvalue = e.args[0]
            return w_exitvalue

    ### accessor functions ###

    def nextop(self):
        c = self.bytecode.co_code[self.next_instr]
        self.next_instr += 1
        return ord(c)

    def nextarg(self):
        lo = self.nextop()
        hi = self.nextop()
        return (hi<<8) + lo

    def getconstant(self, index):
        return self.bytecode.co_consts[index]

    def getlocalvarname(self, index):
        return self.bytecode.co_varnames[index]

    def getname(self, index):
        return self.bytecode.co_names[index]

    def getfreevarname(self, index):
        freevarnames = self.bytecode.co_cellvars + self.bytecode.co_freevars
        return freevarnames[index]

    def iscellvar(self, index):
        # is the variable given by index a cell or a free var?
        return index < len(self.bytecode.co_cellvars)

    ### frame initialization ###

    def setargs(self, w_arguments, w_kwargs=None,
                w_defaults=None, w_closure=None):
        "Initialize the frame with the given arguments tuple."
        arguments = self.decode_arguments(w_arguments, w_kwargs,
                                          w_defaults, w_closure)
        for i in range(len(arguments)):
            varname = self.getlocalvarname(i)
            w_varname = self.space.wrap(varname)
            w_arg = arguments[i]
            self.space.setitem(self.w_locals, w_varname, w_arg)

    def decode_arguments(self, w_arguments, w_kwargs, w_defaults, w_closure):
        # We cannot systematically go to the application-level (_app.py)
        # to do this dirty work, for bootstrapping reasons.  So we check
        # if we are in the most simple case and if so do not go to the
        # application-level at all.
        co = self.bytecode
        if (co.co_flags & (CO_VARARGS|CO_VARKEYWORDS) == 0 and
            (w_defaults is None or not self.space.is_true(w_defaults)) and
            (w_kwargs   is None or not self.space.is_true(w_kwargs))   and
            (w_closure  is None or not self.space.is_true(w_closure))):
            # looks like a simple case, see if we got exactly the correct
            # number of arguments
            try:
                args = self.space.unpacktuple(w_arguments, co.co_argcount)
            except ValueError:
                pass  # no
            else:
                return args   # yes! fine!
        # non-trivial case.  I won't do it myself.
        if w_kwargs   is None: w_kwargs   = self.space.newdict([])
        if w_defaults is None: w_defaults = self.space.newtuple([])
        if w_closure  is None: w_closure  = self.space.newtuple([])
        w_bytecode = self.space.wrap(co)
        w_arguments = self.space.gethelper(appfile).call(
            "decode_frame_arguments", [w_arguments, w_kwargs, w_defaults,
                                       w_closure, w_bytecode])
        # we assume that decode_frame_arguments() gives us a tuple
        # of the correct length.
        return self.space.unpacktuple(w_arguments)

    def load_builtins(self):
        # initialize self.w_builtins.  This cannot be done in the '.app.py'
        # file for bootstrapping reasons.
        w_builtinsname = self.space.wrap("__builtins__")
        w_builtins = self.space.getitem(self.w_globals, w_builtinsname)
        # w_builtins can be a module object or a dictionary object.
        # In frameobject.c we explicitely check if w_builtins is a module
        # object.  Here we will just try to read its __dict__ attribute and
        # if it fails we assume that it was a dictionary in the first place.
        w_attrname = self.space.wrap("__dict__")
        try:
            w_builtins = self.space.getattr(w_builtins, w_attrname)
        except OperationError:
            pass # catch and ignore any error
        self.w_builtins = w_builtins

    ### exception stack ###

    def clean_exceptionstack(self):
        # remove all exceptions that can no longer be re-raised
        # because the current valuestack is no longer deep enough
        # to hold the corresponding information
        while self.exceptionstack:
            unroller, valuestackdepth = self.exceptionstack.top()
            if valuestackdepth <= self.valuestack.depth():
                break
            self.exceptionstack.pop()


### Frame Blocks ###

class FrameBlock:

    """Abstract base class for frame blocks from the blockstack,
    used by the SETUP_XXX and POP_BLOCK opcodes."""

    def __init__(self, frame, handlerposition):
        self.handlerposition = handlerposition
        self.valuestackdepth = frame.valuestack.depth()

    def cleanupstack(self, frame):
        for i in range(self.valuestackdepth, frame.valuestack.depth()):
            frame.valuestack.pop()

    def cleanup(self, frame):
        "Clean up a frame when we normally exit the block."
        self.cleanupstack(frame)

    def unroll(self, frame, unroller):
        "Clean up a frame when we abnormally exit the block."
        self.cleanupstack(frame)


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
            raise StopUnrolling
        self.cleanupstack(frame)
        if isinstance(unroller, SBreakLoop):
            # jump to the end of the loop
            frame.next_instr = self.handlerposition
            raise StopUnrolling


class ExceptBlock(FrameBlock):
    """An try:except: block.  Stores the position of the exception handler."""

    def unroll(self, frame, unroller):
        self.cleanupstack(frame)
        if isinstance(unroller, SApplicationException):
            # push the exception to the value stack for inspection by the
            # exception handler (the code after the except:)
            operationerr = unroller.args[0]
            # the stack setup is slightly different than in CPython:
            # instead of the traceback, we store the unroller object,
            # wrapped.
            frame.valuestack.push(frame.space.wrap(unroller))
            frame.valuestack.push(operationerr.w_value)
            frame.valuestack.push(operationerr.w_type)
            frame.next_instr = self.handlerposition   # jump to the handler
            raise StopUnrolling


class FinallyBlock(FrameBlock):
    """A try:finally: block.  Stores the position of the exception handler."""

    def cleanup(self, frame):
        # upon normal entry into the finally: part, the standard Python
        # bytecode pushes a single None for END_FINALLY.  In our case we
        # always push three values into the stack: the wrapped unroller,
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
        raise StopUnrolling


### Block Stack unrollers ###

class StackUnroller(Exception):
    """Abstract base class for interpreter-level exceptions that unroll the
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
    def unrollstack(self, frame):
        "Default unroller implementation."
        try:
            while not frame.blockstack.empty():
                block = frame.blockstack.pop()
                block.unroll(frame, self)
            self.emptystack(frame)
        except StopUnrolling:
            pass

    def emptystack(self, frame):
        "Default behavior when the block stack is exhausted."
        # could occur e.g. when a BREAK_LOOP is not actually within a loop
        raise BytecodeCorruption, "block stack exhausted"

class SApplicationException(StackUnroller):
    """Unroll the stack because of an application-level exception
    (i.e. an OperationException)."""
    def emptystack(self, frame):
        # propagate the exception to the caller
        operationerr = self.args[0]
        raise operationerr

class SBreakLoop(StackUnroller):
    """Signals a 'break' statement."""

class SContinueLoop(StackUnroller):
    """Signals a 'continue' statement.
    Argument is the bytecode position of the beginning of the loop."""

class SReturnValue(StackUnroller):
    """Signals a 'return' statement.
    Argument is the wrapped object to return."""
    def emptystack(self, frame):
        # XXX do something about generators, like throw a NoValue
        w_returnvalue = self.args[0]
        raise ExitFrame(w_returnvalue)

class SYieldValue(StackUnroller):
    """Signals a 'yield' statement.
    Argument is the wrapped object to return."""
    def unrollstack(self, frame):
        w_yieldedvalue = self.args[0]
        raise ExitFrame(w_yieldedvalue)

class StopUnrolling(Exception):
    "Signals the end of the block stack unrolling."

class ExitFrame(Exception):
    """Signals the end of the frame execution.
    The argument is the returned or yielded value."""

class BytecodeCorruption(ValueError):
    """Detected bytecode corruption.  Never caught; it's an error."""
