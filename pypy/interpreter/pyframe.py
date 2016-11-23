""" PyFrame class implementation with the interpreter main loop.
"""

import sys
from rpython.rlib import jit, rstm
from rpython.rlib.debug import make_sure_not_resized, check_nonneg
from rpython.rlib.jit import hint
from rpython.rlib.objectmodel import instantiate, specialize, we_are_translated
from rpython.rlib.rarithmetic import intmask, r_uint
from rpython.tool.pairtype import extendabletype

from pypy.interpreter import pycode, pytraceback
from pypy.interpreter.argument import Arguments
from pypy.interpreter.astcompiler import consts
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import (
    OperationError, get_cleared_operation_error, oefmt)
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.nestedscope import Cell
from pypy.tool import stdlib_opcode

# Define some opcodes used
for op in '''DUP_TOP POP_TOP SETUP_LOOP SETUP_EXCEPT SETUP_FINALLY SETUP_WITH
POP_BLOCK END_FINALLY'''.split():
    globals()[op] = stdlib_opcode.opmap[op]
HAVE_ARGUMENT = stdlib_opcode.HAVE_ARGUMENT

class FrameDebugData(object):
    """ A small object that holds debug data for tracing
    """
    w_f_trace                = None
    instr_lb                 = 0
    instr_ub                 = 0
    instr_prev_plus_one      = 0
    f_lineno                 = 0      # current lineno for tracing
    is_being_profiled        = False
    w_locals                 = None

    def __init__(self, pycode):
        self.f_lineno = pycode.co_firstlineno
        self.w_globals = pycode.w_globals

class PyFrame(W_Root):
    """Represents a frame for a regular Python function
    that needs to be interpreted.

    Public fields:
     * 'space' is the object space this frame is running in
     * 'code' is the PyCode object this frame runs
     * 'w_locals' is the locals dictionary to use, if needed, stored on a
       debug object
     * 'w_globals' is the attached globals dictionary
     * 'builtin' is the attached built-in module
     * 'valuestack_w', 'blockstack', control the interpretation

    Cell Vars:
        my local variables that are exposed to my inner functions
    Free Vars:
        variables coming from a parent function in which i'm nested
    'closure' is a list of Cell instances: the received free vars.
    """

    __metaclass__ = extendabletype

    _immutable_fields_ = ['pycode', 'locals_stack_w', 'cells']
    # note: 'locals_stack_w' is immutable because it contains always the
    # same list, but what the list itself contains changes

    frame_finished_execution = False
    last_instr               = -1
    last_exception           = None
    f_backref                = jit.vref_None
    
    escaped                  = False  # see mark_as_escaped()
    debugdata                = None

    pycode = None # code object executed by that frame
    locals_cells_stack_w = None # the list of all locals, cells and the valuestack
    valuestackdepth = 0 # number of items on valuestack
    lastblock = None

    # other fields:
    
    # builtin - builtin cache, only if honor__builtins__ is True
    # defaults to False

    # there is also self.space which is removed by the annotator

    # additionally JIT uses vable_token field that is representing
    # frame current virtualizable state as seen by the JIT

    def __init__(self, space, code, w_globals, outer_func):
        if not we_are_translated():
            assert type(self) == space.FrameClass, (
                "use space.FrameClass(), not directly PyFrame()")
        self = hint(self, access_directly=True, fresh_virtualizable=True)
        assert isinstance(code, pycode.PyCode)
        self.space = space
        self.pycode = code
        if code.frame_stores_global(w_globals):
            self.getorcreatedebug().w_globals = w_globals
        ncellvars = len(code.co_cellvars)
        nfreevars = len(code.co_freevars)
        size = code.co_nlocals + ncellvars + nfreevars + code.co_stacksize
        # the layout of this list is as follows:
        # | local vars | cells | stack |
        self.locals_cells_stack_w = [None] * size
        self.valuestackdepth = code.co_nlocals + ncellvars + nfreevars
        make_sure_not_resized(self.locals_cells_stack_w)
        check_nonneg(self.valuestackdepth)
        #
        if space.config.objspace.honor__builtins__:
            self.builtin = space.builtin.pick_builtin(w_globals)
        # regular functions always have CO_OPTIMIZED and CO_NEWLOCALS.
        # class bodies only have CO_NEWLOCALS.
        self.initialize_frame_scopes(outer_func, code)

    def getdebug(self):
        return self.debugdata

    def getorcreatedebug(self):
        if self.debugdata is None:
            self.debugdata = FrameDebugData(self.pycode)
        return self.debugdata

    def get_w_globals(self):
        debugdata = self.getdebug()
        if debugdata is not None:
            return debugdata.w_globals
        return jit.promote(self.pycode).w_globals

    def get_w_f_trace(self):
        d = self.getdebug()
        if d is None:
            return None
        return d.w_f_trace

    def get_is_being_profiled(self):
        d = self.getdebug()
        if d is None:
            return False
        return d.is_being_profiled

    def get_w_locals(self):
        d = self.getdebug()
        if d is None:
            return None
        return d.w_locals

    def __repr__(self):
        # NOT_RPYTHON: useful in tracebacks
        return "<%s.%s executing %s at line %s" % (
            self.__class__.__module__, self.__class__.__name__,
            self.pycode, self.get_last_lineno())

    def _getcell(self, varindex):
        cell = self.locals_cells_stack_w[varindex + self.pycode.co_nlocals]
        assert isinstance(cell, Cell)
        return cell

    def mark_as_escaped(self):
        """
        Must be called on frames that are exposed to applevel, e.g. by
        sys._getframe().  This ensures that the virtualref holding the frame
        is properly forced by ec.leave(), and thus the frame will be still
        accessible even after the corresponding C stack died.
        """
        self.escaped = True

    def append_block(self, block):
        assert block.previous is self.lastblock
        self.lastblock = block

    def pop_block(self):
        block = self.lastblock
        self.lastblock = block.previous
        return block

    def blockstack_non_empty(self):
        return self.lastblock is not None

    def get_blocklist(self):
        """Returns a list containing all the blocks in the frame"""
        lst = []
        block = self.lastblock
        while block is not None:
            lst.append(block)
            block = block.previous
        return lst

    def set_blocklist(self, lst):
        self.lastblock = None
        i = len(lst) - 1
        while i >= 0:
            block = lst[i]
            i -= 1
            block.previous = self.lastblock
            self.lastblock = block

    def get_builtin(self):
        if self.space.config.objspace.honor__builtins__:
            return self.builtin
        else:
            return self.space.builtin

    @jit.unroll_safe
    def initialize_frame_scopes(self, outer_func, code):
        # regular functions always have CO_OPTIMIZED and CO_NEWLOCALS.
        # class bodies only have CO_NEWLOCALS.
        # CO_NEWLOCALS: make a locals dict unless optimized is also set
        # CO_OPTIMIZED: no locals dict needed at all
        flags = code.co_flags
        if not (flags & pycode.CO_OPTIMIZED):
            if flags & pycode.CO_NEWLOCALS:
                self.getorcreatedebug().w_locals = self.space.newdict(module=True)
            else:
                w_globals = self.get_w_globals()
                assert w_globals is not None
                self.getorcreatedebug().w_locals = w_globals

        ncellvars = len(code.co_cellvars)
        nfreevars = len(code.co_freevars)
        if not nfreevars:
            if not ncellvars:
                return            # no cells needed - fast path
        elif outer_func is None:
            space = self.space
            raise oefmt(space.w_TypeError,
                        "directly executed code object may not contain free "
                        "variables")
        if outer_func and outer_func.closure:
            closure_size = len(outer_func.closure)
        else:
            closure_size = 0
        if closure_size != nfreevars:
            raise ValueError("code object received a closure with "
                                 "an unexpected number of free variables")
        index = code.co_nlocals
        for i in range(ncellvars):
            self.locals_cells_stack_w[index] = Cell()
            index += 1
        for i in range(nfreevars):
            self.locals_cells_stack_w[index] = outer_func.closure[i]
            index += 1

    def run(self):
        """Start this frame's execution."""
        if self.getcode().co_flags & pycode.CO_GENERATOR:
            from pypy.interpreter.generator import GeneratorIterator
            return self.space.wrap(GeneratorIterator(self))
        else:
            return self.execute_frame()

    def execute_frame(self, w_inputvalue=None, operr=None):
        """Execute this frame.  Main entry point to the interpreter.
        The optional arguments are there to handle a generator's frame:
        w_inputvalue is for generator.send() and operr is for
        generator.throw().
        """
        # the following 'assert' is an annotation hint: it hides from
        # the annotator all methods that are defined in PyFrame but
        # overridden in the {,Host}FrameClass subclasses of PyFrame.
        assert (isinstance(self, self.space.FrameClass) or
                not self.space.config.translating)
        executioncontext = self.space.getexecutioncontext()
        executioncontext.enter(self)
        got_exception = True
        w_exitvalue = self.space.w_None
        try:
            executioncontext.call_trace(self)
            #
            try:
                if operr is not None:
                    ec = self.space.getexecutioncontext()
                    next_instr = self.handle_operation_error(ec, operr)
                    self.last_instr = intmask(next_instr - 1)
                else:
                    # Execution starts just after the last_instr.  Initially,
                    # last_instr is -1.  After a generator suspends it points to
                    # the YIELD_VALUE instruction.
                    next_instr = r_uint(self.last_instr + 1)
                    if next_instr != 0:
                        self.pushvalue(w_inputvalue)
                w_exitvalue = self.dispatch(self.pycode, next_instr,
                                            executioncontext)
            except OperationError:
                raise
            except Exception as e:      # general fall-back
                raise self._convert_unexpected_exception(e)
            finally:
                executioncontext.return_trace(self, w_exitvalue)
            # it used to say self.last_exception = None
            # this is now done by the code in pypyjit module
            # since we don't want to invalidate the virtualizable
            # for no good reason
            got_exception = False
        finally:
            executioncontext.leave(self, w_exitvalue, got_exception)
        return w_exitvalue
    execute_frame.insert_stack_check_here = True

    # stack manipulation helpers
    def pushvalue(self, w_object):
        depth = self.valuestackdepth
        self.locals_cells_stack_w[depth] = w_object
        self.valuestackdepth = depth + 1

    def _check_stack_index(self, index):
        # will be completely removed by the optimizer if only used in an assert
        # and if asserts are disabled
        code = self.pycode
        ncellvars = len(code.co_cellvars)
        nfreevars = len(code.co_freevars)
        stackstart = code.co_nlocals + ncellvars + nfreevars
        return index >= stackstart

    def popvalue(self):
        depth = self.valuestackdepth - 1
        assert self._check_stack_index(depth)
        assert depth >= 0
        w_object = self.locals_cells_stack_w[depth]
        self.locals_cells_stack_w[depth] = None
        self.valuestackdepth = depth
        return w_object


    # we need two popvalues that return different data types:
    # one in case we want list another in case of tuple
    def _new_popvalues():
        @jit.unroll_safe
        def popvalues(self, n):
            values_w = [None] * n
            while True:
                n -= 1
                if n < 0:
                    break
                values_w[n] = self.popvalue()
            return values_w
        return popvalues
    popvalues = _new_popvalues()
    popvalues_mutable = _new_popvalues()
    del _new_popvalues

    @jit.unroll_safe
    def peekvalues(self, n):
        values_w = [None] * n
        base = self.valuestackdepth - n
        assert self._check_stack_index(base)
        assert base >= 0
        while True:
            n -= 1
            if n < 0:
                break
            values_w[n] = self.locals_cells_stack_w[base+n]
        return values_w

    @jit.unroll_safe
    def dropvalues(self, n):
        n = hint(n, promote=True)
        finaldepth = self.valuestackdepth - n
        assert self._check_stack_index(finaldepth)
        assert finaldepth >= 0
        while True:
            n -= 1
            if n < 0:
                break
            self.locals_cells_stack_w[finaldepth+n] = None
        self.valuestackdepth = finaldepth

    @jit.unroll_safe
    def pushrevvalues(self, n, values_w): # n should be len(values_w)
        make_sure_not_resized(values_w)
        while True:
            n -= 1
            if n < 0:
                break
            self.pushvalue(values_w[n])

    @jit.unroll_safe
    def dupvalues(self, n):
        delta = n-1
        while True:
            n -= 1
            if n < 0:
                break
            w_value = self.peekvalue(delta)
            self.pushvalue(w_value)

    def peekvalue(self, index_from_top=0):
        # NOTE: top of the stack is peekvalue(0).
        # Contrast this with CPython where it's PEEK(-1).
        index_from_top = hint(index_from_top, promote=True)
        index = self.valuestackdepth + ~index_from_top
        assert self._check_stack_index(index)
        assert index >= 0
        return self.locals_cells_stack_w[index]

    def settopvalue(self, w_object, index_from_top=0):
        index_from_top = hint(index_from_top, promote=True)
        index = self.valuestackdepth + ~index_from_top
        assert self._check_stack_index(index)
        assert index >= 0
        self.locals_cells_stack_w[index] = w_object

    @jit.unroll_safe
    def dropvaluesuntil(self, finaldepth):
        depth = self.valuestackdepth - 1
        finaldepth = hint(finaldepth, promote=True)
        assert finaldepth >= 0
        while depth >= finaldepth:
            self.locals_cells_stack_w[depth] = None
            depth -= 1
        self.valuestackdepth = finaldepth

    def make_arguments(self, nargs, methodcall=False):
        return Arguments(
                self.space, self.peekvalues(nargs), methodcall=methodcall)

    def argument_factory(self, arguments, keywords, keywords_w, w_star, w_starstar, methodcall=False):
        return Arguments(
                self.space, arguments, keywords, keywords_w, w_star,
                w_starstar, methodcall=methodcall)

    @jit.dont_look_inside
    def descr__reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('frame_new')
        w_tup_state = self._reduce_state(space)
        nt = space.newtuple
        return nt([new_inst, nt([]), w_tup_state])

    @jit.dont_look_inside
    def _reduce_state(self, space):
        from pypy.module._pickle_support import maker # helper fns
        w = space.wrap
        nt = space.newtuple

        if self.get_w_f_trace() is None:
            f_lineno = self.get_last_lineno()
        else:
            f_lineno = self.getorcreatedebug().f_lineno

        nlocals = self.pycode.co_nlocals
        values_w = self.locals_cells_stack_w
        w_locals_cells_stack = maker.slp_into_tuple_with_nulls(space, values_w)

        w_blockstack = nt([block._get_state_(space) for block in self.get_blocklist()])
        if self.last_exception is None:
            w_exc_value = space.w_None
            w_tb = space.w_None
        else:
            w_exc_value = self.last_exception.get_w_value(space)
            w_tb = w(self.last_exception.get_traceback())

        d = self.getorcreatedebug()
        tup_state = [
            w(self.f_backref()),
            w(self.get_builtin()),
            w(self.pycode),
            w_locals_cells_stack,
            w_blockstack,
            w_exc_value, # last_exception
            w_tb,        #
            self.get_w_globals(),
            w(self.last_instr),
            w(self.frame_finished_execution),
            w(f_lineno),
            space.w_None,           #XXX placeholder for f_locals

            #f_restricted requires no additional data!
            space.w_None,

            w(d.instr_lb),
            w(d.instr_ub),
            w(d.instr_prev_plus_one),
            w(self.valuestackdepth),
            ]
        return nt(tup_state)

    @jit.dont_look_inside
    def descr__setstate__(self, space, w_args):
        from pypy.module._pickle_support import maker # helper fns
        from pypy.interpreter.pycode import PyCode
        from pypy.interpreter.module import Module
        args_w = space.unpackiterable(w_args, 17)
        w_f_back, w_builtin, w_pycode, w_locals_cells_stack, w_blockstack, w_exc_value, w_tb,\
            w_globals, w_last_instr, w_finished, w_f_lineno, w_f_locals, \
            w_f_trace, w_instr_lb, w_instr_ub, w_instr_prev_plus_one, w_stackdepth = args_w

        new_frame = self
        pycode = space.interp_w(PyCode, w_pycode)

        values_w = maker.slp_from_tuple_with_nulls(space, w_locals_cells_stack)
        nfreevars = len(pycode.co_freevars)
        closure = None
        if nfreevars:
            base = pycode.co_nlocals + len(pycode.co_cellvars)
            closure = values_w[base: base + nfreevars]

        # do not use the instance's __init__ but the base's, because we set
        # everything like cells from here
        # XXX hack
        from pypy.interpreter.function import Function
        outer_func = Function(space, None, closure=closure,
                             forcename="fake")
        PyFrame.__init__(self, space, pycode, w_globals, outer_func)
        f_back = space.interp_w(PyFrame, w_f_back, can_be_None=True)
        new_frame.f_backref = jit.non_virtual_ref(f_back)

        if space.config.objspace.honor__builtins__:
            new_frame.builtin = space.interp_w(Module, w_builtin)
        else:
            assert space.interp_w(Module, w_builtin) is space.builtin
        new_frame.set_blocklist([unpickle_block(space, w_blk)
                                 for w_blk in space.unpackiterable(w_blockstack)])
        self.locals_cells_stack_w = values_w[:]
        valuestackdepth = space.int_w(w_stackdepth)
        if not self._check_stack_index(valuestackdepth):
            raise oefmt(space.w_ValueError, "invalid stackdepth")
        assert valuestackdepth >= 0
        self.valuestackdepth = valuestackdepth
        if space.is_w(w_exc_value, space.w_None):
            new_frame.last_exception = None
        else:
            from pypy.interpreter.pytraceback import PyTraceback
            tb = space.interp_w(PyTraceback, w_tb)
            new_frame.last_exception = OperationError(space.type(w_exc_value),
                                                      w_exc_value, tb
                                                      )
        new_frame.last_instr = space.int_w(w_last_instr)
        new_frame.frame_finished_execution = space.is_true(w_finished)
        d = new_frame.getorcreatedebug()
        d.f_lineno = space.int_w(w_f_lineno)

        if space.is_w(w_f_trace, space.w_None):
            d.w_f_trace = None
        else:
            d.w_f_trace = w_f_trace

        d.instr_lb = space.int_w(w_instr_lb)   #the three for tracing
        d.instr_ub = space.int_w(w_instr_ub)
        d.instr_prev_plus_one = space.int_w(w_instr_prev_plus_one)

    def hide(self):
        return self.pycode.hidden_applevel

    def getcode(self):
        return hint(self.pycode, promote=True)

    @jit.look_inside_iff(lambda self, scope_w: jit.isvirtual(scope_w))
    def setfastscope(self, scope_w):
        """Initialize the fast locals from a list of values,
        where the order is according to self.pycode.signature()."""
        scope_len = len(scope_w)
        if scope_len > self.pycode.co_nlocals:
            raise ValueError("new fastscope is longer than the allocated area")
        # don't assign directly to 'locals_cells_stack_w[:scope_len]' to be
        # virtualizable-friendly
        for i in range(scope_len):
            self.locals_cells_stack_w[i] = scope_w[i]
        self.init_cells()

    def getdictscope(self):
        """
        Get the locals as a dictionary
        """
        self.fast2locals()
        return self.debugdata.w_locals

    def setdictscope(self, w_locals):
        """
        Initialize the locals from a dictionary.
        """
        self.getorcreatedebug().w_locals = w_locals
        self.locals2fast()

    @jit.unroll_safe
    def fast2locals(self):
        # Copy values from the fastlocals to self.w_locals
        d = self.getorcreatedebug()
        if d.w_locals is None:
            d.w_locals = self.space.newdict()
        varnames = self.getcode().getvarnames()
        for i in range(min(len(varnames), self.getcode().co_nlocals)):
            name = varnames[i]
            w_value = self.locals_cells_stack_w[i]
            if w_value is not None:
                self.space.setitem_str(d.w_locals, name, w_value)
            else:
                w_name = self.space.wrap(name)
                try:
                    self.space.delitem(d.w_locals, w_name)
                except OperationError as e:
                    if not e.match(self.space, self.space.w_KeyError):
                        raise

        # cellvars are values exported to inner scopes
        # freevars are values coming from outer scopes
        # (see locals2fast for why CO_OPTIMIZED)
        freevarnames = self.pycode.co_cellvars
        if self.pycode.co_flags & consts.CO_OPTIMIZED:
            freevarnames = freevarnames + self.pycode.co_freevars
        for i in range(len(freevarnames)):
            name = freevarnames[i]
            cell = self._getcell(i)
            try:
                w_value = cell.get()
            except ValueError:
                pass
            else:
                self.space.setitem_str(d.w_locals, name, w_value)


    @jit.unroll_safe
    def locals2fast(self):
        # Copy values from self.w_locals to the fastlocals
        w_locals = self.getorcreatedebug().w_locals
        assert w_locals is not None
        varnames = self.getcode().getvarnames()
        numlocals = self.getcode().co_nlocals

        new_fastlocals_w = [None] * numlocals

        for i in range(min(len(varnames), numlocals)):
            name = varnames[i]
            w_value = self.space.finditem_str(w_locals, name)
            if w_value is not None:
                new_fastlocals_w[i] = w_value

        self.setfastscope(new_fastlocals_w)

        freevarnames = self.pycode.co_cellvars
        if self.pycode.co_flags & consts.CO_OPTIMIZED:
            freevarnames = freevarnames + self.pycode.co_freevars
            # If the namespace is unoptimized, then one of the
            # following cases applies:
            # 1. It does not contain free variables, because it
            #    uses import * or is a top-level namespace.
            # 2. It is a class namespace.
            # We don't want to accidentally copy free variables
            # into the locals dict used by the class.
        for i in range(len(freevarnames)):
            name = freevarnames[i]
            cell = self._getcell(i)
            w_value = self.space.finditem_str(w_locals, name)
            if w_value is not None:
                cell.set(w_value)

    @jit.unroll_safe
    def init_cells(self):
        """
        Initialize cellvars from self.locals_cells_stack_w.
        """
        args_to_copy = self.pycode._args_as_cellvars
        index = self.pycode.co_nlocals
        for i in range(len(args_to_copy)):
            argnum = args_to_copy[i]
            if argnum >= 0:
                cell = self.locals_cells_stack_w[index]
                assert isinstance(cell, Cell)
                cell.set(self.locals_cells_stack_w[argnum])
            index += 1

    def getclosure(self):
        return None

    def fget_code(self, space):
        return space.wrap(self.getcode())

    def fget_getdictscope(self, space):
        return self.getdictscope()

    def fget_w_globals(self, space):
        # bit silly, but GetSetProperty passes a space
        return self.get_w_globals()


    ### line numbers ###

    def fget_f_lineno(self, space):
        "Returns the line number of the instruction currently being executed."
        if self.get_w_f_trace() is None:
            return space.wrap(self.get_last_lineno())
        else:
            return space.wrap(self.getorcreatedebug().f_lineno)

    def fset_f_lineno(self, space, w_new_lineno):
        "Returns the line number of the instruction currently being executed."
        try:
            new_lineno = space.int_w(w_new_lineno)
        except OperationError:
            raise oefmt(space.w_ValueError, "lineno must be an integer")

        if self.get_w_f_trace() is None:
            raise oefmt(space.w_ValueError,
                        "f_lineno can only be set by a trace function.")

        line = self.pycode.co_firstlineno
        if new_lineno < line:
            raise oefmt(space.w_ValueError,
                        "line %d comes before the current code.", new_lineno)
        elif new_lineno == line:
            new_lasti = 0
        else:
            new_lasti = -1
            addr = 0
            lnotab = self.pycode.co_lnotab
            for offset in xrange(0, len(lnotab), 2):
                addr += ord(lnotab[offset])
                line += ord(lnotab[offset + 1])
                if line >= new_lineno:
                    new_lasti = addr
                    new_lineno = line
                    break

        if new_lasti == -1:
            raise oefmt(space.w_ValueError,
                        "line %d comes after the current code.", new_lineno)

        # Don't jump to a line with an except in it.
        code = self.pycode.co_code
        if ord(code[new_lasti]) in (DUP_TOP, POP_TOP):
            raise oefmt(space.w_ValueError,
                        "can't jump to 'except' line as there's no exception")

        # Don't jump into or out of a finally block.
        f_lasti_setup_addr = -1
        new_lasti_setup_addr = -1
        blockstack = []
        addr = 0
        while addr < len(code):
            op = ord(code[addr])
            if op in (SETUP_LOOP, SETUP_EXCEPT, SETUP_FINALLY, SETUP_WITH):
                blockstack.append([addr, False])
            elif op == POP_BLOCK:
                setup_op = ord(code[blockstack[-1][0]])
                if setup_op == SETUP_FINALLY or setup_op == SETUP_WITH:
                    blockstack[-1][1] = True
                else:
                    blockstack.pop()
            elif op == END_FINALLY:
                if len(blockstack) > 0:
                    setup_op = ord(code[blockstack[-1][0]])
                    if setup_op == SETUP_FINALLY or setup_op == SETUP_WITH:
                        blockstack.pop()

            if addr == new_lasti or addr == self.last_instr:
                for ii in range(len(blockstack)):
                    setup_addr, in_finally = blockstack[~ii]
                    if in_finally:
                        if addr == new_lasti:
                            new_lasti_setup_addr = setup_addr
                        if addr == self.last_instr:
                            f_lasti_setup_addr = setup_addr
                        break

            if op >= HAVE_ARGUMENT:
                addr += 3
            else:
                addr += 1

        assert len(blockstack) == 0

        if new_lasti_setup_addr != f_lasti_setup_addr:
            raise oefmt(space.w_ValueError,
                        "can't jump into or out of a 'finally' block %d -> %d",
                        f_lasti_setup_addr, new_lasti_setup_addr)

        if new_lasti < self.last_instr:
            min_addr = new_lasti
            max_addr = self.last_instr
        else:
            min_addr = self.last_instr
            max_addr = new_lasti

        delta_iblock = min_delta_iblock = 0
        addr = min_addr
        while addr < max_addr:
            op = ord(code[addr])

            if op in (SETUP_LOOP, SETUP_EXCEPT, SETUP_FINALLY, SETUP_WITH):
                delta_iblock += 1
            elif op == POP_BLOCK:
                delta_iblock -= 1
                if delta_iblock < min_delta_iblock:
                    min_delta_iblock = delta_iblock

            if op >= stdlib_opcode.HAVE_ARGUMENT:
                addr += 3
            else:
                addr += 1

        f_iblock = 0
        block = self.lastblock
        while block:
            f_iblock += 1
            block = block.previous
        min_iblock = f_iblock + min_delta_iblock
        if new_lasti > self.last_instr:
            new_iblock = f_iblock + delta_iblock
        else:
            new_iblock = f_iblock - delta_iblock

        if new_iblock > min_iblock:
            raise oefmt(space.w_ValueError,
                        "can't jump into the middle of a block")

        while f_iblock > new_iblock:
            block = self.pop_block()
            block.cleanup(self)
            f_iblock -= 1

        self.getorcreatedebug().f_lineno = new_lineno
        self.last_instr = new_lasti

    def get_last_lineno(self):
        "Returns the line number of the instruction currently being executed."
        return pytraceback.offset2lineno(self.pycode, self.last_instr)

    def fget_f_builtins(self, space):
        return self.get_builtin().getdict(space)

    def fget_f_back(self, space):
        f_back = ExecutionContext.getnextframe_nohidden(self)
        return self.space.wrap(f_back)

    def fget_f_lasti(self, space):
        return self.space.wrap(self.last_instr)

    def fget_f_trace(self, space):
        return self.get_w_f_trace()

    def fset_f_trace(self, space, w_trace):
        if space.is_w(w_trace, space.w_None):
            self.getorcreatedebug().w_f_trace = None
        else:
            d = self.getorcreatedebug()
            d.w_f_trace = w_trace
            d.f_lineno = self.get_last_lineno()

    def fdel_f_trace(self, space):
        self.getorcreatedebug().w_f_trace = None

    def fget_f_exc_type(self, space):
        if self.last_exception is not None:
            f = self.f_backref()
            while f is not None and f.last_exception is None:
                f = f.f_backref()
            if f is not None:
                return f.last_exception.w_type
        return space.w_None

    def fget_f_exc_value(self, space):
        if self.last_exception is not None:
            f = self.f_backref()
            while f is not None and f.last_exception is None:
                f = f.f_backref()
            if f is not None:
                return f.last_exception.get_w_value(space)
        return space.w_None

    def fget_f_exc_traceback(self, space):
        if self.last_exception is not None:
            f = self.f_backref()
            while f is not None and f.last_exception is None:
                f = f.f_backref()
            if f is not None:
                return space.wrap(f.last_exception.get_traceback())
        return space.w_None

    def fget_f_restricted(self, space):
        if space.config.objspace.honor__builtins__:
            return space.wrap(self.builtin is not space.builtin)
        return space.w_False

    @jit.unroll_safe
    @specialize.arg(2)
    def _exc_info_unroll(self, space, for_hidden=False):
        """Return the most recent OperationError being handled in the
        call stack
        """
        frame = self
        while frame:
            last = frame.last_exception
            if last is not None:
                if last is get_cleared_operation_error(self.space):
                    break
                if for_hidden or not frame.hide():
                    return last
            frame = frame.f_backref()
        return None

    def _convert_unexpected_exception(self, e):
        from pypy.interpreter import error

        operr = error.get_converted_unexpected_exception(self.space, e)
        pytraceback.record_application_traceback(
            self.space, operr, self, self.last_instr)
        raise operr

# ____________________________________________________________

def get_block_class(opname):
    # select the appropriate kind of block
    from pypy.interpreter.pyopcode import block_classes
    return block_classes[opname]

def unpickle_block(space, w_tup):
    w_opname, w_handlerposition, w_valuestackdepth = space.unpackiterable(w_tup)
    opname = space.str_w(w_opname)
    handlerposition = space.int_w(w_handlerposition)
    valuestackdepth = space.int_w(w_valuestackdepth)
    assert valuestackdepth >= 0
    assert handlerposition >= 0
    blk = instantiate(get_block_class(opname))
    blk.handlerposition = handlerposition
    blk.valuestackdepth = valuestackdepth
    return blk
