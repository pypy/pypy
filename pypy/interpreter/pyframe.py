""" PyFrame class implementation with the interpreter main loop.
"""

from pypy.interpreter.executioncontext import OperationError, Stack, NoValue
from pypy.interpreter.appfile import AppFile

appfile = AppFile(__name__, ["interpreter"])


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
        self.bytecode = bytecode # Misnomer; this is really like a code object
        self.w_globals = w_globals
        self.w_locals = w_locals
        self.localcells, self.nestedcells = bytecode.locals2cells(space,
                                                                  w_locals)
        self.w_builtins = self.load_builtins()
        self.valuestack = Stack()
        self.blockstack = Stack()
        self.last_exception = None
        self.next_instr = 0

    def eval(self, executioncontext):
        "Interpreter main loop!"
        from pypy.interpreter import opcode
        try:
            while True:
                try:
                    executioncontext.bytecode_trace(self)
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
                        # convert an OperationError into a control flow
                        # exception
                        raise SApplicationException(e)
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

    def fast2locals(self):
        # Copy values from self.localcells to self.w_locals
        for i in range(len(self.localcells)):
            name = self.bytecode.co_varnames[i]
            cell = self.localcells[i]
            w_name = self.space.wrap(name)
            try:
                w_value = cell.get()
            except ValueError:
                pass
            else:
                self.space.setitem(self.w_locals, w_name, w_value)

    def locals2fast(self):
        # Copy values from self.w_locals to self.localcells
        for i in range(self.bytecode.co_nlocals):
            name = self.bytecode.co_varnames[i]
            cell = self.localcells[i]
            w_name = self.space.wrap(name)
            try:
                w_value = self.space.getitem(self.w_locals, w_name)
            except OperationError, e:
                if not e.match(self.space, self.space.w_KeyError):
                    raise
                else:
                    pass
            else:
                cell.set(w_value)

    ### frame initialization ###

    def load_builtins(self):
        # compute w_builtins.  This cannot be done in the '.app.py'
        # file for bootstrapping reasons.
        w_builtinsname = self.space.wrap("__builtins__")
        try:
            w_builtins = self.space.getitem(self.w_globals, w_builtinsname)
        except OperationError, e:
            if not e.match(self.space, self.space.w_KeyError):
                raise
            w_builtins = self.space.w_builtins  # fall-back for bootstrapping
        # w_builtins can be a module object or a dictionary object.
        # In frameobject.c we explicitely check if w_builtins is a module
        # object.  Here we will just try to read its __dict__ attribute and
        # if it fails we assume that it was a dictionary in the first place.
        w_attrname = self.space.wrap("__dict__")
        # XXX Commented out the following; it doesn't work for Ann space,
        # and doesn't seem to be needed for other spaces AFAICT.
##        try:
##            w_builtins = self.space.getattr(w_builtins, w_attrname)
##        except OperationError:
##            pass # XXX catch and ignore any error
        return w_builtins

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

            s = frame.space
            w_value = operationerr.w_value
            w_type = operationerr.w_type
##             import pdb
##             pdb.set_trace()
##             print w_type, `w_value`, frame.bytecode.co_name
            w_res = s.gethelper(appfile).call(
                "normalize_exception", [w_type, w_value])
            w_value = s.getitem(w_res, s.wrap(1))
            
            frame.valuestack.push(w_value)
            frame.valuestack.push(w_type)
            frame.next_instr = self.handlerposition   # jump to the handler
            raise StopUnrolling


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
        raise StopUnrolling


### Internal exceptions that change the control flow ###
### and (typically) unroll the block stack           ###

class ControlFlowException(Exception):
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

class SApplicationException(ControlFlowException):
    """Unroll the stack because of an application-level exception
    (i.e. an OperationException)."""
    def emptystack(self, frame):
        # propagate the exception to the caller
        operationerr = self.args[0]
        raise operationerr

class SBreakLoop(ControlFlowException):
    """Signals a 'break' statement."""

class SContinueLoop(ControlFlowException):
    """Signals a 'continue' statement.
    Argument is the bytecode position of the beginning of the loop."""

class SReturnValue(ControlFlowException):
    """Signals a 'return' statement.
    Argument is the wrapped object to return."""
    def emptystack(self, frame):
        if frame.bytecode.co_flags & 0x0020:#CO_GENERATOR:
            raise NoValue
        w_returnvalue = self.args[0]
        raise ExitFrame(w_returnvalue)

class SYieldValue(ControlFlowException):
    """Signals a 'yield' statement.
    Argument is the wrapped object to return."""
    def action(self, frame, last_instr, executioncontext):
        w_returnvalue = self.args[0]
        raise ExitFrame(w_returnvalue)

class StopUnrolling(Exception):
    "Signals the end of the block stack unrolling."

class ExitFrame(Exception):
    """Signals the end of the frame execution.
    The argument is the returned or yielded value, already wrapped."""

class BytecodeCorruption(ValueError):
    """Detected bytecode corruption.  Never caught; it's an error."""


## Cells ##

_NULL = object() # Marker object

class Cell:
    def __init__(self, w_value=_NULL):
        self.w_value = w_value

    def get(self):
        if self.w_value is _NULL:
            raise ValueError, "get() from an empty cell"
        return self.w_value

    def set(self, w_value):
        self.w_value = w_value

    def delete(self):
        if self.w_value is _NULL:
            raise ValueError, "make_empty() on an empty cell"
        self.w_value = _NULL

    def __repr__(self):
        """ representation for debugging purposes """
        if self.w_value is _NULL:
            return "%s()" % self.__class__.__name__
        else:
            return "%s(%s)" % (self.__class__.__name__, self.w_value)

