"""
Python-style code objects.
PyCode instances have the same co_xxx arguments as CPython code objects.
The bytecode interpreter itself is implemented by the PyFrame class.
"""

import dis, imp, struct, types, new, sys

from pypy.interpreter import eval
from pypy.interpreter.argument import Signature
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped, unwrap_spec
from pypy.interpreter.astcompiler.consts import (
    CO_OPTIMIZED, CO_NEWLOCALS, CO_VARARGS, CO_VARKEYWORDS, CO_NESTED,
    CO_GENERATOR, CO_CONTAINSGLOBALS)
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.debug import make_sure_not_resized
from pypy.rlib import jit
from pypy.rlib.objectmodel import compute_hash
from pypy.tool.stdlib_opcode import opcodedesc, HAVE_ARGUMENT

# helper

def unpack_str_tuple(space,w_str_tuple):
    return [space.str_w(w_el) for w_el in space.unpackiterable(w_str_tuple)]


# Magic numbers for the bytecode version in code objects.
# See comments in pypy/module/imp/importing.
cpython_magic, = struct.unpack("<i", imp.get_magic())   # host magic number
default_magic = (168686339+2) | 0x0a0d0000              # this PyPy's magic
                                                        # (from CPython 2.7.0)

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
    return Signature(argnames, varargname, kwargname)

class PyCode(eval.Code):
    "CPython-style code objects."
    _immutable_ = True
    _immutable_fields_ = ["co_consts_w[*]", "co_names_w[*]", "co_varnames[*]",
                          "co_freevars[*]", "co_cellvars[*]"]

    def __init__(self, space,  argcount, nlocals, stacksize, flags,
                     code, consts, names, varnames, filename,
                     name, firstlineno, lnotab, freevars, cellvars,
                     hidden_applevel=False, magic = default_magic):
        """Initialize a new code object from parameters given by
        the pypy compiler"""
        self.space = space
        eval.Code.__init__(self, name)
        assert nlocals >= 0
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
        self._initialize()

    def _initialize(self):
        self._init_flags()
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
            # The compiler used to be clever about the order of
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

        self._compute_flatcall()

        if self.space.config.objspace.std.withmapdict:
            from pypy.objspace.std.mapdict import init_mapdict_cache
            init_mapdict_cache(self)

    def _freeze_(self):
        if (self.magic == cpython_magic and
            '__pypy__' not in sys.builtin_module_names):
            raise Exception("CPython host codes should not be rendered")
        return False

    def _init_flags(self):
        co_code = self.co_code
        next_instr = 0
        while next_instr < len(co_code):
            opcode = ord(co_code[next_instr])
            next_instr += 1
            if opcode >= HAVE_ARGUMENT:
                next_instr += 2
            while opcode == opcodedesc.EXTENDED_ARG.index:
                opcode = ord(co_code[next_instr])
                next_instr += 3
            if opcode == opcodedesc.LOAD_GLOBAL.index:
                self.co_flags |= CO_CONTAINSGLOBALS
            elif opcode == opcodedesc.LOAD_NAME.index:
                self.co_flags |= CO_CONTAINSGLOBALS

    co_names = property(lambda self: [self.space.unwrap(w_name) for w_name in self.co_names_w]) # for trace

    def signature(self):
        return self._signature

    @classmethod
    def _from_code(cls, space, code, hidden_applevel=False, code_hook=None):
        """ Initialize the code object from a real (CPython) one.
            This is just a hack, until we have our own compile.
            At the moment, we just fake this.
            This method is called by our compile builtin function.
        """
        assert isinstance(code, types.CodeType)
        newconsts_w = [None] * len(code.co_consts)
        num = 0
        if code_hook is None:
            code_hook = cls._from_code
        for const in code.co_consts:
            if isinstance(const, types.CodeType): # from stable compiler
                const = code_hook(space, const, hidden_applevel, code_hook)
            newconsts_w[num] = space.wrap(const)
            num += 1
        # stick the underlying CPython magic value, if the code object
        # comes from there
        return cls(space, code.co_argcount,
                      code.co_nlocals,
                      code.co_stacksize,
                      code.co_flags,
                      code.co_code,
                      newconsts_w[:],
                      list(code.co_names),
                      list(code.co_varnames),
                      code.co_filename,
                      code.co_name,
                      code.co_firstlineno,
                      code.co_lnotab,
                      list(code.co_freevars),
                      list(code.co_cellvars),
                      hidden_applevel, cpython_magic)


    def _compute_flatcall(self):
        # Speed hack!
        self.fast_natural_arity = eval.Code.HOPELESS
        if self.co_flags & (CO_VARARGS | CO_VARKEYWORDS):
            return
        if len(self._args_as_cellvars) > 0:
            return
        if self.co_argcount > 0xff:
            return

        self.fast_natural_arity = eval.Code.FLATPYCALL | self.co_argcount

    def funcrun(self, func, args):
        frame = self.space.createframe(self, func.w_func_globals,
                                  func)
        sig = self._signature
        # speed hack
        fresh_frame = jit.hint(frame, access_directly=True,
                                      fresh_virtualizable=True)
        args_matched = args.parse_into_scope(None, fresh_frame.locals_stack_w,
                                             func.name,
                                             sig, func.defs_w)
        fresh_frame.init_cells()
        return frame.run()

    def funcrun_obj(self, func, w_obj, args):
        frame = self.space.createframe(self, func.w_func_globals,
                                  func)
        sig = self._signature
        # speed hack
        fresh_frame = jit.hint(frame, access_directly=True,
                                      fresh_virtualizable=True)
        args_matched = args.parse_into_scope(w_obj, fresh_frame.locals_stack_w,
                                             func.name,
                                             sig, func.defs_w)
        fresh_frame.init_cells()
        return frame.run()

    def getvarnames(self):
        return self.co_varnames

    def getdocstring(self, space):
        if self.co_consts_w:   # it is probably never empty
            w_first = self.co_consts_w[0]
            if space.is_true(space.isinstance(w_first, space.w_basestring)):
                return w_first
        return space.w_None

    def _to_code(self):
        """For debugging only."""
        consts = [None] * len(self.co_consts_w)
        num = 0
        for w in self.co_consts_w:
            if isinstance(w, PyCode):
                consts[num] = w._to_code()
            else:
                consts[num] = self.space.unwrap(w)
            num += 1
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

    def exec_host_bytecode(self, w_globals, w_locals):
        from pypy.interpreter.pyframe import CPythonFrame
        frame = CPythonFrame(self.space, self, w_globals, None)
        frame.setdictscope(w_locals)
        return frame.run()

    def dump(self):
        """A dis.dis() dump of the code object."""
        co = self._to_code()
        dis.dis(co)

    def fget_co_consts(self, space):
        return space.newtuple(self.co_consts_w)

    def fget_co_names(self, space):
        return space.newtuple(self.co_names_w)

    def fget_co_varnames(self, space):
        return space.newtuple([space.wrap(name) for name in self.co_varnames])

    def fget_co_cellvars(self, space):
        return space.newtuple([space.wrap(name) for name in self.co_cellvars])

    def fget_co_freevars(self, space):
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
        result =  compute_hash(self.co_name)
        result ^= self.co_argcount
        result ^= self.co_nlocals
        result ^= self.co_flags
        result ^= self.co_firstlineno
        result ^= compute_hash(self.co_code)
        for name in self.co_varnames:  result ^= compute_hash(name)
        for name in self.co_freevars:  result ^= compute_hash(name)
        for name in self.co_cellvars:  result ^= compute_hash(name)
        w_result = space.wrap(intmask(result))
        for w_name in self.co_names_w:
            w_result = space.xor(w_result, space.hash(w_name))
        for w_const in self.co_consts_w:
            w_result = space.xor(w_result, space.hash(w_const))
        return w_result

    @unwrap_spec(argcount=int, nlocals=int, stacksize=int, flags=int,
                 codestring=str,
                 filename=str, name=str, firstlineno=int,
                 lnotab=str, magic=int)
    def descr_code__new__(space, w_subtype,
                          argcount, nlocals, stacksize, flags,
                          codestring, w_constants, w_names,
                          w_varnames, filename, name, firstlineno,
                          lnotab, w_freevars=NoneNotWrapped,
                          w_cellvars=NoneNotWrapped,
                          magic=default_magic):
        if argcount < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("code: argcount must not be negative"))
        if nlocals < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("code: nlocals must not be negative"))
        if not space.is_true(space.isinstance(w_constants, space.w_tuple)):
            raise OperationError(space.w_TypeError,
                                 space.wrap("Expected tuple for constants"))
        consts_w   = space.fixedview(w_constants)
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
        PyCode.__init__(code, space, argcount, nlocals, stacksize, flags, codestring, consts_w[:], names,
                      varnames, filename, name, firstlineno, lnotab, freevars, cellvars, magic=magic)
        return space.wrap(code)

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
            w(self.magic),
        ]
        return space.newtuple([new_inst, space.newtuple(tup)])

    def get_repr(self):
        return "<code object %s, file '%s', line %d>" % (
            self.co_name, self.co_filename, self.co_firstlineno)

    def repr(self, space):
        return space.wrap(self.get_repr())
