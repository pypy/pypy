""" PyFrame class implementation with the interpreter main loop.
"""

from pypy.interpreter import eval, baseobjspace, gateway
from pypy.interpreter.miscutils import Stack
from pypy.interpreter.error import OperationError
from pypy.interpreter import pytraceback
import opcode

# Define some opcodes used
g = globals()
for op in '''DUP_TOP POP_TOP SETUP_LOOP SETUP_EXCEPT SETUP_FINALLY
POP_BLOCK END_FINALLY'''.split():
    g[op] = opcode.opmap[op]
HAVE_ARGUMENT = opcode.HAVE_ARGUMENT

import __future__
compiler_flags = 0
for fname in __future__.all_feature_names:
    compiler_flags |= getattr(__future__, fname).compiler_flag


class PyFrame(eval.Frame):
    """Represents a frame for a regular Python function
    that needs to be interpreted.

    See also pyopcode.PyStandardFrame and pynestedscope.PyNestedScopeFrame.

    Public fields:
     * 'space' is the object space this frame is running in
     * 'code' is the PyCode object this frame runs
     * 'w_locals' is the locals dictionary to use
     * 'w_globals' is the attached globals dictionary
     * 'builtin' is the attached built-in module
     * 'valuestack', 'blockstack', 'next_instr' control the interpretation
    """

    def __init__(self, space, code, w_globals, closure):
        eval.Frame.__init__(self, space, code, w_globals, code.co_nlocals)
        self.valuestack = Stack()
        self.blockstack = Stack()
        self.last_exception = None
        self.next_instr = 0
        self.builtin = space.builtin.pick_builtin(w_globals)
        # regular functions always have CO_OPTIMIZED and CO_NEWLOCALS.
        # class bodies only have CO_NEWLOCALS.
        if code.dictscope_needed():
            self.w_locals = space.newdict([])  # set to None by Frame.__init__

        self.fastlocals_w = [None]*self.numlocals
        self.w_f_trace = None
        self.last_instr = -1
        self.f_back = None
        self.f_lineno = self.code.co_firstlineno
        
        # For tracing
        self.instr_lb = 0
        self.instr_ub = -1
        
    def getfastscope(self):
        "Get the fast locals as a list."
        return self.fastlocals_w

    def setfastscope(self, scope_w):
        """Initialize the fast locals from a list of values,
        where the order is according to self.code.signature()."""
        if len(scope_w) > len(self.fastlocals_w):
            raise ValueError, "new fastscope is longer than the allocated area"
        self.fastlocals_w[:len(scope_w)] = scope_w
        
    def getclosure(self):
        return None

    def get_compile_flags(self):
        return self.code.co_flags & compiler_flags

    def eval(self, executioncontext):
        "Interpreter main loop!"
        try:
            executioncontext.call_trace(self)
            self.last_instr = -1
            while True:
                try:
                    try:
                        try:
                            while True:
                                # fetch and dispatch the next opcode
                                # dispatch() is abstract, see pyopcode.
                                self.last_instr = self.next_instr
                                executioncontext.bytecode_trace(self)
                                self.next_instr = self.last_instr
                                self.dispatch()
                        # catch asynchronous exceptions and turn them
                        # into OperationErrors
                        except KeyboardInterrupt:
                            import sys; tb = sys.exc_info()[2]
                            raise OperationError, OperationError(self.space.w_KeyboardInterrupt,
                                                   self.space.w_None), tb
                        except MemoryError:
                            import sys; tb = sys.exc_info()[2]
                            raise OperationError, OperationError(self.space.w_MemoryError,
                                                   self.space.w_None), tb
                        except RuntimeError, e:
                            import sys; tb = sys.exc_info()[2]
                            raise OperationError, OperationError(self.space.w_RuntimeError,
                                self.space.wrap("internal error: " + str(e))), tb

                    except OperationError, e:
                        pytraceback.record_application_traceback(
                            self.space, e, self, self.last_instr)
                        executioncontext.exception_trace(self, e)
                        # convert an OperationError into a control flow
                        # exception
                        raise SApplicationException(e)

                except ControlFlowException, ctlflowexc:
                    # we have a reason to change the control flow
                    # (typically unroll the stack)
                    ctlflowexc.action(self, self.last_instr, executioncontext)
            
        except ExitFrame, e:
            # leave that frame
            w_exitvalue = e.args[0]
            executioncontext.return_trace(self, w_exitvalue)
            return w_exitvalue
        
    ### line numbers ###

    def fget_f_lineno(space, w_self):
        "Returns the line number of the instruction currently being executed."
        self = space.interpclass_w(w_self)
        if self.w_f_trace is None:
            return space.wrap(self.get_last_lineno())
        else:
            return space.wrap(self.f_lineno)

    def fset_f_lineno(space, w_self, w_new_lineno):
        "Returns the line number of the instruction currently being executed."
        try:
            new_lineno = space.int_w(w_new_lineno)
        except OperationError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap("lineno must be an integer"))
            
        self = space.interpclass_w(w_self)
        if self.w_f_trace is None:
            raise OperationError(space.w_ValueError,
                  space.wrap("f_lineo can only be set by a trace function."))

        if new_lineno < self.code.co_firstlineno:
            raise OperationError(space.w_ValueError,
                  space.wrap("line %d comes before the current code." % new_lineno))
        code = self.code.co_code
        addr = 0
        line = self.code.co_firstlineno
        new_lasti = -1
        offset = 0
        lnotab = self.code.co_lnotab
        for offset in xrange(0, len(lnotab), 2):
            addr += ord(lnotab[offset])
            line += ord(lnotab[offset + 1])
            if line >= new_lineno:
                new_lasti = addr
                new_lineno = line
                break

        if new_lasti == -1:
            raise OperationError(space.w_ValueError,
                  space.wrap("line %d comes after the current code." % new_lineno))

        # Don't jump to a line with an except in it.
        if ord(code[new_lasti]) in (DUP_TOP, POP_TOP):
            raise OperationError(space.w_ValueError,
                  space.wrap("can't jump to 'except' line as there's no exception"))
            
        # Don't jump into or out of a finally block.
        f_lasti_setup_addr = -1
        new_lasti_setup_addr = -1
        blockstack = Stack()
        addr = 0
        while addr < len(code):
            op = ord(code[addr])
            if op in (SETUP_LOOP, SETUP_EXCEPT, SETUP_FINALLY):
                blockstack.push([addr, False])
            elif op == POP_BLOCK:
                setup_op = ord(code[blockstack.top()[0]])
                if setup_op == SETUP_FINALLY:
                    blockstack.top()[1] = True
                else:
                    blockstack.pop()
            elif op == END_FINALLY:
                if not blockstack.empty():
                    setup_op = ord(code[blockstack.top()[0]])
                    if setup_op == SETUP_FINALLY:
                        blockstack.pop()

            if addr == new_lasti or addr == self.last_instr:
                for ii in range(blockstack.depth()):
                    setup_addr, in_finally = blockstack.top(ii)
                    if in_finally:
                        if addr == new_lasti:
                            new_lasti_setup_addr = setup_addr
                        if addr == self.last_instr:
                            f_lasti_setup_addr = setup_addr
                        break
                    
            if op >= HAVE_ARGUMENT:
                addr += 3
            else:
                addr += 1
                
        assert blockstack.empty()

        if new_lasti_setup_addr != f_lasti_setup_addr:
            raise OperationError(space.w_ValueError,
                  space.wrap("can't jump into or out of a 'finally' block %d -> %d" %
                             (f_lasti_setup_addr, new_lasti_setup_addr)))

        if new_lasti < self.last_instr:
            min_addr = new_lasti
            max_addr = self.last_instr
        else:
            min_addr = self.last_instr
            max_addr = new_lasti

        delta_iblock = min_delta_iblock = 0
        addr = min_addr
        while addr < max_addr:
            op = ord(code[addr])

            if op in (SETUP_LOOP, SETUP_EXCEPT, SETUP_FINALLY):
                delta_iblock += 1;
            elif op == POP_BLOCK:
                delta_iblock -= 1
                if delta_iblock < min_delta_iblock:
                    min_delta_iblock = delta_iblock

            if op >= opcode.HAVE_ARGUMENT:
                addr += 3
            else:
                addr += 1

        f_iblock = self.blockstack.depth()
        min_iblock = f_iblock + min_delta_iblock
        if new_lasti > self.last_instr:
            new_iblock = f_iblock + delta_iblock
        else:
            new_iblock = f_iblock - delta_iblock

        if new_iblock > min_iblock:
            raise OperationError(space.w_ValueError,
                                 space.wrap("can't jump into the middle of a block"))

        while f_iblock > new_iblock:
            block = self.blockstack.pop()
            block.cleanup(self)
            f_iblock -= 1
            
        self.f_lineno = new_lineno
        self.last_instr = new_lasti
            
    def get_last_lineno(self):
        "Returns the line number of the instruction currently being executed."
        return pytraceback.offset2lineno(self.code, self.next_instr-1)

    def get_next_lineno(self):
        "Returns the line number of the next instruction to execute."
        return pytraceback.offset2lineno(self.code, self.next_instr)

    def fget_f_builtins(space, w_self):
        self = space.interpclass_w(w_self)
        return self.builtin.getdict()

    def fget_f_back(space, w_self):
        self = space.interpclass_w(w_self)
        return self.space.wrap(self.f_back)

    def fget_f_lasti(space, w_self):
        self = space.interpclass_w(w_self)
        return self.space.wrap(self.last_instr)

    def fget_f_trace(space, w_self):
        self = space.interpclass_w(w_self)
        return self.w_f_trace

    def fset_f_trace(space, w_self, w_trace):
        self = space.interpclass_w(w_self)
        if space.is_true(space.is_(w_trace, space.w_None)):
            self.w_f_trace = None
        else:
            self.w_f_trace = w_trace
            self.f_lineno = self.get_last_lineno()

    def fget_f_exc_type(space, w_self):
        self = space.interpclass_w(w_self)
        if self.last_exception is not None:
            f = self.f_back
            while f is not None and f.last_exception is None:
                f = f_back
            if f is not None:
                return f.last_exception.w_type
        return space.w_None
         
    def fget_f_exc_value(space, w_self):
        self = space.interpclass_w(w_self)
        if self.last_exception is not None:
            f = self.f_back
            while f is not None and f.last_exception is None:
                f = f_back
            if f is not None:
                return f.last_exception.w_value
        return space.w_None

    def fget_f_exc_traceback(space, w_self):
        self = space.interpclass_w(w_self)
        if self.last_exception is not None:
            f = self.f_back
            while f is not None and f.last_exception is None:
                f = f_back
            if f is not None:
                return space.wrap(f.last_exception.application_traceback)
        return space.w_None
         
    def fget_f_restricted(space, w_self):
        self = space.interpclass_w(w_self)
        return space.wrap(self.builtin is not space.builtin)

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

app = gateway.applevel('''
    def normalize_exception(etype, value, tb):
        """Normalize an (exc_type, exc_value) pair:
        exc_value will be an exception instance and exc_type its class.
        """
        # mistakes here usually show up as infinite recursion, which is fun.
        while isinstance(etype, tuple):
            etype = etype[0]
        if isinstance(etype, (type, _classobj)):
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
            # things like 'raise 1', but it is probably fine (i.e.
            # not ambiguous) to allow them in the explicit form 'raise int, 1'
            if not hasattr(value, '__dict__') and not hasattr(value, '__slots__'):
                raise TypeError("raising built-in objects can be ambiguous, "
                                "use 'raise type, value' instead")
        return etype, value, tb
''')
normalize_exception = app.interphook("normalize_exception")


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

                WHY_NOT,        OK, not this one :-)
                WHY_EXCEPTION,  SApplicationException
                WHY_RERAISE,    we don't think this is needed
                WHY_RETURN,     SReturnValue
                WHY_BREAK,      SBreakLoop
                WHY_CONTINUE,   SContinueLoop
                WHY_YIELD       SYieldValue

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
        self.args = (space.int_w(w_jump_to),)

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
