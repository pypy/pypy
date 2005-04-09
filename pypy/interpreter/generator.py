from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.eval import Frame
from pypy.interpreter.pyframe import ControlFlowException, ExitFrame

#
# Generator support. Note that GeneratorFrame is not a subclass of PyFrame.
# PyCode objects use a custom subclass of both PyFrame and GeneratorFrame
# when they need to interpret Python bytecode that is a generator.
# Otherwise, GeneratorFrame could also be used to define, say,
# built-in generators (which are usually done in CPython as functions
# that return iterators).
#

class GeneratorFrame(Frame):
    "A frame attached to a generator."

    def run(self):
        "Build a generator-iterator."
        return self.space.wrap(GeneratorIterator(self))

    ### extra opcodes ###

    # XXX mmmh, GeneratorFrame is supposed to be independent from
    # Python bytecode... Well, it is. These are not used when
    # GeneratorFrame is used with other kinds of Code subclasses.

    def RETURN_VALUE(f):  # overridden
        raise SGeneratorReturn()

    def YIELD_VALUE(f):
        w_yieldedvalue = f.valuestack.pop()
        raise SYieldValue(w_yieldedvalue)
    YIELD_STMT = YIELD_VALUE  # misnamed in old versions of dis.opname


class GeneratorIterator(Wrappable):
    "An iterator created by a generator."
    
    def __init__(self, frame):
        self.space = frame.space
        self.frame = frame
        self.running = False
        self.exhausted = False

    def descr__iter__(self):
        return self.space.wrap(self)

    def descr_next(self):
        space = self.space
        if self.running:
            raise OperationError(space.w_ValueError,
                                 space.wrap('generator already executing'))
        if self.exhausted:
            raise OperationError(space.w_StopIteration, space.w_None) 
        self.running = True
        try:
            try:
                return self.frame.resume()
            except OperationError:
                self.exhausted = True
                raise
        finally:
            self.running = False

#
# the specific ControlFlowExceptions used by generators
#

class SYieldValue(ControlFlowException):
    """Signals a 'yield' statement.
    Argument is the wrapped object to return."""

    def __init__(self, w_yieldvalue):
        self.w_yieldvalue = w_yieldvalue

    def action(self, frame, last_instr, executioncontext):
        raise ExitFrame(self.w_yieldvalue)

class SGeneratorReturn(ControlFlowException):
    """Signals a 'return' statement inside a generator."""
    def emptystack(self, frame):
        raise OperationError(frame.space.w_StopIteration, frame.space.w_None) 
