from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import NoValue
from pypy.interpreter.eval import Frame
from pypy.interpreter.pyframe import ControlFlowException, ExitFrame
from pypy.interpreter import function, gateway

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
        self.exhausted = False
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


class GeneratorIterator(object):
    "An iterator created by a generator."
    
    def __init__(self, frame):
        self.space = frame.space
        self.frame = frame
        self.running = False

    def pypy_iter(self):
        return self.space.wrap(self)

    def pypy_next(self):
        # raise NoValue when exhausted
        if self.running:
            space = self.frame.space
            raise OperationError(space.w_ValueError,
                                 space.wrap('generator already executing'))
        if self.frame.exhausted:
            raise NoValue
        self.running = True
        try:
            try: return Frame.run(self.frame)
            except OperationError, e:
                if e.w_type is self.space.w_StopIteration:
                    raise NoValue
                else:
                    raise
        finally:
            self.running = False

    def next(self):
        try:
            return self.pypy_next()
        except NoValue:
            raise OperationError(self.space.w_StopIteration,
                                 self.space.w_None)
    app_next = gateway.interp2app(next)

    def pypy_getattr(self, w_attr):
        # XXX boilerplate that should disappear at some point
        attr = self.space.unwrap(w_attr)
        if attr == 'next':
            return self.space.wrap(self.app_next)
        raise OperationError(self.space.w_AttributeError, w_attr)

    # XXX the following is for TrivialObjSpace only, when iteration is
    # done by C code (e.g. when calling 'list(g())').
    def __iter__(self):
        class hack:
            def next(h):
                try:
                    return self.pypy_next()
                except NoValue:
                    raise StopIteration
        return hack()

#
# the specific ControlFlowExceptions used by generators
#

class SYieldValue(ControlFlowException):
    """Signals a 'yield' statement.
    Argument is the wrapped object to return."""
    def action(self, frame, last_instr, executioncontext):
        w_yieldvalue = self.args[0]
        raise ExitFrame(w_yieldvalue)

class SGeneratorReturn(ControlFlowException):
    """Signals a 'return' statement inside a generator."""
    def emptystack(self, frame):
        frame.exhausted = True
        raise NoValue
