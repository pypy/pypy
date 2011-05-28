"""
This module defines the abstract base classes that support execution:
Code and Frame.
"""
from pypy.rlib import jit
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable


class Code(Wrappable):
    """A code is a compiled version of some source code.
    Abstract base class."""
    _immutable_ = True
    hidden_applevel = False

    # n >= 0 : arity
    # FLATPYCALL = 0x100
    # n|FLATPYCALL: pycode flat case
    # FLATPYCALL<<x (x>=1): special cases
    # HOPELESS: hopeless
    FLATPYCALL = 0x100
    PASSTHROUGHARGS1 = 0x200
    HOPELESS = 0x400
    fast_natural_arity = HOPELESS

    def __init__(self, co_name):
        self.co_name = co_name

    def exec_code(self, space, w_globals, w_locals):
        "Implements the 'exec' statement."
        # this should be on PyCode?
        frame = space.createframe(self, w_globals, None)
        frame.setdictscope(w_locals)
        return frame.run()

    def signature(self):
        raise NotImplementedError

    def getvarnames(self):
        """List of names including the arguments, vararg and kwarg,
        and possibly more locals."""
        return self.signature().getallvarnames()

    def getformalargcount(self):
        return self.signature().scope_length()

    def getdocstring(self, space):
        return space.w_None

    def funcrun(self, func, args):
        raise NotImplementedError("purely abstract")

    def funcrun_obj(self, func, w_obj, args):
        return self.funcrun(func, args.prepend(w_obj))

class Frame(Wrappable):
    """A frame is an environment supporting the execution of a code object.
    Abstract base class."""

    def __init__(self, space, w_globals=None):
        self.space      = space
        self.w_globals  = w_globals  # wrapped dict of globals
        self.w_locals   = None       # wrapped dict of locals

    def run(self):
        "Abstract method to override. Runs the frame"
        raise TypeError, "abstract"
    
    def getdictscope(self):
        "Get the locals as a dictionary."
        self.fast2locals()
        return self.w_locals

    def getcode(self):
        return None

    def fget_code(self, space):
        return space.wrap(self.getcode())

    def fget_getdictscope(self, space):
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

    def getfastscopelength(self):
        "Abstract. Get the expected number of locals."
        raise TypeError, "abstract"

    @jit.dont_look_inside
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

    @jit.dont_look_inside
    def locals2fast(self):
        # Copy values from self.w_locals to self.fastlocals_w
        assert self.w_locals is not None
        varnames = self.getcode().getvarnames()
        numlocals = self.getfastscopelength()

        new_fastlocals_w = [None] * numlocals

        for i in range(min(len(varnames), numlocals)):
            w_name = self.space.wrap(varnames[i])
            try:
                w_value = self.space.getitem(self.w_locals, w_name)
            except OperationError, e:
                if not e.match(self.space, self.space.w_KeyError):
                    raise
            else:
                new_fastlocals_w[i] = w_value

        self.setfastscope(new_fastlocals_w)
