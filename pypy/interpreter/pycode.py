"""
Python-style code objects.
PyCode instances have the same co_xxx arguments as CPython code objects.
The bytecode interpreter itself is implemented by the PyFrame class.
"""

import dis
from pypy.interpreter import eval
from pypy.interpreter.gateway import NoneNotWrapped 
from pypy.interpreter.baseobjspace import ObjSpace, W_Root 
from pypy.tool.cache import Cache 

# helper

def unpack_str_tuple(space,w_str_tuple):
    els = []
    for w_el in space.unpackiterable(w_str_tuple):
        els.append(space.str_w(w_el))
    return tuple(els)


# code object contants, for co_flags below
CO_OPTIMIZED    = 0x0001
CO_NEWLOCALS    = 0x0002
CO_VARARGS      = 0x0004
CO_VARKEYWORDS  = 0x0008
CO_NESTED       = 0x0010
CO_GENERATOR    = 0x0020

# cpython_code_signature helper
def cpython_code_signature(code):
    "([list-of-arg-names], vararg-name-or-None, kwarg-name-or-None)."
    argcount = code.co_argcount
    argnames = list(code.co_varnames[:argcount])
    if code.co_flags & CO_VARARGS:
        varargname = code.co_varnames[argcount]
        argcount += 1
    else:
        varargname = None
    if code.co_flags & CO_VARKEYWORDS:
        kwargname = code.co_varnames[argcount]
        argcount += 1
    else:
        kwargname = None
    return argnames, varargname, kwargname


NESTED    = 1
GENERATOR = 2

frame_classes = {}

def setup_frame_classes():
    "NOT_RPYTHON"
    from pypy.interpreter.pyopcode import PyInterpFrame
    from pypy.interpreter.nestedscope import PyNestedScopeFrame
    from pypy.interpreter.generator import GeneratorFrame

    def fresh_GeneratorFrame_methods():
        import types
        from pypy.tool.hack import func_with_new_name
        dic = GeneratorFrame.__dict__.copy()
        for n in dic:
            x = dic[n]
            if isinstance(x, types.FunctionType):
                dic[n] = func_with_new_name(x, x.__name__)
        return dic

    frame_classes[0]                = PyInterpFrame
    frame_classes[NESTED]           = PyNestedScopeFrame
    frame_classes[GENERATOR]        = type('PyGeneratorFrame',
                                           (PyInterpFrame,),
                                           fresh_GeneratorFrame_methods())
    frame_classes[NESTED|GENERATOR] = type('PyNestedScopeGeneratorFrame',
                                           (PyNestedScopeFrame,),
                                           fresh_GeneratorFrame_methods())

class PyCode(eval.Code):
    "CPython-style code objects."
    
    def __init__(self, space, co_name=''):
        self.space = space
        eval.Code.__init__(self, co_name)
        self.co_argcount = 0         # #arguments, except *vararg and **kwarg
        self.co_nlocals = 0          # #local variables
        self.co_stacksize = 0        # #entries needed for evaluation stack
        self.co_flags = 0            # CO_..., see above
        self.co_code = None          # string: instruction opcodes
        self.co_consts_w = []        # list of constants used (wrapped!)
        self.co_names = []           # list of strings: names (for attrs..)
        self.co_varnames = []        # tuple of strings: local variable names
        self.co_freevars = []        # tuple of strings: free variable names
        self.co_cellvars = []        # tuple of strings: cell variable names
        # The rest doesn't count for hash/cmp
        self.co_filename = ""        # string: where it was loaded from
        #self.co_name (in base class)# string: name, for reference
        self.co_firstlineno = 0      # first source line number
        self.co_lnotab = ""          # string: encoding addr<->lineno mapping
        self.applevel = False

    def _from_code(self, code, applevel=False):
        """ Initialize the code object from a real (CPython) one.
            This is just a hack, until we have our own compile.
            At the moment, we just fake this.
            This method is called by our compile builtin function.
        """
        self.applevel = applevel
        import types
        assert isinstance(code, types.CodeType)
        # simply try to suck in all attributes we know of
        # with a lot of boring asserts to enforce type knowledge
        # XXX get rid of that ASAP with a real compiler!
        x = code.co_argcount; assert isinstance(x, int)
        self.co_argcount = x
        x = code.co_nlocals; assert isinstance(x, int)
        self.co_nlocals = x
        x = code.co_stacksize; assert isinstance(x, int)
        self.co_stacksize = x
        x = code.co_flags; assert isinstance(x, int)
        self.co_flags = x
        x = code.co_code; assert isinstance(x, str)
        self.co_code = x
        #self.co_consts = <see below>
        x = code.co_names; assert isinstance(x, tuple)
        self.co_names = [ str(n) for n in x ]
        x = code.co_varnames; assert isinstance(x, tuple)
        self.co_varnames = [ str(n) for n in x ]
        x = code.co_freevars; assert isinstance(x, tuple)
        self.co_freevars = [ str(n) for n in x ]
        x = code.co_cellvars; assert isinstance(x, tuple)
        self.co_cellvars = [ str(n) for n in x ]
        x = code.co_filename; assert isinstance(x, str)
        self.co_filename = x
        x = code.co_name; assert isinstance(x, str)
        self.co_name = x
        x = code.co_firstlineno; assert isinstance(x, int)
        self.co_firstlineno = x
        x = code.co_lnotab; assert isinstance(x, str)
        self.co_lnotab = x
        # recursively _from_code()-ify the code objects in code.co_consts
        space = self.space
        newconsts_w = []
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                const = PyCode(space)._from_code(const, applevel=applevel)
            newconsts_w.append(space.wrap(const))
        self.co_consts_w = newconsts_w
        return self

    def create_frame(self, space, w_globals, closure=None):
        "Create an empty PyFrame suitable for this code object."
        # select the appropriate kind of frame
        if not frame_classes:
            setup_frame_classes()   # lazily
        choose = 0
        if self.co_cellvars or self.co_freevars:
            choose |= NESTED
        if self.co_flags & CO_GENERATOR:
            choose |= GENERATOR
        Frame = frame_classes[choose]
        return Frame(space, self, w_globals, closure)

    signature = cpython_code_signature

    def getapplevel(self):
        return self.applevel
    
    def getvarnames(self):
        return self.co_varnames

    def getdocstring(self):
        if self.co_consts_w:   # it is probably never empty
            const0_w = self.co_consts_w[0]
            if const0_w is self.space.w_None:
                return None
            else:
                return self.space.str_w(const0_w)
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

    def fget_co_consts(space, self):
        return space.newtuple(self.co_consts_w)
    
    def fget_co_names(space, self):
        return space.newtuple([space.wrap(name) for name in self.co_names])

    def fget_co_varnames(space, self):
        return space.newtuple([space.wrap(name) for name in self.co_varnames])

    def fget_co_cellvars(space, self):
        return space.newtuple([space.wrap(name) for name in self.co_freevars])

    def fget_co_freevars(space, self):
        return space.newtuple([space.wrap(name) for name in self.co_cellvars])    

    def descr_code__eq__(self, w_other):
        space = self.space
        other = space.interpclass_w(w_other)
        if not isinstance(other, PyCode):
            return space.w_False
        areEqual = (self.co_name == other.co_name and
                    self.co_argcount == other.co_argcount and
                    self.co_nlocals == other.co_nlocals and
                    self.co_flags == other.co_flags and
                    self.co_firstlineno == other.co_firstlineno and
                    self.co_code == other.co_code and
                    len(self.co_consts_w) == len(other.co_consts_w) and
                    self.co_names == other.co_names and
                    self.co_varnames == other.co_varnames and
                    self.co_freevars == other.co_freevars and
                    self.co_cellvars == other.co_cellvars)
        if not areEqual:
            return space.w_False

        for i in range(len(self.co_consts_w)):
            if not space.eq_w(self.co_consts_w[i], other.co_consts_w[i]):
                return space.w_False

        return space.w_True
   
    unwrap_spec =        [ObjSpace, W_Root, 
                          int, int, int, int,
                          str, W_Root, W_Root, 
                          W_Root, str, str, int, 
                          str, W_Root, 
                          W_Root]
    def descr_code__new__(space, w_subtype,
                          argcount, nlocals, stacksize, flags,
                          codestring, w_constants, w_names,
                          w_varnames, filename, name, firstlineno,
                          lnotab, w_freevars=NoneNotWrapped,
                          w_cellvars=NoneNotWrapped):
        code = space.allocate_instance(PyCode, w_subtype)
        code.__init__(space)
        code.co_argcount   = argcount 
        code.co_nlocals    = nlocals 
        code.co_stacksize  = stacksize 
        code.co_flags      = flags 
        code.co_code       = codestring 
        code.co_consts_w   = space.unpacktuple(w_constants)
        code.co_names      = unpack_str_tuple(space, w_names)
        code.co_varnames   = unpack_str_tuple(space, w_varnames)
        code.co_filename   = filename 
        code.co_name       = name 
        code.co_firstlineno= firstlineno 
        code.co_lnotab     = lnotab 
        if w_freevars is not None:
            code.co_freevars = unpack_str_tuple(space, w_freevars)
        if w_cellvars is not None:
            code.co_cellvars = unpack_str_tuple(space, w_cellvars)
        return space.wrap(code)
    descr_code__new__.unwrap_spec = unwrap_spec 
