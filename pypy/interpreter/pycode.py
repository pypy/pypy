"""
Python-style code objects.
PyCode instances have the same co_xxx arguments as CPython code objects.
The bytecode interpreter itself is implemented by the PyFrame class.
"""

import dis
from pypy.interpreter import eval
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable


# code object contants, for co_flags below
CO_OPTIMIZED    = 0x0001
CO_NEWLOCALS    = 0x0002
CO_VARARGS      = 0x0004
CO_VARKEYWORDS  = 0x0008
CO_NESTED       = 0x0010
CO_GENERATOR    = 0x0020

class AppPyCode(Wrappable):
    """ applevel representation of a PyCode object. """
    def __init__(self, pycode, space):
        self.space = space
        self.pycode = pycode

    def __unwrap__(self):
        return self.pycode
        
    def pypy_id(self):
        # XXX we need a type system for internal objects!
        return id(self.pycode)

    def pypy_type(self):
        # XXX we need a type system for internal objects!
        return self.space.wrap(self.__class__)
       
    def app_visible(self):

        # XXX change that if we have type objects ...
        l = []
        for name,value in self.pycode.__dict__.items():
            if name.startswith('co_'):
                l.append( (name, self.space.wrap(value)))
        l.append(('__class__', self.pypy_type()))
        return l

class PyCode(eval.Code):
    "CPython-style code objects."
    
    def __init__(self, co_name=''):
        eval.Code.__init__(self, co_name)
        self.co_argcount = 0         # #arguments, except *vararg and **kwarg
        self.co_nlocals = 0          # #local variables
        self.co_stacksize = 0        # #entries needed for evaluation stack
        self.co_flags = 0            # CO_..., see above
        self.co_code = None          # string: instruction opcodes
        self.co_consts = ()          # tuple: constants used
        self.co_names = ()           # tuple of strings: names (for attrs,...)
        self.co_varnames = ()        # tuple of strings: local variable names
        self.co_freevars = ()        # tuple of strings: free variable names
        self.co_cellvars = ()        # tuple of strings: cell variable names
        # The rest doesn't count for hash/cmp
        self.co_filename = ""        # string: where it was loaded from
        #self.co_name (in base class)# string: name, for reference
        self.co_firstlineno = 0      # first source line number
        self.co_lnotab = ""          # string: encoding addr<->lineno mapping

    def __wrap__(self, space):
        return space.wrap(AppPyCode(self, space))

    def _from_code(self, code):
        """ Initialize the code object from a real (CPython) one.
            This is just a hack, until we have our own compile.
            At the moment, we just fake this.
            This method is called by our compile builtin function.
        """
        import types
        assert isinstance(code, types.CodeType)
        # simply try to suck in all attributes we know of
        for name in self.__dict__.keys():
            value = getattr(code, name)
            setattr(self, name, value)
        newconsts = ()
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                const = PyCode()._from_code(const)
            newconsts = newconsts + (const,)
        self.co_consts = newconsts
        return self

    def create_frame(self, space, w_globals, closure=None):
        "Create an empty PyFrame suitable for this code object."
        # select the appropriate kind of frame
        from pypy.interpreter.pyopcode import PyInterpFrame as Frame
        if self.co_cellvars or self.co_freevars:
            from pypy.interpreter.nestedscope import PyNestedScopeFrame as F
            Frame = enhanceclass(Frame, F)
        if self.co_flags & CO_GENERATOR:
            from pypy.interpreter.generator import GeneratorFrame as F
            Frame = enhanceclass(Frame, F)
        return Frame(space, self, w_globals, closure)

    def signature(self):
        "([list-of-arg-names], vararg-name-or-None, kwarg-name-or-None)."
        argcount = self.co_argcount
        argnames = list(self.co_varnames[:argcount])
        if self.co_flags & CO_VARARGS:
            varargname = self.co_varnames[argcount]
            argcount += 1
        else:
            varargname = None
        if self.co_flags & CO_VARKEYWORDS:
            kwargname = self.co_varnames[argcount]
            argcount += 1
        else:
            kwargname = None
        return argnames, varargname, kwargname

    def getvarnames(self):
        return self.co_varnames

    def dictscope_needed(self):
        # regular functions always have CO_OPTIMIZED and CO_NEWLOCALS.
        # class bodies only have CO_NEWLOCALS.
        return not (self.co_flags & CO_OPTIMIZED)

    def getjoinpoints(self):
        """Compute the bytecode positions that are potential join points
        (for FlowObjSpace)"""
        # first approximation
        return dis.findlabels(self.co_code)


def enhanceclass(baseclass, newclass, cache={}):
    # this is a bit too dynamic for RPython, but it looks nice
    # and I assume that we can easily change it into a static
    # pre-computed table
    if issubclass(newclass, baseclass):
        return newclass
    else:
        try:
            return cache[baseclass, newclass]
        except KeyError:
            class Mixed(newclass, baseclass):
                pass
            cache[baseclass, newclass] = Mixed
            return Mixed
