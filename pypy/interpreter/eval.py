"""
This module defines the abstract base classes that support execution:
Code and Frame.
"""
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable


class Code(Wrappable):
    """A code is a compiled version of some source code.
    Abstract base class."""

    def __init__(self, co_name):
        self.co_name = co_name

    def create_frame(self, space, w_globals, closure=None):
        "Create an empty frame object suitable for evaluation of this code."
        raise TypeError, "abstract"

    def exec_code(self, space, w_globals, w_locals):
        "Implements the 'exec' statement."
        frame = self.create_frame(space, w_globals)
        frame.setdictscope(w_locals)
        return frame.run()

    def signature(self):
        "([list-of-arg-names], vararg-name-or-None, kwarg-name-or-None)."
        return [], None, None

    def getvarnames(self):
        """List of names including the arguments, vararg and kwarg,
        and possibly more locals."""
        argnames, varargname, kwargname = self.signature()
        if varargname is not None:
            argnames = argnames + [varargname]
        if kwargname is not None:
            argnames = argnames + [kwargname]
        return argnames

    def getformalargcount(self):
        argnames, varargname, kwargname = self.signature()
        argcount = len(argnames)
        if varargname is not None:
            argcount += 1
        if kwargname is not None:
            argcount += 1
        return argcount

    def getdocstring(self):
        return None

class UndefinedClass(object):
    pass
UNDEFINED = UndefinedClass()  # marker for undefined local variables


class Frame(Wrappable):
    """A frame is an environment supporting the execution of a code object.
    Abstract base class."""

    def __init__(self, space, code, w_globals=None, numlocals=-1):
        self.space      = space
        self.code       = code       # Code instance
        self.w_globals  = w_globals  # wrapped dict of globals
        self.w_locals   = None       # wrapped dict of locals
        if numlocals < 0:  # compute the minimal size based on arguments
            numlocals = len(code.getvarnames())
        self.numlocals = numlocals

    def resume(self):
        "Resume the execution of the frame from its current state."
        executioncontext = self.space.getexecutioncontext()
        previous = executioncontext.enter(self)
        try:
            result = self.eval(executioncontext)
        finally:
            executioncontext.leave(previous)
        return result

    # running a frame is usually the same as resuming it from its
    # initial state, but not for generator frames
    run = resume

    def eval(self, executioncontext):
        "Abstract method to override."
        raise TypeError, "abstract"

    def getdictscope(self):
        "Get the locals as a dictionary."
        self.fast2locals()
        return self.w_locals

    def fget_getdictscope(space, w_self):
        self = space.unwrap_builtin(w_self)
        return self.getdictscope()

    def setdictscope(self, w_locals):
        "Initialize the locals from a dictionary."
        self.w_locals = w_locals
        self.locals2fast()

    def getfastscope(self):
        "Abstract. Get the fast locals as a list."
        raise TypeError, "abstract"

    def setfastscope(self, scope_w):
        """Abstract. Initialize the fast locals from a list of values,
        where the order is according to self.code.signature()."""
        raise TypeError, "abstract"        

    def fast2locals(self):
        # Copy values from self.fastlocals_w to self.w_locals
        if self.w_locals is None:
            self.w_locals = self.space.newdict([])
        varnames = self.code.getvarnames()
        for name, w_value in zip(varnames, self.getfastscope()):
            if w_value is not UNDEFINED:
                w_name = self.space.wrap(name)
                self.space.setitem(self.w_locals, w_name, w_value)

    def locals2fast(self):
        # Copy values from self.w_locals to self.fastlocals_w
        assert self.w_locals is not None
        varnames = self.code.getvarnames()

        new_fastlocals_w = [UNDEFINED]*self.numlocals
        
        for name, i in zip(varnames, range(self.numlocals)):
            w_name = self.space.wrap(varnames[i])
            try:
                w_value = self.space.getitem(self.w_locals, w_name)
            except OperationError, e:
                if not e.match(self.space, self.space.w_KeyError):
                    raise
            else:
                new_fastlocals_w[i] = w_value

        self.setfastscope(new_fastlocals_w)
