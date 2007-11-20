"""
This module defines the abstract base classes that support execution:
Code and Frame.
"""
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable


class Code(Wrappable):
    """A code is a compiled version of some source code.
    Abstract base class."""
    hidden_applevel = False

    def __init__(self, co_name):
        self.co_name = co_name

    def exec_code(self, space, w_globals, w_locals):
        "Implements the 'exec' statement."
        # this should be on PyCode?
        frame = space.createframe(self, w_globals, None)
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

    def getdocstring(self, space):
        return space.w_None

    def funcrun(self, func, args):
        frame = func.space.createframe(self, func.w_func_globals,
                                        func.closure)
        sig = self.signature()
        scope_w = args.parse(func.name, sig, func.defs_w)
        frame.setfastscope(scope_w)
        return frame.run()

        
    # a performance hack (see gateway.BuiltinCode1/2/3 and pycode.PyCode)
    def fastcall_0(self, space, func):
        return None
    def fastcall_1(self, space, func, w1):
        return None
    def fastcall_2(self, space, func, w1, w2):
        return None
    def fastcall_3(self, space, func, w1, w2, w3):
        return None
    def fastcall_4(self, space, func, w1, w2, w3, w4):
        return None

class Frame(Wrappable):
    """A frame is an environment supporting the execution of a code object.
    Abstract base class."""

    def __init__(self, space, w_globals=None, numlocals=-1):
        self.space      = space
        self.w_globals  = w_globals  # wrapped dict of globals
        self.w_locals   = None       # wrapped dict of locals
        if numlocals < 0:  # compute the minimal size based on arguments
            numlocals = len(self.getcode().getvarnames())
        self.numlocals = numlocals

    def run(self):
        "Abstract method to override. Runs the frame"
        raise TypeError, "abstract"
    
    def getdictscope(self):
        "Get the locals as a dictionary."
        self.fast2locals()
        return self.w_locals

    def getcode(self):
        return None

    def fget_code(space, self):
        return space.wrap(self.getcode())

    def fget_getdictscope(space, self): # unwrapping through unwrap_spec in typedef.py
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
        where the order is according to self.getcode().signature()."""
        raise TypeError, "abstract"

    def fast2locals(self):
        # Copy values from self.fastlocals_w to self.w_locals
        if self.w_locals is None:
            self.w_locals = self.space.newdict()
        varnames = self.getcode().getvarnames()
        fastscope_w = self.getfastscope()
        for i in range(min(len(varnames), len(fastscope_w))):
            name = varnames[i]
            w_value = fastscope_w[i]
            if w_value is not None:
                w_name = self.space.wrap(name)
                self.space.setitem(self.w_locals, w_name, w_value)

    def locals2fast(self):
        # Copy values from self.w_locals to self.fastlocals_w
        assert self.w_locals is not None
        varnames = self.getcode().getvarnames()

        new_fastlocals_w = [None]*self.numlocals
        
        for i in range(min(len(varnames), self.numlocals)):
            w_name = self.space.wrap(varnames[i])
            try:
                w_value = self.space.getitem(self.w_locals, w_name)
            except OperationError, e:
                if not e.match(self.space, self.space.w_KeyError):
                    raise
            else:
                new_fastlocals_w[i] = w_value

        self.setfastscope(new_fastlocals_w)
