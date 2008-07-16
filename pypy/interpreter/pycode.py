"""
Python-style code objects.
PyCode instances have the same co_xxx arguments as CPython code objects.
The bytecode interpreter itself is implemented by the PyFrame class.
"""

import dis, imp, struct, types, new

from pypy.interpreter import eval
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped 
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.rlib.rarithmetic import intmask

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


class PyCode(eval.Code):
    "CPython-style code objects."

    def __init__(self, space,  argcount, nlocals, stacksize, flags,
                     code, consts, names, varnames, filename,
                     name, firstlineno, lnotab, freevars, cellvars,
                     hidden_applevel=False, magic = 62131 | 0x0a0d0000): # value for Python 2.5c2
        """Initialize a new code object from parameters given by
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
            # Cell vars could shadow already-set arguments.
            # astcompiler.pyassem used to be clever about the order of
            # the variables in both co_varnames and co_cellvars, but
            # it no longer is for the sake of simplicity.  Moreover
            # code objects loaded from CPython don't necessarily follow
            # an order, which could lead to strange bugs if .pyc files
            # produced by CPython are loaded by PyPy.  Note that CPython
            # contains the following bad-looking nested loops at *every*
            # function call!
            argvars  = self.co_varnames
            cellvars = self.co_cellvars
            for i in range(len(cellvars)):
                cellname = cellvars[i]
                for j in range(argcount):
                    if cellname == argvars[j]:
                        # argument j has the same name as the cell var i
                        while len(self._args_as_cellvars) <= i:
                            self._args_as_cellvars.append(-1)   # pad
                        self._args_as_cellvars[i] = j

        self._compute_fastcall()

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
        if len(self._args_as_cellvars) > 0:
            return

        self.do_fastcall = self.co_argcount

    def fastcall_0(self, space, w_func):
        if self.do_fastcall == 0:
            frame = space.createframe(self, w_func.w_func_globals,
                                      w_func.closure)
            return frame.run()
        return None

    def fastcall_1(self, space, w_func, w_arg):
        if self.do_fastcall == 1:
            frame = space.createframe(self, w_func.w_func_globals,
                                      w_func.closure)
            frame.fastlocals_w[0] = w_arg # frame.setfastscope([w_arg])
            return frame.run()
        return None

    def fastcall_2(self, space, w_func, w_arg1, w_arg2):
        if self.do_fastcall == 2:
            frame = space.createframe(self, w_func.w_func_globals,
                                      w_func.closure)
            frame.fastlocals_w[0] = w_arg1 # frame.setfastscope([w_arg])
            frame.fastlocals_w[1] = w_arg2
            return frame.run()
        return None

    def fastcall_3(self, space, w_func, w_arg1, w_arg2, w_arg3):
        if self.do_fastcall == 3:
            frame = space.createframe(self, w_func.w_func_globals,
                                       w_func.closure)
            frame.fastlocals_w[0] = w_arg1 # frame.setfastscope([w_arg])
            frame.fastlocals_w[1] = w_arg2 
            frame.fastlocals_w[2] = w_arg3 
            return frame.run()
        return None

    def fastcall_4(self, space, w_func, w_arg1, w_arg2, w_arg3, w_arg4):
        if self.do_fastcall == 4:
            frame = space.createframe(self, w_func.w_func_globals,
                                       w_func.closure)
            frame.fastlocals_w[0] = w_arg1 # frame.setfastscope([w_arg])
            frame.fastlocals_w[1] = w_arg2 
            frame.fastlocals_w[2] = w_arg3 
            frame.fastlocals_w[3] = w_arg4 
            return frame.run()
        return None

    def funcrun(self, func, args):
        frame = self.space.createframe(self, func.w_func_globals,
                                  func.closure)
        sig = self._signature
        # speed hack
        args_matched = args.parse_into_scope(frame.fastlocals_w, func.name,
                                             sig, func.defs_w)
        frame.init_cells()
        return frame.run()

    def getvarnames(self):
        return self.co_varnames

    def getdocstring(self, space):
        if self.co_consts_w:   # it is probably never empty
            return self.co_consts_w[0]
        else:
            return space.w_None

    def getjoinpoints(self):
        """Compute the bytecode positions that are potential join points
        (for FlowObjSpace)"""
        # first approximation
        return dis.findlabels(self.co_code)

    def _to_code(self):
        """For debugging only."""
        consts = []
        for w in self.co_consts_w:
            if isinstance(w, PyCode):
                consts.append(w._to_code())
            else:
                consts.append(self.space.unwrap(w))
        return new.code( self.co_argcount,
                         self.co_nlocals,
                         self.co_stacksize,
                         self.co_flags,
                         self.co_code,
                         tuple(consts),
                         tuple(self.co_names),
                         tuple(self.co_varnames),
                         self.co_filename,
                         self.co_name,
                         self.co_firstlineno,
                         self.co_lnotab,
                         tuple(self.co_freevars),
                         tuple(self.co_cellvars) )

    def dump(self):
        """A dis.dis() dump of the code object."""
        co = self._to_code()
        dis.dis(co)

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
        from pypy.interpreter.mixedmodule import MixedModule
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
