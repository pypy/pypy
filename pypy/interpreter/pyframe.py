""" PyFrame class implementation with the interpreter main loop.
"""

from pypy.tool.pairtype import extendabletype
from pypy.interpreter import eval, baseobjspace, pycode
from pypy.interpreter.argument import Arguments
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter import pytraceback
from pypy.rlib.objectmodel import we_are_translated, instantiate
from pypy.rlib.jit import hint
from pypy.rlib.debug import make_sure_not_resized, check_nonneg
from pypy.rlib.rarithmetic import intmask
from pypy.rlib import jit
from pypy.tool import stdlib_opcode
from pypy.tool.stdlib_opcode import host_bytecode_spec

# Define some opcodes used
g = globals()
for op in '''DUP_TOP POP_TOP SETUP_LOOP SETUP_EXCEPT SETUP_FINALLY
POP_BLOCK END_FINALLY'''.split():
    g[op] = stdlib_opcode.opmap[op]
HAVE_ARGUMENT = stdlib_opcode.HAVE_ARGUMENT

class PyFrame(eval.Frame):
    """Represents a frame for a regular Python function
    that needs to be interpreted.

    See also pyopcode.PyStandardFrame and nestedscope.PyNestedScopeFrame.

    Public fields:
     * 'space' is the object space this frame is running in
     * 'code' is the PyCode object this frame runs
     * 'w_locals' is the locals dictionary to use
     * 'w_globals' is the attached globals dictionary
     * 'builtin' is the attached built-in module
     * 'valuestack_w', 'blockstack', control the interpretation
    """

    __metaclass__ = extendabletype

    frame_finished_execution = False
    last_instr               = -1
    last_exception           = None
    f_backref                = jit.vref_None
    w_f_trace                = None
    # For tracing
    instr_lb                 = 0
    instr_ub                 = 0
    instr_prev_plus_one      = 0
    is_being_profiled        = False
    escaped                  = False  # see mark_as_escaped()

    def __init__(self, space, code, w_globals, outer_func):
        if not we_are_translated():
            assert type(self) in (space.FrameClass, CPythonFrame), (
                "use space.FrameClass(), not directly PyFrame()")
        self = hint(self, access_directly=True, fresh_virtualizable=True)
        assert isinstance(code, pycode.PyCode)
        self.pycode = code
        eval.Frame.__init__(self, space, w_globals)
        self.locals_stack_w = [None] * (code.co_nlocals + code.co_stacksize)
        self.nlocals = code.co_nlocals
        self.valuestackdepth = code.co_nlocals
        self.lastblock = None
        make_sure_not_resized(self.locals_stack_w)
        check_nonneg(self.nlocals)
        #
        if space.config.objspace.honor__builtins__ and w_globals is not None:
            self.builtin = space.builtin.pick_builtin(w_globals)
        # regular functions always have CO_OPTIMIZED and CO_NEWLOCALS.
        # class bodies only have CO_NEWLOCALS.
        self.initialize_frame_scopes(outer_func, code)
        self.f_lineno = code.co_firstlineno

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

    def initialize_frame_scopes(self, outer_func, code):
        # regular functions always have CO_OPTIMIZED and CO_NEWLOCALS.
        # class bodies only have CO_NEWLOCALS.
        # CO_NEWLOCALS: make a locals dict unless optimized is also set
        # CO_OPTIMIZED: no locals dict needed at all
        # NB: this method is overridden in nestedscope.py
        flags = code.co_flags
        if flags & pycode.CO_OPTIMIZED: 
            return 
        if flags & pycode.CO_NEWLOCALS:
            self.w_locals = self.space.newdict(module=True)
        else:
            assert self.w_globals is not None
            self.w_locals = self.w_globals

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
        w_inputvalue is for generator.send()) and operr is for
        generator.throw()).
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
            if operr is not None:
                ec = self.space.getexecutioncontext()
                next_instr = self.handle_operation_error(ec, operr)
                self.last_instr = intmask(next_instr - 1)
            else:
                # Execution starts just after the last_instr.  Initially,
                # last_instr is -1.  After a generator suspends it points to
                # the YIELD_VALUE instruction.
                next_instr = self.last_instr + 1
                if next_instr != 0:
                    self.pushvalue(w_inputvalue)
            #
            try:
                w_exitvalue = self.dispatch(self.pycode, next_instr,
                                            executioncontext)
            except Exception:
                executioncontext.return_trace(self, self.space.w_None)
                raise
            executioncontext.return_trace(self, w_exitvalue)
            # clean up the exception, might be useful for not
            # allocating exception objects in some cases
            self.last_exception = None
            got_exception = False
        finally:
            executioncontext.leave(self, w_exitvalue, got_exception)
        return w_exitvalue
    execute_frame.insert_stack_check_here = True

    # stack manipulation helpers
    def pushvalue(self, w_object):
        depth = self.valuestackdepth
        self.locals_stack_w[depth] = w_object
        self.valuestackdepth = depth + 1

    def popvalue(self):
        depth = self.valuestackdepth - 1
        assert depth >= self.nlocals, "pop from empty value stack"
        w_object = self.locals_stack_w[depth]
        self.locals_stack_w[depth] = None
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
        assert base >= self.nlocals
        while True:
            n -= 1
            if n < 0:
                break
            values_w[n] = self.locals_stack_w[base+n]
        return values_w

    @jit.unroll_safe
    def dropvalues(self, n):
        n = hint(n, promote=True)
        finaldepth = self.valuestackdepth - n
        assert finaldepth >= self.nlocals, "stack underflow in dropvalues()"
        while True:
            n -= 1
            if n < 0:
                break
            self.locals_stack_w[finaldepth+n] = None
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
        assert index >= self.nlocals, "peek past the bottom of the stack"
        return self.locals_stack_w[index]

    def settopvalue(self, w_object, index_from_top=0):
        index_from_top = hint(index_from_top, promote=True)
        index = self.valuestackdepth + ~index_from_top
        assert index >= self.nlocals, "settop past the bottom of the stack"
        self.locals_stack_w[index] = w_object

    @jit.unroll_safe
    def dropvaluesuntil(self, finaldepth):
        depth = self.valuestackdepth - 1
        finaldepth = hint(finaldepth, promote=True)
        while depth >= finaldepth:
            self.locals_stack_w[depth] = None
            depth -= 1
        self.valuestackdepth = finaldepth

    def save_locals_stack(self):
        return self.locals_stack_w[:self.valuestackdepth]

    def restore_locals_stack(self, items_w):
        self.locals_stack_w[:len(items_w)] = items_w
        self.init_cells()
        self.dropvaluesuntil(len(items_w))

    def make_arguments(self, nargs):
        return Arguments(self.space, self.peekvalues(nargs))

    def argument_factory(self, arguments, keywords, keywords_w, w_star, w_starstar):
        return Arguments(self.space, arguments, keywords, keywords_w, w_star, w_starstar)

    @jit.dont_look_inside
    def descr__reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        from pypy.module._pickle_support import maker # helper fns
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('frame_new')
        w        = space.wrap
        nt = space.newtuple

        cells = self._getcells()
        if cells is None:
            w_cells = space.w_None
        else:
            w_cells = space.newlist([space.wrap(cell) for cell in cells])

        if self.w_f_trace is None:
            f_lineno = self.get_last_lineno()
        else:
            f_lineno = self.f_lineno

        values_w = self.locals_stack_w[self.nlocals:self.valuestackdepth]
        w_valuestack = maker.slp_into_tuple_with_nulls(space, values_w)
        
        w_blockstack = nt([block._get_state_(space) for block in self.get_blocklist()])
        w_fastlocals = maker.slp_into_tuple_with_nulls(
            space, self.locals_stack_w[:self.nlocals])
        if self.last_exception is None:
            w_exc_value = space.w_None
            w_tb = space.w_None
        else:
            w_exc_value = self.last_exception.get_w_value(space)
            w_tb = w(self.last_exception.get_traceback())
        
        tup_state = [
            w(self.f_backref()),
            w(self.get_builtin()),
            w(self.pycode),
            w_valuestack,
            w_blockstack,
            w_exc_value, # last_exception
            w_tb,        #
            self.w_globals,
            w(self.last_instr),
            w(self.frame_finished_execution),
            w(f_lineno),
            w_fastlocals,
            space.w_None,           #XXX placeholder for f_locals
            
            #f_restricted requires no additional data!
            space.w_None, ## self.w_f_trace,  ignore for now

            w(self.instr_lb), #do we need these three (that are for tracing)
            w(self.instr_ub),
            w(self.instr_prev_plus_one),
            w_cells,
            ]

        return nt([new_inst, nt([]), nt(tup_state)])

    @jit.dont_look_inside
    def descr__setstate__(self, space, w_args):
        from pypy.module._pickle_support import maker # helper fns
        from pypy.interpreter.pycode import PyCode
        from pypy.interpreter.module import Module
        args_w = space.unpackiterable(w_args)
        w_f_back, w_builtin, w_pycode, w_valuestack, w_blockstack, w_exc_value, w_tb,\
            w_globals, w_last_instr, w_finished, w_f_lineno, w_fastlocals, w_f_locals, \
            w_f_trace, w_instr_lb, w_instr_ub, w_instr_prev_plus_one, w_cells = args_w

        new_frame = self
        pycode = space.interp_w(PyCode, w_pycode)

        if space.is_w(w_cells, space.w_None):
            closure = None
            cellvars = []
        else:
            from pypy.interpreter.nestedscope import Cell
            cells_w = space.unpackiterable(w_cells)
            cells = [space.interp_w(Cell, w_cell) for w_cell in cells_w]
            ncellvars = len(pycode.co_cellvars)
            cellvars = cells[:ncellvars]
            closure = cells[ncellvars:]
        
        # do not use the instance's __init__ but the base's, because we set
        # everything like cells from here
        # XXX hack
        from pypy.interpreter.function import Function
        outer_func = Function(space, None, closure=closure,
                             forcename="fake")
        PyFrame.__init__(self, space, pycode, w_globals, outer_func)
        f_back = space.interp_w(PyFrame, w_f_back, can_be_None=True)
        new_frame.f_backref = jit.non_virtual_ref(f_back)

        new_frame.builtin = space.interp_w(Module, w_builtin)
        new_frame.set_blocklist([unpickle_block(space, w_blk)
                                 for w_blk in space.unpackiterable(w_blockstack)])
        values_w = maker.slp_from_tuple_with_nulls(space, w_valuestack)
        for w_value in values_w:
            new_frame.pushvalue(w_value)
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
        new_frame.f_lineno = space.int_w(w_f_lineno)
        fastlocals_w = maker.slp_from_tuple_with_nulls(space, w_fastlocals)
        new_frame.locals_stack_w[:len(fastlocals_w)] = fastlocals_w

        if space.is_w(w_f_trace, space.w_None):
            new_frame.w_f_trace = None
        else:
            new_frame.w_f_trace = w_f_trace

        new_frame.instr_lb = space.int_w(w_instr_lb)   #the three for tracing
        new_frame.instr_ub = space.int_w(w_instr_ub)
        new_frame.instr_prev_plus_one = space.int_w(w_instr_prev_plus_one)

        self._setcellvars(cellvars)
        # XXX what if the frame is in another thread??
        space.frame_trace_action.fire()

    def hide(self):
        return self.pycode.hidden_applevel

    def getcode(self):
        return hint(self.pycode, promote=True)

    @jit.dont_look_inside
    def getfastscope(self):
        "Get the fast locals as a list."
        return self.locals_stack_w

    @jit.dont_look_inside
    def setfastscope(self, scope_w):
        """Initialize the fast locals from a list of values,
        where the order is according to self.pycode.signature()."""
        scope_len = len(scope_w)
        if scope_len > self.nlocals:
            raise ValueError, "new fastscope is longer than the allocated area"
        # don't assign directly to 'locals_stack_w[:scope_len]' to be
        # virtualizable-friendly
        for i in range(scope_len):
            self.locals_stack_w[i] = scope_w[i]
        self.init_cells()

    def init_cells(self):
        """Initialize cellvars from self.locals_stack_w.
        This is overridden in nestedscope.py"""
        pass

    def getfastscopelength(self):
        return self.nlocals

    def getclosure(self):
        return None

    def _getcells(self):
        return None

    def _setcellvars(self, cellvars):
        pass

    ### line numbers ###

    def fget_f_lineno(self, space): 
        "Returns the line number of the instruction currently being executed."
        if self.w_f_trace is None:
            return space.wrap(self.get_last_lineno())
        else:
            return space.wrap(self.f_lineno)

    def fset_f_lineno(self, space, w_new_lineno):
        "Returns the line number of the instruction currently being executed."
        try:
            new_lineno = space.int_w(w_new_lineno)
        except OperationError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap("lineno must be an integer"))
            
        if self.w_f_trace is None:
            raise OperationError(space.w_ValueError,
                  space.wrap("f_lineno can only be set by a trace function."))

        line = self.pycode.co_firstlineno
        if new_lineno < line:
            raise operationerrfmt(space.w_ValueError,
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
            raise operationerrfmt(space.w_ValueError,
                  "line %d comes after the current code.", new_lineno)

        # Don't jump to a line with an except in it.
        code = self.pycode.co_code
        if ord(code[new_lasti]) in (DUP_TOP, POP_TOP):
            raise OperationError(space.w_ValueError,
                  space.wrap("can't jump to 'except' line as there's no exception"))
            
        # Don't jump into or out of a finally block.
        f_lasti_setup_addr = -1
        new_lasti_setup_addr = -1
        blockstack = []
        addr = 0
        while addr < len(code):
            op = ord(code[addr])
            if op in (SETUP_LOOP, SETUP_EXCEPT, SETUP_FINALLY):
                blockstack.append([addr, False])
            elif op == POP_BLOCK:
                setup_op = ord(code[blockstack[-1][0]])
                if setup_op == SETUP_FINALLY:
                    blockstack[-1][1] = True
                else:
                    blockstack.pop()
            elif op == END_FINALLY:
                if len(blockstack) > 0:
                    setup_op = ord(code[blockstack[-1][0]])
                    if setup_op == SETUP_FINALLY:
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
            raise operationerrfmt(space.w_ValueError,
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

            if op in (SETUP_LOOP, SETUP_EXCEPT, SETUP_FINALLY):
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
            raise OperationError(space.w_ValueError,
                                 space.wrap("can't jump into the middle of a block"))

        while f_iblock > new_iblock:
            block = self.pop_block()
            block.cleanup(self)
            f_iblock -= 1
            
        self.f_lineno = new_lineno
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
        return self.w_f_trace

    def fset_f_trace(self, space, w_trace):
        if space.is_w(w_trace, space.w_None):
            self.w_f_trace = None
        else:
            self.w_f_trace = w_trace
            self.f_lineno = self.get_last_lineno()
            space.frame_trace_action.fire()

    def fdel_f_trace(self, space): 
        self.w_f_trace = None 

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

class CPythonFrame(PyFrame):
    """
    Execution of host (CPython) opcodes.
    """

    bytecode_spec = host_bytecode_spec
    opcode_method_names = host_bytecode_spec.method_names
    opcodedesc = host_bytecode_spec.opcodedesc
    opdescmap = host_bytecode_spec.opdescmap
    HAVE_ARGUMENT = host_bytecode_spec.HAVE_ARGUMENT


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
    blk = instantiate(get_block_class(opname))
    blk.handlerposition = handlerposition
    blk.valuestackdepth = valuestackdepth
    return blk
