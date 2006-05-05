"""
Python-style code objects.
PyCode instances have the same co_xxx arguments as CPython code objects.
The bytecode interpreter itself is implemented by the PyFrame class.
"""

import dis, imp, struct, types

from pypy.interpreter import eval
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped 
from pypy.interpreter.baseobjspace import ObjSpace, W_Root 
from pypy.interpreter.mixedmodule import MixedModule
from pypy.rpython.rarithmetic import intmask

# helper

def unpack_str_tuple(space,w_str_tuple):
    els = []
    for w_el in space.unpackiterable(w_str_tuple):
        els.append(space.str_w(w_el))
    return els


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
    assert argcount >= 0     # annotator hint
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

cpython_magic, = struct.unpack("<i", imp.get_magic())

NESTED    = 1
GENERATOR = 2

frame_classes = []

def setup_frame_classes():
    "NOT_RPYTHON"
    from pypy.interpreter.pyopcode import PyInterpFrame
    from pypy.interpreter.nestedscope import PyNestedScopeFrame
    from pypy.interpreter.generator import GeneratorFrame

    def fresh_GeneratorFrame_methods():
        from pypy.tool.sourcetools import func_with_new_name
        dic = GeneratorFrame.__dict__.copy()
        for n in dic:
            x = dic[n]
            if isinstance(x, types.FunctionType):
                dic[n] = func_with_new_name(x, x.__name__)
        return dic

    frame_classes.extend([None]*4)
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

    def __init__(self, space,  argcount, nlocals, stacksize, flags,
                     code, consts, names, varnames, filename,
                     name, firstlineno, lnotab, freevars, cellvars,
                     hidden_applevel=False, magic = 62061 | 0x0a0d0000): # value for Python 2.4.1
        """Initialize a new code objects from parameters given by
        the pypy compiler"""
        self.space = space
        eval.Code.__init__(self, name)
        self.co_argcount = argcount
        self.co_nlocals = nlocals
        self.co_stacksize = stacksize
        self.co_flags = flags
        self.co_code = code
        self.co_consts_w = consts
        self.co_names_w = [space.new_interned_str(aname) for aname in names]
        self.co_varnames = varnames
        self.co_freevars = freevars
        self.co_cellvars = cellvars
        self.co_filename = filename
        self.co_name = name
        self.co_firstlineno = firstlineno
        self.co_lnotab = lnotab
        self.hidden_applevel = hidden_applevel
        self.magic = magic
        self._compute_fastcall()
        self._signature = cpython_code_signature(self)
        # Precompute what arguments need to be copied into cellvars
        self._args_as_cellvars = []
        
        if self.co_cellvars:
            argcount = self.co_argcount
            assert argcount >= 0     # annotator hint
            if self.co_flags & CO_VARARGS:
                argcount += 1
            if self.co_flags & CO_VARKEYWORDS:
                argcount += 1
            # the first few cell vars could shadow already-set arguments,
            # in the same order as they appear in co_varnames
            argvars  = self.co_varnames
            cellvars = self.co_cellvars
            next     = 0
            nextname = cellvars[0]
            for i in range(argcount):
                if argvars[i] == nextname:
                    # argument i has the same name as the next cell var
                    self._args_as_cellvars.append(i)
                    next += 1
                    try:
                        nextname = cellvars[next]
                    except IndexError:
                        break   # all cell vars initialized this way

    co_names = property(lambda self: [self.space.unwrap(w_name) for w_name in self.co_names_w]) # for trace

    def signature(self):
        return self._signature
    
    def _from_code(space, code, hidden_applevel=False):
        """ Initialize the code object from a real (CPython) one.
            This is just a hack, until we have our own compile.
            At the moment, we just fake this.
            This method is called by our compile builtin function.
        """
        assert isinstance(code, types.CodeType)
        newconsts_w = []
        for const in code.co_consts:
            if isinstance(const, types.CodeType): # from stable compiler
                const = PyCode._from_code(space, const, hidden_applevel=hidden_applevel)

            newconsts_w.append(space.wrap(const))
        # stick the underlying CPython magic value, if the code object
        # comes from there
        return PyCode(space, code.co_argcount,
                      code.co_nlocals,
                      code.co_stacksize,
                      code.co_flags,
                      code.co_code,
                      newconsts_w,
                      list(code.co_names),
                      list(code.co_varnames),
                      code.co_filename,
                      code.co_name,
                      code.co_firstlineno,
                      code.co_lnotab,
                      list(code.co_freevars),
                      list(code.co_cellvars),
                      hidden_applevel, cpython_magic)

    _from_code = staticmethod(_from_code)

    def _code_new_w(space, argcount, nlocals, stacksize, flags,
                    code, consts, names, varnames, filename,
                    name, firstlineno, lnotab, freevars, cellvars,
                    hidden_applevel=False):
        """Initialize a new code objects from parameters given by
        the pypy compiler"""
        return PyCode(space, argcount, nlocals, stacksize, flags, code, consts,
                      names, varnames, filename, name, firstlineno, lnotab,
                      freevars, cellvars, hidden_applevel)

    _code_new_w = staticmethod(_code_new_w)
    
    def _compute_fastcall(self):
        # Speed hack!
        self.do_fastcall = -1
        if not (0 <= self.co_argcount <= 4):
            return
        if self.co_flags & (CO_VARARGS | CO_VARKEYWORDS):
            return
        if self.co_cellvars:
            first_cellvar = self.co_cellvars[0]
            for i in range(self.co_argcount):
                if first_cellvar == self.co_varnames[i]:
                    return

        self.do_fastcall = self.co_argcount

    def fastcall_0(self, space, w_func):
        if self.do_fastcall == 0:
            frame = self.create_frame(space, w_func.w_func_globals,
                                      w_func.closure)
            return frame.run()
        return None

    def fastcall_1(self, space, w_func, w_arg):
        if self.do_fastcall == 1:
            frame = self.create_frame(space, w_func.w_func_globals,
                                      w_func.closure)
            frame.fastlocals_w[0] = w_arg # frame.setfastscope([w_arg])
            return frame.run()
        return None

    def fastcall_2(self, space, w_func, w_arg1, w_arg2):
        if self.do_fastcall == 2:
            frame = self.create_frame(space, w_func.w_func_globals,
                                      w_func.closure)
            frame.fastlocals_w[0] = w_arg1 # frame.setfastscope([w_arg])
            frame.fastlocals_w[1] = w_arg2
            return frame.run()
        return None

    def fastcall_3(self, space, w_func, w_arg1, w_arg2, w_arg3):
        if self.do_fastcall == 3:
            frame = self.create_frame(space, w_func.w_func_globals,
                                      w_func.closure)
            frame.fastlocals_w[0] = w_arg1 # frame.setfastscope([w_arg])
            frame.fastlocals_w[1] = w_arg2 
            frame.fastlocals_w[2] = w_arg3 
            return frame.run()
        return None

    def fastcall_4(self, space, w_func, w_arg1, w_arg2, w_arg3, w_arg4):
        if self.do_fastcall == 4:
            frame = self.create_frame(space, w_func.w_func_globals,
                                      w_func.closure)
            frame.fastlocals_w[0] = w_arg1 # frame.setfastscope([w_arg])
            frame.fastlocals_w[1] = w_arg2 
            frame.fastlocals_w[2] = w_arg3 
            frame.fastlocals_w[3] = w_arg4 
            return frame.run()
        return None

    def funcrun(self, func, args):
        frame = self.create_frame(self.space, func.w_func_globals,
                                  func.closure)
        sig = self._signature
        # speed hack
        args_matched = args.parse_into_scope(frame.fastlocals_w, func.name,
                                             sig, func.defs_w)
        frame.init_cells()
        return frame.run()

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

    def initialize_frame_scopes(self, frame): 
        # regular functions always have CO_OPTIMIZED and CO_NEWLOCALS.
        # class bodies only have CO_NEWLOCALS.
        # CO_NEWLOCALS: make a locals dict unless optimized is also set
        # CO_OPTIMIZED: no locals dict needed at all 
        flags = self.co_flags
        if flags & CO_OPTIMIZED: 
            return 
        if flags & CO_NEWLOCALS:
            frame.w_locals = frame.space.newdict([])
        else:
            assert frame.w_globals is not None
            frame.w_locals = frame.w_globals 
        
    def getjoinpoints(self):
        """Compute the bytecode positions that are potential join points
        (for FlowObjSpace)"""
        # first approximation
        return dis.findlabels(self.co_code)

    def fget_co_consts(space, self):
        return space.newtuple(self.co_consts_w)
    
    def fget_co_names(space, self):
        return space.newtuple(self.co_names_w)

    def fget_co_varnames(space, self):
        return space.newtuple([space.wrap(name) for name in self.co_varnames])

    def fget_co_cellvars(space, self):
        return space.newtuple([space.wrap(name) for name in self.co_cellvars])

    def fget_co_freevars(space, self):
        return space.newtuple([space.wrap(name) for name in self.co_freevars])    

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
                    len(self.co_names_w) == len(other.co_names_w) and
                    self.co_varnames == other.co_varnames and
                    self.co_freevars == other.co_freevars and
                    self.co_cellvars == other.co_cellvars)
        if not areEqual:
            return space.w_False

        for i in range(len(self.co_names_w)):
            if not space.eq_w(self.co_names_w[i], other.co_names_w[i]):
                return space.w_False

        for i in range(len(self.co_consts_w)):
            if not space.eq_w(self.co_consts_w[i], other.co_consts_w[i]):
                return space.w_False

        return space.w_True

    def descr_code__hash__(self):
        space = self.space
        result =  hash(self.co_name)
        result ^= self.co_argcount
        result ^= self.co_nlocals
        result ^= self.co_flags
        result ^= self.co_firstlineno
        result ^= hash(self.co_code)
        for name in self.co_varnames:  result ^= hash(name)
        for name in self.co_freevars:  result ^= hash(name)
        for name in self.co_cellvars:  result ^= hash(name)
        w_result = space.wrap(intmask(result))
        for w_name in self.co_names_w:
            w_result = space.xor(w_result, space.hash(w_name))
        for w_const in self.co_consts_w:
            w_result = space.xor(w_result, space.hash(w_const))
        return w_result

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
        if argcount < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("code: argcount must not be negative"))
        if nlocals < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("code: nlocals must not be negative"))        
        consts_w   = space.unpacktuple(w_constants)
        names      = unpack_str_tuple(space, w_names)
        varnames   = unpack_str_tuple(space, w_varnames)
        if w_freevars is not None:
            freevars = unpack_str_tuple(space, w_freevars)
        else:
            freevars = []
        if w_cellvars is not None:
            cellvars = unpack_str_tuple(space, w_cellvars)
        else:
            cellvars = []
        code = space.allocate_instance(PyCode, w_subtype)
        PyCode.__init__(code, space, argcount, nlocals, stacksize, flags, codestring, consts_w, names,
                      varnames, filename, name, firstlineno, lnotab, freevars, cellvars)
        return space.wrap(code)
    descr_code__new__.unwrap_spec = unwrap_spec 

    def descr__reduce__(self, space):
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('code_new')
        w        = space.wrap
        tup      = [
            w(self.co_argcount), 
            w(self.co_nlocals), 
            w(self.co_stacksize), 
            w(self.co_flags),
            w(self.co_code), 
            space.newtuple(self.co_consts_w), 
            space.newtuple(self.co_names_w), 
            space.newtuple([w(v) for v in self.co_varnames]), 
            w(self.co_filename),
            w(self.co_name), 
            w(self.co_firstlineno),
            w(self.co_lnotab), 
            space.newtuple([w(v) for v in self.co_freevars]),
            space.newtuple([w(v) for v in self.co_cellvars]),
            #hidden_applevel=False, magic = 62061 | 0x0a0d0000
        ]
        return space.newtuple([new_inst, space.newtuple(tup)])
