"""
Python-style code objects.
PyCode instances have the same co_xxx arguments as CPython code objects.
The bytecode interpreter itself is implemented by the PyFrame class.
"""

import dis
from pypy.interpreter import eval
from pypy.tool.cache import Cache 

# code object contants, for co_flags below
CO_OPTIMIZED    = 0x0001
CO_NEWLOCALS    = 0x0002
CO_VARARGS      = 0x0004
CO_VARKEYWORDS  = 0x0008
CO_NESTED       = 0x0010
CO_GENERATOR    = 0x0020

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

    def _from_code(self, code):
        """ NOT_RPYTHON
            Initialize the code object from a real (CPython) one.
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

    def getdocstring(self):
        if self.co_consts:   # it is probably never empty
            return self.co_consts[0]
        else:
            return None

    def dictscope_needed(self):
        # regular functions always have CO_OPTIMIZED and CO_NEWLOCALS.
        # class bodies only have CO_NEWLOCALS.
        return not (self.co_flags & CO_OPTIMIZED)

    def getjoinpoints(self):
        """Compute the bytecode positions that are potential join points
        (for FlowObjSpace)"""
        # first approximation
        return dis.findlabels(self.co_code)

    def descr_code__new__(space, w_subtype,
                          w_argcount, w_nlocals, w_stacksize, w_flags,
                          w_codestring, w_constants, w_names,
                          w_varnames, w_filename, w_name, w_firstlineno,
                          w_lnotab, w_freevars=None, w_cellvars=None):
        code = space.allocate_instance(PyCode, w_subtype)
        code.__init__()
        # XXX typechecking everywhere!
        code.co_argcount   = space.unwrap(w_argcount)
        code.co_nlocals    = space.unwrap(w_nlocals)
        code.co_stacksize  = space.unwrap(w_stacksize)
        code.co_flags      = space.unwrap(w_flags)
        code.co_code       = space.unwrap(w_codestring)
        code.co_consts     = space.unwrap(w_constants)
        code.co_names      = space.unwrap(w_names)
        code.co_varnames   = space.unwrap(w_varnames)
        code.co_filename   = space.unwrap(w_filename)
        code.co_name       = space.unwrap(w_name)
        code.co_firstlineno= space.unwrap(w_firstlineno)
        code.co_lnotab     = space.unwrap(w_lnotab)
        if w_freevars is not None:
            code.co_freevars = space.unwrap(w_freevars)
        if w_cellvars is not None:
            code.co_cellvars = space.unwrap(w_cellvars)
        return space.wrap(code)

def _really_enhanceclass(key, stuff):
    return type("Mixed", key, {})

def enhanceclass(baseclass, newclass, cache=Cache()):
    # this is a bit too dynamic for RPython, but it looks nice
    # and I assume that we can easily change it into a static
    # pre-computed table
    if issubclass(newclass, baseclass):
        return newclass
    else:
        return cache.getorbuild((newclass, baseclass),
                                _really_enhanceclass, None)
