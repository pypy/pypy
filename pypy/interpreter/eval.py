"""
This module defines the abstract base classes that support execution:
Code and Frame.
"""
from error import OperationError

class Code(object):
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


UNDEFINED = object()  # marker for undefined local variables


class Frame(object):
    """A frame is an environment supporting the execution of a code object.
    Abstract base class."""

    def __init__(self, space, code, w_globals=None, numlocals=-1):
        self.space      = space
        self.code       = code       # Code instance
        self.w_globals  = w_globals  # wrapped dict of globals
        self.w_locals   = None       # wrapped dict of locals
        if numlocals < 0:  # compute the minimal size based on arguments
            numlocals = len(code.getvarnames())
        self.fastlocals_w = [UNDEFINED]*numlocals  # flat list of wrapped locals

    def run(self):
        "Run the frame."
        executioncontext = self.space.getexecutioncontext()
        previous = executioncontext.enter(self)
        try:
            result = self.eval(executioncontext)
        finally:
            executioncontext.leave(previous)
        return result

    def eval(self, executioncontext):
        "Abstract method to override."
        raise TypeError, "abstract"

    def getdictscope(self):
        "Get the locals as a dictionary."
        self.fast2locals()
        return self.w_locals

    def setdictscope(self, w_locals):
        "Initialize the locals from a dictionary."
        self.w_locals = w_locals
        self.locals2fast()

    def getfastscope(self):
        "Get the fast locals as a list."
        return self.fastlocals_w

    def setfastscope(self, scope_w):
        """Initialize the fast locals from a list of values,
        where the order is according to self.code.signature()."""
        if len(scope_w) > len(self.fastlocals_w):
            raise ValueError, "new fastscope is longer than the allocated area"
        self.fastlocals_w[:len(scope_w)] = scope_w

    def fast2locals(self):
        # Copy values from self.fastlocals_w to self.w_locals
        if self.w_locals is None:
            self.w_locals = self.space.newdict([])
        varnames = self.code.getvarnames()
        for name, w_value in zip(varnames, self.fastlocals_w):
            if w_value is not UNDEFINED:
                w_name = self.space.wrap(name)
                self.space.setitem(self.w_locals, w_name, w_value)

    def locals2fast(self):
        # Copy values from self.w_locals to self.fastlocals_w
        assert self.w_locals is not None
        varnames = self.code.getvarnames()
        for name, i in zip(varnames, range(len(self.fastlocals_w))):
            w_name = self.space.wrap(varnames[i])
            try:
                w_value = self.space.getitem(self.w_locals, w_name)
            except OperationError, e:
                if not e.match(self.space, self.space.w_KeyError):
                    raise
            else:
                self.fastlocals_w[i] = w_value
