"""
Implementation of a part of the standard Python opcodes.

The rest, dealing with variables in optimized ways, is in nestedscope.py.
"""

from rpython.rlib import jit, rstackovf
from rpython.rlib.debug import check_nonneg
from rpython.rlib.objectmodel import (we_are_translated, always_inline,
        dont_inline)
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.tool.sourcetools import func_with_new_name

from pypy.interpreter import (
    gateway, function, eval, pyframe, pytraceback, pycode
)
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.pycode import PyCode, BytecodeCorruption
from pypy.tool.stdlib_opcode import bytecode_spec

def unaryoperation(operationname):
    """NOT_RPYTHON"""
    def opimpl(self, *ignored):
        operation = getattr(self.space, operationname)
        w_1 = self.popvalue()
        w_result = operation(w_1)
        self.pushvalue(w_result)
    opimpl.unaryop = operationname

    return func_with_new_name(opimpl, "opcode_impl_for_%s" % operationname)

def binaryoperation(operationname):
    """NOT_RPYTHON"""
    def opimpl(self, *ignored):
        operation = getattr(self.space, operationname)
        w_2 = self.popvalue()
        w_1 = self.popvalue()
        w_result = operation(w_1, w_2)
        self.pushvalue(w_result)
    opimpl.binop = operationname

    return func_with_new_name(opimpl, "opcode_impl_for_%s" % operationname)


opcodedesc = bytecode_spec.opcodedesc
HAVE_ARGUMENT = bytecode_spec.HAVE_ARGUMENT

class __extend__(pyframe.PyFrame):
    """A PyFrame that knows about interpretation of standard Python opcodes
    minus the ones related to nested scopes."""

    ### opcode dispatch ###

    def dispatch(self, pycode, next_instr, ec):
        # For the sequel, force 'next_instr' to be unsigned for performance
        next_instr = r_uint(next_instr)
        co_code = pycode.co_code

        try:
            while True:
                next_instr = self.handle_bytecode(co_code, next_instr, ec)
        except ExitFrame:
            self.last_exception = None
            return self.popvalue()

    def handle_bytecode(self, co_code, next_instr, ec):
        try:
            next_instr = self.dispatch_bytecode(co_code, next_instr, ec)
        except OperationError as operr:
            next_instr = self.handle_operation_error(ec, operr)
        except RaiseWithExplicitTraceback as e:
            next_instr = self.handle_operation_error(ec, e.operr,
                                                     attach_tb=False)
        except KeyboardInterrupt:
            next_instr = self.handle_asynchronous_error(ec,
                self.space.w_KeyboardInterrupt)
        except MemoryError:
            next_instr = self.handle_asynchronous_error(ec,
                self.space.w_MemoryError)
        except rstackovf.StackOverflow as e:
            # Note that this case catches AttributeError!
            rstackovf.check_stack_overflow()
            next_instr = self.handle_asynchronous_error(ec,
                self.space.w_RuntimeError,
                self.space.wrap("maximum recursion depth exceeded"))
        return next_instr

    def handle_asynchronous_error(self, ec, w_type, w_value=None):
        # catch asynchronous exceptions and turn them
        # into OperationErrors
        if w_value is None:
            w_value = self.space.w_None
        operr = OperationError(w_type, w_value)
        return self.handle_operation_error(ec, operr)

    def handle_operation_error(self, ec, operr, attach_tb=True):
        if attach_tb:
            if 1:
                # xxx this is a hack.  It allows bytecode_trace() to
                # call a signal handler which raises, and catch the
                # raised exception immediately.  See test_alarm_raise in
                # pypy/module/signal/test/test_signal.py.  Without the
                # next four lines, if an external call (like
                # socket.accept()) is interrupted by a signal, it raises
                # an exception carrying EINTR which arrives here,
                # entering the next "except" block -- but the signal
                # handler is then called on the next call to
                # dispatch_bytecode(), causing the real exception to be
                # raised after the exception handler block was popped.
                try:
                    trace = self.get_w_f_trace()
                    if trace is not None:
                        self.getorcreatedebug().w_f_trace = None
                    try:
                        ec.bytecode_trace_after_exception(self)
                    finally:
                        if trace is not None:
                            self.getorcreatedebug().w_f_trace = trace
                except OperationError as e:
                    operr = e
            pytraceback.record_application_traceback(
                self.space, operr, self, self.last_instr)
            ec.exception_trace(self, operr)

        block = self.unrollstack(SApplicationException.kind)
        if block is None:
            # no handler found for the OperationError
            if we_are_translated():
                raise operr
            else:
                # try to preserve the CPython-level traceback
                import sys
                tb = sys.exc_info()[2]
                raise OperationError, operr, tb
        else:
            unroller = SApplicationException(operr)
            next_instr = block.handle(self, unroller)
            return next_instr

    def call_contextmanager_exit_function(self, w_func, w_typ, w_val, w_tb):
        return self.space.call_function(w_func, w_typ, w_val, w_tb)

    @jit.unroll_safe
    def dispatch_bytecode(self, co_code, next_instr, ec):
        while True:
            self.last_instr = intmask(next_instr)
            if jit.we_are_jitted():
                ec.bytecode_only_trace(self)
            else:
                ec.bytecode_trace(self)
            next_instr = r_uint(self.last_instr)
            opcode = ord(co_code[next_instr])
            next_instr += 1

            if opcode >= HAVE_ARGUMENT:
                lo = ord(co_code[next_instr])
                hi = ord(co_code[next_instr+1])
                next_instr += 2
                oparg = (hi * 256) | lo
            else:
                oparg = 0

            # note: the structure of the code here is such that it makes
            # (after translation) a big "if/elif" chain, which is then
            # turned into a switch().

            while opcode == opcodedesc.EXTENDED_ARG.index:
                opcode = ord(co_code[next_instr])
                if opcode < HAVE_ARGUMENT:
                    raise BytecodeCorruption
                lo = ord(co_code[next_instr+1])
                hi = ord(co_code[next_instr+2])
                next_instr += 3
                oparg = (oparg * 65536) | (hi * 256) | lo

            if opcode == opcodedesc.RETURN_VALUE.index:
                w_returnvalue = self.popvalue()
                block = self.unrollstack(SReturnValue.kind)
                if block is None:
                    self.pushvalue(w_returnvalue)   # XXX ping pong
                    raise Return
                else:
                    unroller = SReturnValue(w_returnvalue)
                    next_instr = block.handle(self, unroller)
                    return next_instr    # now inside a 'finally' block
            elif opcode == opcodedesc.END_FINALLY.index:
                unroller = self.end_finally()
                if isinstance(unroller, SuspendedUnroller):
                    # go on unrolling the stack
                    block = self.unrollstack(unroller.kind)
                    if block is None:
                        w_result = unroller.nomoreblocks()
                        self.pushvalue(w_result)
                        raise Return
                    else:
                        next_instr = block.handle(self, unroller)
                return next_instr
            elif opcode == opcodedesc.JUMP_ABSOLUTE.index:
                return self.jump_absolute(oparg, ec)
            elif opcode == opcodedesc.BREAK_LOOP.index:
                next_instr = self.BREAK_LOOP(oparg, next_instr)
            elif opcode == opcodedesc.CONTINUE_LOOP.index:
                return self.CONTINUE_LOOP(oparg, next_instr)
            elif opcode == opcodedesc.FOR_ITER.index:
                next_instr = self.FOR_ITER(oparg, next_instr)
            elif opcode == opcodedesc.JUMP_FORWARD.index:
                next_instr = self.JUMP_FORWARD(oparg, next_instr)
            elif opcode == opcodedesc.JUMP_IF_FALSE_OR_POP.index:
                next_instr = self.JUMP_IF_FALSE_OR_POP(oparg, next_instr)
            elif opcode == opcodedesc.JUMP_IF_NOT_DEBUG.index:
                next_instr = self.JUMP_IF_NOT_DEBUG(oparg, next_instr)
            elif opcode == opcodedesc.JUMP_IF_TRUE_OR_POP.index:
                next_instr = self.JUMP_IF_TRUE_OR_POP(oparg, next_instr)
            elif opcode == opcodedesc.POP_JUMP_IF_FALSE.index:
                next_instr = self.POP_JUMP_IF_FALSE(oparg, next_instr)
            elif opcode == opcodedesc.POP_JUMP_IF_TRUE.index:
                next_instr = self.POP_JUMP_IF_TRUE(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_ADD.index:
                self.BINARY_ADD(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_AND.index:
                self.BINARY_AND(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_DIVIDE.index:
                self.BINARY_DIVIDE(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_FLOOR_DIVIDE.index:
                self.BINARY_FLOOR_DIVIDE(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_LSHIFT.index:
                self.BINARY_LSHIFT(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_MODULO.index:
                self.BINARY_MODULO(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_MULTIPLY.index:
                self.BINARY_MULTIPLY(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_OR.index:
                self.BINARY_OR(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_POWER.index:
                self.BINARY_POWER(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_RSHIFT.index:
                self.BINARY_RSHIFT(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_SUBSCR.index:
                self.BINARY_SUBSCR(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_SUBTRACT.index:
                self.BINARY_SUBTRACT(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_TRUE_DIVIDE.index:
                self.BINARY_TRUE_DIVIDE(oparg, next_instr)
            elif opcode == opcodedesc.BINARY_XOR.index:
                self.BINARY_XOR(oparg, next_instr)
            elif opcode == opcodedesc.BUILD_CLASS.index:
                self.BUILD_CLASS(oparg, next_instr)
            elif opcode == opcodedesc.BUILD_LIST.index:
                self.BUILD_LIST(oparg, next_instr)
            elif opcode == opcodedesc.BUILD_LIST_FROM_ARG.index:
                self.BUILD_LIST_FROM_ARG(oparg, next_instr)
            elif opcode == opcodedesc.BUILD_MAP.index:
                self.BUILD_MAP(oparg, next_instr)
            elif opcode == opcodedesc.BUILD_SET.index:
                self.BUILD_SET(oparg, next_instr)
            elif opcode == opcodedesc.BUILD_SLICE.index:
                self.BUILD_SLICE(oparg, next_instr)
            elif opcode == opcodedesc.BUILD_TUPLE.index:
                self.BUILD_TUPLE(oparg, next_instr)
            elif opcode == opcodedesc.CALL_FUNCTION.index:
                self.CALL_FUNCTION(oparg, next_instr)
            elif opcode == opcodedesc.CALL_FUNCTION_KW.index:
                self.CALL_FUNCTION_KW(oparg, next_instr)
            elif opcode == opcodedesc.CALL_FUNCTION_VAR.index:
                self.CALL_FUNCTION_VAR(oparg, next_instr)
            elif opcode == opcodedesc.CALL_FUNCTION_VAR_KW.index:
                self.CALL_FUNCTION_VAR_KW(oparg, next_instr)
            elif opcode == opcodedesc.CALL_METHOD.index:
                self.CALL_METHOD(oparg, next_instr)
            elif opcode == opcodedesc.COMPARE_OP.index:
                self.COMPARE_OP(oparg, next_instr)
            elif opcode == opcodedesc.DELETE_ATTR.index:
                self.DELETE_ATTR(oparg, next_instr)
            elif opcode == opcodedesc.DELETE_FAST.index:
                self.DELETE_FAST(oparg, next_instr)
            elif opcode == opcodedesc.DELETE_GLOBAL.index:
                self.DELETE_GLOBAL(oparg, next_instr)
            elif opcode == opcodedesc.DELETE_NAME.index:
                self.DELETE_NAME(oparg, next_instr)
            elif opcode == opcodedesc.DELETE_SLICE_0.index:
                self.DELETE_SLICE_0(oparg, next_instr)
            elif opcode == opcodedesc.DELETE_SLICE_1.index:
                self.DELETE_SLICE_1(oparg, next_instr)
            elif opcode == opcodedesc.DELETE_SLICE_2.index:
                self.DELETE_SLICE_2(oparg, next_instr)
            elif opcode == opcodedesc.DELETE_SLICE_3.index:
                self.DELETE_SLICE_3(oparg, next_instr)
            elif opcode == opcodedesc.DELETE_SUBSCR.index:
                self.DELETE_SUBSCR(oparg, next_instr)
            elif opcode == opcodedesc.DUP_TOP.index:
                self.DUP_TOP(oparg, next_instr)
            elif opcode == opcodedesc.DUP_TOPX.index:
                self.DUP_TOPX(oparg, next_instr)
            elif opcode == opcodedesc.EXEC_STMT.index:
                self.EXEC_STMT(oparg, next_instr)
            elif opcode == opcodedesc.GET_ITER.index:
                self.GET_ITER(oparg, next_instr)
            elif opcode == opcodedesc.IMPORT_FROM.index:
                self.IMPORT_FROM(oparg, next_instr)
            elif opcode == opcodedesc.IMPORT_NAME.index:
                self.IMPORT_NAME(oparg, next_instr)
            elif opcode == opcodedesc.IMPORT_STAR.index:
                self.IMPORT_STAR(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_ADD.index:
                self.INPLACE_ADD(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_AND.index:
                self.INPLACE_AND(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_DIVIDE.index:
                self.INPLACE_DIVIDE(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_FLOOR_DIVIDE.index:
                self.INPLACE_FLOOR_DIVIDE(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_LSHIFT.index:
                self.INPLACE_LSHIFT(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_MODULO.index:
                self.INPLACE_MODULO(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_MULTIPLY.index:
                self.INPLACE_MULTIPLY(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_OR.index:
                self.INPLACE_OR(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_POWER.index:
                self.INPLACE_POWER(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_RSHIFT.index:
                self.INPLACE_RSHIFT(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_SUBTRACT.index:
                self.INPLACE_SUBTRACT(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_TRUE_DIVIDE.index:
                self.INPLACE_TRUE_DIVIDE(oparg, next_instr)
            elif opcode == opcodedesc.INPLACE_XOR.index:
                self.INPLACE_XOR(oparg, next_instr)
            elif opcode == opcodedesc.LIST_APPEND.index:
                self.LIST_APPEND(oparg, next_instr)
            elif opcode == opcodedesc.LOAD_ATTR.index:
                self.LOAD_ATTR(oparg, next_instr)
            elif opcode == opcodedesc.LOAD_CLOSURE.index:
                self.LOAD_CLOSURE(oparg, next_instr)
            elif opcode == opcodedesc.LOAD_CONST.index:
                self.LOAD_CONST(oparg, next_instr)
            elif opcode == opcodedesc.LOAD_DEREF.index:
                self.LOAD_DEREF(oparg, next_instr)
            elif opcode == opcodedesc.LOAD_FAST.index:
                self.LOAD_FAST(oparg, next_instr)
            elif opcode == opcodedesc.LOAD_GLOBAL.index:
                self.LOAD_GLOBAL(oparg, next_instr)
            elif opcode == opcodedesc.LOAD_LOCALS.index:
                self.LOAD_LOCALS(oparg, next_instr)
            elif opcode == opcodedesc.LOAD_NAME.index:
                self.LOAD_NAME(oparg, next_instr)
            elif opcode == opcodedesc.LOOKUP_METHOD.index:
                self.LOOKUP_METHOD(oparg, next_instr)
            elif opcode == opcodedesc.MAKE_CLOSURE.index:
                self.MAKE_CLOSURE(oparg, next_instr)
            elif opcode == opcodedesc.MAKE_FUNCTION.index:
                self.MAKE_FUNCTION(oparg, next_instr)
            elif opcode == opcodedesc.MAP_ADD.index:
                self.MAP_ADD(oparg, next_instr)
            elif opcode == opcodedesc.NOP.index:
                self.NOP(oparg, next_instr)
            elif opcode == opcodedesc.POP_BLOCK.index:
                self.POP_BLOCK(oparg, next_instr)
            elif opcode == opcodedesc.POP_TOP.index:
                self.POP_TOP(oparg, next_instr)
            elif opcode == opcodedesc.PRINT_EXPR.index:
                self.PRINT_EXPR(oparg, next_instr)
            elif opcode == opcodedesc.PRINT_ITEM.index:
                self.PRINT_ITEM(oparg, next_instr)
            elif opcode == opcodedesc.PRINT_ITEM_TO.index:
                self.PRINT_ITEM_TO(oparg, next_instr)
            elif opcode == opcodedesc.PRINT_NEWLINE.index:
                self.PRINT_NEWLINE(oparg, next_instr)
            elif opcode == opcodedesc.PRINT_NEWLINE_TO.index:
                self.PRINT_NEWLINE_TO(oparg, next_instr)
            elif opcode == opcodedesc.RAISE_VARARGS.index:
                self.RAISE_VARARGS(oparg, next_instr)
            elif opcode == opcodedesc.ROT_FOUR.index:
                self.ROT_FOUR(oparg, next_instr)
            elif opcode == opcodedesc.ROT_THREE.index:
                self.ROT_THREE(oparg, next_instr)
            elif opcode == opcodedesc.ROT_TWO.index:
                self.ROT_TWO(oparg, next_instr)
            elif opcode == opcodedesc.SETUP_EXCEPT.index:
                self.SETUP_EXCEPT(oparg, next_instr)
            elif opcode == opcodedesc.SETUP_FINALLY.index:
                self.SETUP_FINALLY(oparg, next_instr)
            elif opcode == opcodedesc.SETUP_LOOP.index:
                self.SETUP_LOOP(oparg, next_instr)
            elif opcode == opcodedesc.SETUP_WITH.index:
                self.SETUP_WITH(oparg, next_instr)
            elif opcode == opcodedesc.SET_ADD.index:
                self.SET_ADD(oparg, next_instr)
            elif opcode == opcodedesc.SLICE_0.index:
                self.SLICE_0(oparg, next_instr)
            elif opcode == opcodedesc.SLICE_1.index:
                self.SLICE_1(oparg, next_instr)
            elif opcode == opcodedesc.SLICE_2.index:
                self.SLICE_2(oparg, next_instr)
            elif opcode == opcodedesc.SLICE_3.index:
                self.SLICE_3(oparg, next_instr)
            elif opcode == opcodedesc.STOP_CODE.index:
                self.STOP_CODE(oparg, next_instr)
            elif opcode == opcodedesc.STORE_ATTR.index:
                self.STORE_ATTR(oparg, next_instr)
            elif opcode == opcodedesc.STORE_DEREF.index:
                self.STORE_DEREF(oparg, next_instr)
            elif opcode == opcodedesc.STORE_FAST.index:
                self.STORE_FAST(oparg, next_instr)
            elif opcode == opcodedesc.STORE_GLOBAL.index:
                self.STORE_GLOBAL(oparg, next_instr)
            elif opcode == opcodedesc.STORE_MAP.index:
                self.STORE_MAP(oparg, next_instr)
            elif opcode == opcodedesc.STORE_NAME.index:
                self.STORE_NAME(oparg, next_instr)
            elif opcode == opcodedesc.STORE_SLICE_0.index:
                self.STORE_SLICE_0(oparg, next_instr)
            elif opcode == opcodedesc.STORE_SLICE_1.index:
                self.STORE_SLICE_1(oparg, next_instr)
            elif opcode == opcodedesc.STORE_SLICE_2.index:
                self.STORE_SLICE_2(oparg, next_instr)
            elif opcode == opcodedesc.STORE_SLICE_3.index:
                self.STORE_SLICE_3(oparg, next_instr)
            elif opcode == opcodedesc.STORE_SUBSCR.index:
                self.STORE_SUBSCR(oparg, next_instr)
            elif opcode == opcodedesc.UNARY_CONVERT.index:
                self.UNARY_CONVERT(oparg, next_instr)
            elif opcode == opcodedesc.UNARY_INVERT.index:
                self.UNARY_INVERT(oparg, next_instr)
            elif opcode == opcodedesc.UNARY_NEGATIVE.index:
                self.UNARY_NEGATIVE(oparg, next_instr)
            elif opcode == opcodedesc.UNARY_NOT.index:
                self.UNARY_NOT(oparg, next_instr)
            elif opcode == opcodedesc.UNARY_POSITIVE.index:
                self.UNARY_POSITIVE(oparg, next_instr)
            elif opcode == opcodedesc.UNPACK_SEQUENCE.index:
                self.UNPACK_SEQUENCE(oparg, next_instr)
            elif opcode == opcodedesc.WITH_CLEANUP.index:
                self.WITH_CLEANUP(oparg, next_instr)
            elif opcode == opcodedesc.YIELD_VALUE.index:
                self.YIELD_VALUE(oparg, next_instr)
            else:
                self.MISSING_OPCODE(oparg, next_instr)

            if jit.we_are_jitted():
                return next_instr

    @jit.unroll_safe
    def unrollstack(self, unroller_kind):
        while self.blockstack_non_empty():
            block = self.pop_block()
            if (block.handling_mask & unroller_kind) != 0:
                return block
            block.cleanupstack(self)
        self.frame_finished_execution = True  # for generators
        return None

    def unrollstack_and_jump(self, unroller):
        block = self.unrollstack(unroller.kind)
        if block is None:
            raise BytecodeCorruption("misplaced bytecode - should not return")
        return block.handle(self, unroller)

    ### accessor functions ###

    def getlocalvarname(self, index):
        return self.getcode().co_varnames[index]

    def getconstant_w(self, index):
        return self.getcode().co_consts_w[index]

    def getname_u(self, index):
        return self.space.str_w(self.getcode().co_names_w[index])

    def getname_w(self, index):
        return self.getcode().co_names_w[index]


    ################################################################
    ##  Implementation of the "operational" opcodes
    ##  See also nestedscope.py for the rest.
    ##

    def NOP(self, oparg, next_instr):
        # annotation-time check: if it fails, it means that the decoding
        # of oparg failed to produce an integer which is annotated as non-neg
        check_nonneg(oparg)

    @always_inline
    def LOAD_FAST(self, varindex, next_instr):
        # access a local variable directly
        w_value = self.locals_cells_stack_w[varindex]
        if w_value is None:
            self._load_fast_failed(varindex)
        self.pushvalue(w_value)

    @dont_inline
    def _load_fast_failed(self, varindex):
        varname = self.getlocalvarname(varindex)
        raise oefmt(self.space.w_UnboundLocalError,
                    "local variable '%s' referenced before assignment",
                    varname)

    def LOAD_CONST(self, constindex, next_instr):
        w_const = self.getconstant_w(constindex)
        self.pushvalue(w_const)

    def STORE_FAST(self, varindex, next_instr):
        w_newvalue = self.popvalue()
        assert w_newvalue is not None
        self.locals_cells_stack_w[varindex] = w_newvalue

    def getfreevarname(self, index):
        freevarnames = self.pycode.co_cellvars + self.pycode.co_freevars
        return freevarnames[index]

    def iscellvar(self, index):
        # is the variable given by index a cell or a free var?
        return index < len(self.pycode.co_cellvars)

    def LOAD_DEREF(self, varindex, next_instr):
        # nested scopes: access a variable through its cell object
        cell = self._getcell(varindex)
        try:
            w_value = cell.get()
        except ValueError:
            varname = self.getfreevarname(varindex)
            if self.iscellvar(varindex):
                message = "local variable '%s' referenced before assignment" % varname
                w_exc_type = self.space.w_UnboundLocalError
            else:
                message = ("free variable '%s' referenced before assignment"
                           " in enclosing scope" % varname)
                w_exc_type = self.space.w_NameError
            raise OperationError(w_exc_type, self.space.wrap(message))
        else:
            self.pushvalue(w_value)

    def STORE_DEREF(self, varindex, next_instr):
        # nested scopes: access a variable through its cell object
        w_newvalue = self.popvalue()
        cell = self._getcell(varindex)
        cell.set(w_newvalue)

    def LOAD_CLOSURE(self, varindex, next_instr):
        # nested scopes: access the cell object
        cell = self._getcell(varindex)
        w_value = self.space.wrap(cell)
        self.pushvalue(w_value)

    def POP_TOP(self, oparg, next_instr):
        self.popvalue()

    def ROT_TWO(self, oparg, next_instr):
        w_1 = self.popvalue()
        w_2 = self.popvalue()
        self.pushvalue(w_1)
        self.pushvalue(w_2)

    def ROT_THREE(self, oparg, next_instr):
        w_1 = self.popvalue()
        w_2 = self.popvalue()
        w_3 = self.popvalue()
        self.pushvalue(w_1)
        self.pushvalue(w_3)
        self.pushvalue(w_2)

    def ROT_FOUR(self, oparg, next_instr):
        w_1 = self.popvalue()
        w_2 = self.popvalue()
        w_3 = self.popvalue()
        w_4 = self.popvalue()
        self.pushvalue(w_1)
        self.pushvalue(w_4)
        self.pushvalue(w_3)
        self.pushvalue(w_2)

    def DUP_TOP(self, oparg, next_instr):
        w_1 = self.peekvalue()
        self.pushvalue(w_1)

    def DUP_TOPX(self, itemcount, next_instr):
        assert 1 <= itemcount <= 5, "limitation of the current interpreter"
        self.dupvalues(itemcount)

    UNARY_POSITIVE = unaryoperation("pos")
    UNARY_NEGATIVE = unaryoperation("neg")
    UNARY_NOT      = unaryoperation("not_")
    UNARY_CONVERT  = unaryoperation("repr")
    UNARY_INVERT   = unaryoperation("invert")

    def BINARY_POWER(self, oparg, next_instr):
        w_2 = self.popvalue()
        w_1 = self.popvalue()
        w_result = self.space.pow(w_1, w_2, self.space.w_None)
        self.pushvalue(w_result)

    BINARY_MULTIPLY = binaryoperation("mul")
    BINARY_TRUE_DIVIDE  = binaryoperation("truediv")
    BINARY_FLOOR_DIVIDE = binaryoperation("floordiv")
    BINARY_DIVIDE       = binaryoperation("div")
    # XXX BINARY_DIVIDE must fall back to BINARY_TRUE_DIVIDE with -Qnew
    BINARY_MODULO       = binaryoperation("mod")
    BINARY_ADD      = binaryoperation("add")
    BINARY_SUBTRACT = binaryoperation("sub")
    BINARY_SUBSCR   = binaryoperation("getitem")
    BINARY_LSHIFT   = binaryoperation("lshift")
    BINARY_RSHIFT   = binaryoperation("rshift")
    BINARY_AND = binaryoperation("and_")
    BINARY_XOR = binaryoperation("xor")
    BINARY_OR  = binaryoperation("or_")

    def INPLACE_POWER(self, oparg, next_instr):
        w_2 = self.popvalue()
        w_1 = self.popvalue()
        w_result = self.space.inplace_pow(w_1, w_2)
        self.pushvalue(w_result)

    INPLACE_MULTIPLY = binaryoperation("inplace_mul")
    INPLACE_TRUE_DIVIDE  = binaryoperation("inplace_truediv")
    INPLACE_FLOOR_DIVIDE = binaryoperation("inplace_floordiv")
    INPLACE_DIVIDE       = binaryoperation("inplace_div")
    # XXX INPLACE_DIVIDE must fall back to INPLACE_TRUE_DIVIDE with -Qnew
    INPLACE_MODULO       = binaryoperation("inplace_mod")
    INPLACE_ADD      = binaryoperation("inplace_add")
    INPLACE_SUBTRACT = binaryoperation("inplace_sub")
    INPLACE_LSHIFT   = binaryoperation("inplace_lshift")
    INPLACE_RSHIFT   = binaryoperation("inplace_rshift")
    INPLACE_AND = binaryoperation("inplace_and")
    INPLACE_XOR = binaryoperation("inplace_xor")
    INPLACE_OR  = binaryoperation("inplace_or")

    def slice(self, w_start, w_end):
        w_obj = self.popvalue()
        w_result = self.space.getslice(w_obj, w_start, w_end)
        self.pushvalue(w_result)

    def SLICE_0(self, oparg, next_instr):
        self.slice(self.space.w_None, self.space.w_None)

    def SLICE_1(self, oparg, next_instr):
        w_start = self.popvalue()
        self.slice(w_start, self.space.w_None)

    def SLICE_2(self, oparg, next_instr):
        w_end = self.popvalue()
        self.slice(self.space.w_None, w_end)

    def SLICE_3(self, oparg, next_instr):
        w_end = self.popvalue()
        w_start = self.popvalue()
        self.slice(w_start, w_end)

    def storeslice(self, w_start, w_end):
        w_obj = self.popvalue()
        w_newvalue = self.popvalue()
        self.space.setslice(w_obj, w_start, w_end, w_newvalue)

    def STORE_SLICE_0(self, oparg, next_instr):
        self.storeslice(self.space.w_None, self.space.w_None)

    def STORE_SLICE_1(self, oparg, next_instr):
        w_start = self.popvalue()
        self.storeslice(w_start, self.space.w_None)

    def STORE_SLICE_2(self, oparg, next_instr):
        w_end = self.popvalue()
        self.storeslice(self.space.w_None, w_end)

    def STORE_SLICE_3(self, oparg, next_instr):
        w_end = self.popvalue()
        w_start = self.popvalue()
        self.storeslice(w_start, w_end)

    def deleteslice(self, w_start, w_end):
        w_obj = self.popvalue()
        self.space.delslice(w_obj, w_start, w_end)

    def DELETE_SLICE_0(self, oparg, next_instr):
        self.deleteslice(self.space.w_None, self.space.w_None)

    def DELETE_SLICE_1(self, oparg, next_instr):
        w_start = self.popvalue()
        self.deleteslice(w_start, self.space.w_None)

    def DELETE_SLICE_2(self, oparg, next_instr):
        w_end = self.popvalue()
        self.deleteslice(self.space.w_None, w_end)

    def DELETE_SLICE_3(self, oparg, next_instr):
        w_end = self.popvalue()
        w_start = self.popvalue()
        self.deleteslice(w_start, w_end)

    def STORE_SUBSCR(self, oparg, next_instr):
        "obj[subscr] = newvalue"
        w_subscr = self.popvalue()
        w_obj = self.popvalue()
        w_newvalue = self.popvalue()
        self.space.setitem(w_obj, w_subscr, w_newvalue)

    def DELETE_SUBSCR(self, oparg, next_instr):
        "del obj[subscr]"
        w_subscr = self.popvalue()
        w_obj = self.popvalue()
        self.space.delitem(w_obj, w_subscr)

    def PRINT_EXPR(self, oparg, next_instr):
        w_expr = self.popvalue()
        print_expr(self.space, w_expr)

    def PRINT_ITEM_TO(self, oparg, next_instr):
        w_stream = self.popvalue()
        w_item = self.popvalue()
        if self.space.is_w(w_stream, self.space.w_None):
            w_stream = sys_stdout(self.space)   # grumble grumble special cases
        print_item_to(self.space, self._printable_object(w_item), w_stream)

    def PRINT_ITEM(self, oparg, next_instr):
        w_item = self.popvalue()
        print_item(self.space, self._printable_object(w_item))

    def _printable_object(self, w_obj):
        space = self.space
        if not space.isinstance_w(w_obj, space.w_unicode):
            w_obj = space.str(w_obj)
        return w_obj

    def PRINT_NEWLINE_TO(self, oparg, next_instr):
        w_stream = self.popvalue()
        if self.space.is_w(w_stream, self.space.w_None):
            w_stream = sys_stdout(self.space)   # grumble grumble special cases
        print_newline_to(self.space, w_stream)

    def PRINT_NEWLINE(self, oparg, next_instr):
        print_newline(self.space)

    def BREAK_LOOP(self, oparg, next_instr):
        return self.unrollstack_and_jump(SBreakLoop.singleton)

    def CONTINUE_LOOP(self, startofloop, next_instr):
        unroller = SContinueLoop(startofloop)
        return self.unrollstack_and_jump(unroller)

    def RAISE_VARARGS(self, nbargs, next_instr):
        space = self.space
        if nbargs == 0:
            last_operr = self._exc_info_unroll(space, for_hidden=True)
            if last_operr is None:
                raise oefmt(space.w_TypeError,
                            "No active exception to reraise")
            # re-raise, no new traceback obj will be attached
            self.last_exception = last_operr
            raise RaiseWithExplicitTraceback(last_operr)

        w_value = w_traceback = space.w_None
        if nbargs >= 3:
            w_traceback = self.popvalue()
        if nbargs >= 2:
            w_value = self.popvalue()
        if 1:
            w_type = self.popvalue()
        operror = OperationError(w_type, w_value)
        operror.normalize_exception(space)
        if space.is_w(w_traceback, space.w_None):
            # common case
            raise operror
        else:
            msg = "raise: arg 3 must be a traceback or None"
            tb = pytraceback.check_traceback(space, w_traceback, msg)
            operror.set_traceback(tb)
            # special 3-arguments raise, no new traceback obj will be attached
            raise RaiseWithExplicitTraceback(operror)

    def LOAD_LOCALS(self, oparg, next_instr):
        self.pushvalue(self.getorcreatedebug().w_locals)

    def EXEC_STMT(self, oparg, next_instr):
        w_locals = self.popvalue()
        w_globals = self.popvalue()
        w_prog = self.popvalue()
        ec = self.space.getexecutioncontext()
        flags = ec.compiler.getcodeflags(self.pycode)
        w_compile_flags = self.space.wrap(flags)
        w_resulttuple = prepare_exec(self.space, self.space.wrap(self), w_prog,
                                     w_globals, w_locals,
                                     w_compile_flags,
                                     self.space.wrap(self.get_builtin()),
                                     self.space.gettypeobject(PyCode.typedef))
        w_prog, w_globals, w_locals = self.space.fixedview(w_resulttuple, 3)

        plain = (self.get_w_locals() is not None and
                 self.space.is_w(w_locals, self.get_w_locals()))
        if plain:
            w_locals = self.getdictscope()
        co = self.space.interp_w(eval.Code, w_prog)
        co.exec_code(self.space, w_globals, w_locals)
        if plain:
            self.setdictscope(w_locals)

    def POP_BLOCK(self, oparg, next_instr):
        block = self.pop_block()
        block.cleanup(self)  # the block knows how to clean up the value stack

    def end_finally(self):
        # unlike CPython, there are two statically distinct cases: the
        # END_FINALLY might be closing an 'except' block or a 'finally'
        # block.  In the first case, the stack contains three items:
        #   [exception type we are now handling]
        #   [exception value we are now handling]
        #   [wrapped SApplicationException]
        # In the case of a finally: block, the stack contains only one
        # item (unlike CPython which can have 1, 2 or 3 items):
        #   [wrapped subclass of SuspendedUnroller]
        w_top = self.popvalue()
        if self.space.is_w(w_top, self.space.w_None):
            # case of a finally: block with no exception
            return None
        if isinstance(w_top, SuspendedUnroller):
            # case of a finally: block with a suspended unroller
            return w_top
        else:
            # case of an except: block.  We popped the exception type
            self.popvalue()        #     Now we pop the exception value
            w_unroller = self.popvalue()
            assert w_unroller is not None
            return w_unroller

    def BUILD_CLASS(self, oparg, next_instr):
        w_methodsdict = self.popvalue()
        w_bases = self.popvalue()
        w_name = self.popvalue()
        w_metaclass = find_metaclass(self.space, w_bases,
                                     w_methodsdict, self.get_w_globals(),
                                     self.space.wrap(self.get_builtin()))
        w_newclass = self.space.call_function(w_metaclass, w_name,
                                              w_bases, w_methodsdict)
        self.pushvalue(w_newclass)

    def STORE_NAME(self, varindex, next_instr):
        varname = self.getname_u(varindex)
        w_newvalue = self.popvalue()
        self.space.setitem_str(self.getorcreatedebug().w_locals, varname,
                               w_newvalue)

    def DELETE_NAME(self, varindex, next_instr):
        w_varname = self.getname_w(varindex)
        try:
            self.space.delitem(self.getorcreatedebug().w_locals, w_varname)
        except OperationError as e:
            # catch KeyErrors and turn them into NameErrors
            if not e.match(self.space, self.space.w_KeyError):
                raise
            raise oefmt(self.space.w_NameError, "name '%s' is not defined",
                        self.space.str_w(w_varname))

    def UNPACK_SEQUENCE(self, itemcount, next_instr):
        w_iterable = self.popvalue()
        items = self.space.fixedview_unroll(w_iterable, itemcount)
        self.pushrevvalues(itemcount, items)

    def STORE_ATTR(self, nameindex, next_instr):
        "obj.attributename = newvalue"
        w_attributename = self.getname_w(nameindex)
        w_obj = self.popvalue()
        w_newvalue = self.popvalue()
        self.space.setattr(w_obj, w_attributename, w_newvalue)

    def DELETE_ATTR(self, nameindex, next_instr):
        "del obj.attributename"
        w_attributename = self.getname_w(nameindex)
        w_obj = self.popvalue()
        self.space.delattr(w_obj, w_attributename)

    def STORE_GLOBAL(self, nameindex, next_instr):
        varname = self.getname_u(nameindex)
        w_newvalue = self.popvalue()
        self.space.setitem_str(self.get_w_globals(), varname, w_newvalue)

    def DELETE_GLOBAL(self, nameindex, next_instr):
        w_varname = self.getname_w(nameindex)
        self.space.delitem(self.get_w_globals(), w_varname)

    def LOAD_NAME(self, nameindex, next_instr):
        if self.getorcreatedebug().w_locals is not self.get_w_globals():
            varname = self.getname_u(nameindex)
            w_value = self.space.finditem_str(self.getorcreatedebug().w_locals,
                                              varname)
            if w_value is not None:
                self.pushvalue(w_value)
                return
        self.LOAD_GLOBAL(nameindex, next_instr)    # fall-back

    @always_inline
    def _load_global(self, varname):
        w_value = self.space.finditem_str(self.get_w_globals(), varname)
        if w_value is None:
            # not in the globals, now look in the built-ins
            w_value = self.get_builtin().getdictvalue(self.space, varname)
            if w_value is None:
                self._load_global_failed(varname)
        return w_value

    @dont_inline
    def _load_global_failed(self, varname):
        raise oefmt(self.space.w_NameError,
                    "global name '%s' is not defined", varname)

    @always_inline
    def LOAD_GLOBAL(self, nameindex, next_instr):
        self.pushvalue(self._load_global(self.getname_u(nameindex)))

    def DELETE_FAST(self, varindex, next_instr):
        if self.locals_cells_stack_w[varindex] is None:
            varname = self.getlocalvarname(varindex)
            raise oefmt(self.space.w_UnboundLocalError,
                        "local variable '%s' referenced before assignment",
                        varname)
        self.locals_cells_stack_w[varindex] = None

    def BUILD_TUPLE(self, itemcount, next_instr):
        items = self.popvalues(itemcount)
        w_tuple = self.space.newtuple(items)
        self.pushvalue(w_tuple)

    def BUILD_LIST(self, itemcount, next_instr):
        items = self.popvalues_mutable(itemcount)
        w_list = self.space.newlist(items)
        self.pushvalue(w_list)

    def BUILD_LIST_FROM_ARG(self, _, next_instr):
        space = self.space
        # this is a little dance, because list has to be before the
        # value
        last_val = self.popvalue()
        length_hint = 0
        try:
            length_hint = space.length_hint(last_val, length_hint)
        except OperationError as e:
            if e.async(space):
                raise
        self.pushvalue(space.newlist([], sizehint=length_hint))
        self.pushvalue(last_val)

    @always_inline
    def LOAD_ATTR(self, nameindex, next_instr):
        "obj.attributename"
        w_obj = self.popvalue()
        if not jit.we_are_jitted():
            from pypy.objspace.std.mapdict import LOAD_ATTR_caching
            w_value = LOAD_ATTR_caching(self.getcode(), w_obj, nameindex)
        else:
            w_attributename = self.getname_w(nameindex)
            w_value = self.space.getattr(w_obj, w_attributename)
        self.pushvalue(w_value)

    @jit.unroll_safe
    def cmp_exc_match(self, w_1, w_2):
        space = self.space
        if space.isinstance_w(w_2, space.w_tuple):
            for w_t in space.fixedview(w_2):
                if space.isinstance_w(w_t, space.w_str):
                    msg = "catching of string exceptions is deprecated"
                    space.warn(space.wrap(msg), space.w_DeprecationWarning)
        elif space.isinstance_w(w_2, space.w_str):
            msg = "catching of string exceptions is deprecated"
            space.warn(space.wrap(msg), space.w_DeprecationWarning)
        return space.newbool(space.exception_match(w_1, w_2))

    def COMPARE_OP(self, testnum, next_instr):
        w_2 = self.popvalue()
        w_1 = self.popvalue()
        if testnum == 0:
            w_result = self.space.lt(w_1, w_2)
        elif testnum == 1:
            w_result = self.space.le(w_1, w_2)
        elif testnum == 2:
            w_result = self.space.eq(w_1, w_2)
        elif testnum == 3:
            w_result = self.space.ne(w_1, w_2)
        elif testnum == 4:
            w_result = self.space.gt(w_1, w_2)
        elif testnum == 5:
            w_result = self.space.ge(w_1, w_2)
        elif testnum == 6:
            w_result = self.space.contains(w_2, w_1)
        elif testnum == 7:
            w_result = self.space.not_(self.space.contains(w_2, w_1))
        elif testnum == 8:
            w_result = self.space.is_(w_1, w_2)
        elif testnum == 9:
            w_result = self.space.not_(self.space.is_(w_1, w_2))
        elif testnum == 10:
            w_result = self.cmp_exc_match(w_1, w_2)
        else:
            raise BytecodeCorruption("bad COMPARE_OP oparg")
        self.pushvalue(w_result)

    def IMPORT_NAME(self, nameindex, next_instr):
        space = self.space
        w_modulename = self.getname_w(nameindex)
        modulename = self.space.str_w(w_modulename)
        w_fromlist = self.popvalue()

        w_flag = self.popvalue()
        try:
            if space.int_w(w_flag) == -1:
                w_flag = None
        except OperationError as e:
            if e.async(space):
                raise

        w_import = self.get_builtin().getdictvalue(space, '__import__')
        if w_import is None:
            raise OperationError(space.w_ImportError,
                                 space.wrap("__import__ not found"))
        d = self.getdebug()
        if d is None:
            w_locals = None
        else:
            w_locals = d.w_locals
        if w_locals is None:            # CPython does this
            w_locals = space.w_None
        w_modulename = space.wrap(modulename)
        w_globals = self.get_w_globals()
        if w_flag is None:
            w_obj = space.call_function(w_import, w_modulename, w_globals,
                                        w_locals, w_fromlist)
        else:
            w_obj = space.call_function(w_import, w_modulename, w_globals,
                                        w_locals, w_fromlist, w_flag)

        self.pushvalue(w_obj)

    def IMPORT_STAR(self, oparg, next_instr):
        w_module = self.popvalue()
        w_locals = self.getdictscope()
        import_all_from(self.space, w_module, w_locals)
        self.setdictscope(w_locals)

    def IMPORT_FROM(self, nameindex, next_instr):
        w_name = self.getname_w(nameindex)
        w_module = self.peekvalue()
        try:
            w_obj = self.space.getattr(w_module, w_name)
        except OperationError as e:
            if not e.match(self.space, self.space.w_AttributeError):
                raise
            raise oefmt(self.space.w_ImportError,
                        "cannot import name '%s'", self.space.str_w(w_name))
        self.pushvalue(w_obj)

    def YIELD_VALUE(self, oparg, next_instr):
        raise Yield

    def jump_absolute(self, jumpto, ec):
        # this function is overridden by pypy.module.pypyjit.interp_jit
        check_nonneg(jumpto)
        return jumpto

    def JUMP_FORWARD(self, jumpby, next_instr):
        next_instr += jumpby
        return next_instr

    def POP_JUMP_IF_FALSE(self, target, next_instr):
        w_value = self.popvalue()
        if not self.space.is_true(w_value):
            return target
        return next_instr

    def POP_JUMP_IF_TRUE(self, target, next_instr):
        w_value = self.popvalue()
        if self.space.is_true(w_value):
            return target
        return next_instr

    def JUMP_IF_FALSE_OR_POP(self, target, next_instr):
        w_value = self.peekvalue()
        if not self.space.is_true(w_value):
            return target
        self.popvalue()
        return next_instr

    def JUMP_IF_TRUE_OR_POP(self, target, next_instr):
        w_value = self.peekvalue()
        if self.space.is_true(w_value):
            return target
        self.popvalue()
        return next_instr

    def JUMP_IF_NOT_DEBUG(self, jumpby, next_instr):
        if not self.space.sys.debug:
            next_instr += jumpby
        return next_instr

    def GET_ITER(self, oparg, next_instr):
        w_iterable = self.popvalue()
        w_iterator = self.space.iter(w_iterable)
        self.pushvalue(w_iterator)

    def FOR_ITER(self, jumpby, next_instr):
        w_iterator = self.peekvalue()
        try:
            w_nextitem = self.space.next(w_iterator)
        except OperationError as e:
            if not e.match(self.space, self.space.w_StopIteration):
                raise
            # iterator exhausted
            self.popvalue()
            next_instr += jumpby
        else:
            self.pushvalue(w_nextitem)
        return next_instr

    def FOR_LOOP(self, oparg, next_instr):
        raise BytecodeCorruption("old opcode, no longer in use")

    def SETUP_LOOP(self, offsettoend, next_instr):
        block = LoopBlock(self, next_instr + offsettoend, self.lastblock)
        self.lastblock = block

    def SETUP_EXCEPT(self, offsettoend, next_instr):
        block = ExceptBlock(self, next_instr + offsettoend, self.lastblock)
        self.lastblock = block

    def SETUP_FINALLY(self, offsettoend, next_instr):
        block = FinallyBlock(self, next_instr + offsettoend, self.lastblock)
        self.lastblock = block

    def SETUP_WITH(self, offsettoend, next_instr):
        w_manager = self.peekvalue()
        w_enter = self.space.lookup(w_manager, "__enter__")
        w_descr = self.space.lookup(w_manager, "__exit__")
        if w_enter is None or w_descr is None:
            raise oefmt(self.space.w_AttributeError,
                        "'%T' object is not a context manager (no __enter__/"
                        "__exit__ method)", w_manager)
        w_exit = self.space.get(w_descr, w_manager)
        self.settopvalue(w_exit)
        w_result = self.space.get_and_call_function(w_enter, w_manager)
        block = WithBlock(self, next_instr + offsettoend, self.lastblock)
        self.lastblock = block
        self.pushvalue(w_result)

    def WITH_CLEANUP(self, oparg, next_instr):
        # see comment in END_FINALLY for stack state
        w_unroller = self.popvalue()
        w_exitfunc = self.popvalue()
        self.pushvalue(w_unroller)
        if isinstance(w_unroller, SApplicationException):
            # app-level exception
            operr = w_unroller.operr
            self.last_exception = operr
            w_traceback = self.space.wrap(operr.get_traceback())
            w_suppress = self.call_contextmanager_exit_function(
                w_exitfunc,
                operr.w_type,
                operr.get_w_value(self.space),
                w_traceback)
            if self.space.is_true(w_suppress):
                # __exit__() returned True -> Swallow the exception.
                self.settopvalue(self.space.w_None)
        else:
            self.call_contextmanager_exit_function(
                w_exitfunc,
                self.space.w_None,
                self.space.w_None,
                self.space.w_None)

    @jit.unroll_safe
    def call_function(self, oparg, w_star=None, w_starstar=None):
        n_arguments = oparg & 0xff
        n_keywords = (oparg>>8) & 0xff
        if n_keywords:
            keywords = [None] * n_keywords
            keywords_w = [None] * n_keywords
            while True:
                n_keywords -= 1
                if n_keywords < 0:
                    break
                w_value = self.popvalue()
                w_key = self.popvalue()
                key = self.space.str_w(w_key)
                keywords[n_keywords] = key
                keywords_w[n_keywords] = w_value
        else:
            keywords = None
            keywords_w = None
        arguments = self.popvalues(n_arguments)
        args = self.argument_factory(arguments, keywords, keywords_w, w_star,
                                     w_starstar)
        w_function  = self.popvalue()
        if self.get_is_being_profiled() and function.is_builtin_code(w_function):
            w_result = self.space.call_args_and_c_profile(self, w_function,
                                                          args)
        else:
            w_result = self.space.call_args(w_function, args)
        self.pushvalue(w_result)

    def CALL_FUNCTION(self, oparg, next_instr):
        # XXX start of hack for performance
        if (oparg >> 8) & 0xff == 0:
            # Only positional arguments
            nargs = oparg & 0xff
            w_function = self.peekvalue(nargs)
            try:
                w_result = self.space.call_valuestack(w_function, nargs, self)
            finally:
                self.dropvalues(nargs + 1)
            self.pushvalue(w_result)
        # XXX end of hack for performance
        else:
            # general case
            self.call_function(oparg)

    def CALL_FUNCTION_VAR(self, oparg, next_instr):
        w_varargs = self.popvalue()
        self.call_function(oparg, w_varargs)

    def CALL_FUNCTION_KW(self, oparg, next_instr):
        w_varkw = self.popvalue()
        self.call_function(oparg, None, w_varkw)

    def CALL_FUNCTION_VAR_KW(self, oparg, next_instr):
        w_varkw = self.popvalue()
        w_varargs = self.popvalue()
        self.call_function(oparg, w_varargs, w_varkw)

    def MAKE_FUNCTION(self, numdefaults, next_instr):
        w_codeobj = self.popvalue()
        codeobj = self.space.interp_w(PyCode, w_codeobj)
        defaultarguments = self.popvalues(numdefaults)
        fn = function.Function(self.space, codeobj, self.get_w_globals(),
                               defaultarguments)
        self.pushvalue(self.space.wrap(fn))

    @jit.unroll_safe
    def MAKE_CLOSURE(self, numdefaults, next_instr):
        w_codeobj = self.popvalue()
        codeobj = self.space.interp_w(pycode.PyCode, w_codeobj)
        w_freevarstuple = self.popvalue()
        freevars = [self.space.interp_w(Cell, cell)
                    for cell in self.space.fixedview(w_freevarstuple)]
        defaultarguments = self.popvalues(numdefaults)
        fn = function.Function(self.space, codeobj, self.get_w_globals(),
                               defaultarguments, freevars)
        self.pushvalue(self.space.wrap(fn))

    def BUILD_SLICE(self, numargs, next_instr):
        if numargs == 3:
            w_step = self.popvalue()
        elif numargs == 2:
            w_step = self.space.w_None
        else:
            raise BytecodeCorruption
        w_end = self.popvalue()
        w_start = self.popvalue()
        w_slice = self.space.newslice(w_start, w_end, w_step)
        self.pushvalue(w_slice)

    def LIST_APPEND(self, oparg, next_instr):
        w = self.popvalue()
        v = self.peekvalue(oparg - 1)
        self.space.call_method(v, 'append', w)

    def SET_ADD(self, oparg, next_instr):
        w_value = self.popvalue()
        w_set = self.peekvalue(oparg - 1)
        self.space.call_method(w_set, 'add', w_value)

    def MAP_ADD(self, oparg, next_instr):
        w_key = self.popvalue()
        w_value = self.popvalue()
        w_dict = self.peekvalue(oparg - 1)
        self.space.setitem(w_dict, w_key, w_value)

    def SET_LINENO(self, lineno, next_instr):
        pass

    # overridden by faster version in the standard object space.
    LOOKUP_METHOD = LOAD_ATTR
    CALL_METHOD = CALL_FUNCTION

    def MISSING_OPCODE(self, oparg, next_instr):
        ofs = self.last_instr
        c = self.pycode.co_code[ofs]
        name = self.pycode.co_name
        raise BytecodeCorruption("unknown opcode, ofs=%d, code=%d, name=%s" %
                                 (ofs, ord(c), name) )

    STOP_CODE = MISSING_OPCODE

    def BUILD_MAP(self, itemcount, next_instr):
        w_dict = self.space.newdict()
        self.pushvalue(w_dict)

    @jit.unroll_safe
    def BUILD_SET(self, itemcount, next_instr):
        w_set = self.space.newset()
        for i in range(itemcount-1, -1, -1):
            w_item = self.peekvalue(i)
            self.space.call_method(w_set, 'add', w_item)
        self.popvalues(itemcount)
        self.pushvalue(w_set)

    def STORE_MAP(self, oparg, next_instr):
        w_key = self.popvalue()
        w_value = self.popvalue()
        w_dict = self.peekvalue()
        self.space.setitem(w_dict, w_key, w_value)


### ____________________________________________________________ ###

class ExitFrame(Exception):
    pass


class Return(ExitFrame):
    """Raised when exiting a frame via a 'return' statement."""


class Yield(ExitFrame):
    """Raised when exiting a frame via a 'yield' statement."""


class RaiseWithExplicitTraceback(Exception):
    """Raised at interp-level by a 0- or 3-arguments 'raise' statement."""
    def __init__(self, operr):
        self.operr = operr


### Frame Blocks ###

class SuspendedUnroller(W_Root):
    """Abstract base class for interpreter-level objects that
    instruct the interpreter to change the control flow and the
    block stack.

    The concrete subclasses correspond to the various values WHY_XXX
    values of the why_code enumeration in ceval.c:

                WHY_NOT,        OK, not this one :-)
                WHY_EXCEPTION,  SApplicationException
                WHY_RERAISE,    implemented differently, see Reraise
                WHY_RETURN,     SReturnValue
                WHY_BREAK,      SBreakLoop
                WHY_CONTINUE,   SContinueLoop
                WHY_YIELD       not needed
    """
    _immutable_ = True
    def nomoreblocks(self):
        raise BytecodeCorruption("misplaced bytecode - should not return")

class SReturnValue(SuspendedUnroller):
    """Signals a 'return' statement.
    Argument is the wrapped object to return."""
    _immutable_ = True
    kind = 0x01
    def __init__(self, w_returnvalue):
        self.w_returnvalue = w_returnvalue
    def nomoreblocks(self):
        return self.w_returnvalue

class SApplicationException(SuspendedUnroller):
    """Signals an application-level exception
    (i.e. an OperationException)."""
    _immutable_ = True
    kind = 0x02
    def __init__(self, operr):
        self.operr = operr
    def nomoreblocks(self):
        raise RaiseWithExplicitTraceback(self.operr)

class SBreakLoop(SuspendedUnroller):
    """Signals a 'break' statement."""
    _immutable_ = True
    kind = 0x04
SBreakLoop.singleton = SBreakLoop()

class SContinueLoop(SuspendedUnroller):
    """Signals a 'continue' statement.
    Argument is the bytecode position of the beginning of the loop."""
    _immutable_ = True
    kind = 0x08
    def __init__(self, jump_to):
        self.jump_to = jump_to


class FrameBlock(object):
    """Abstract base class for frame blocks from the blockstack,
    used by the SETUP_XXX and POP_BLOCK opcodes."""

    _immutable_ = True

    def __init__(self, frame, handlerposition, previous):
        self.handlerposition = handlerposition
        self.valuestackdepth = frame.valuestackdepth
        self.previous = previous   # this makes a linked list of blocks

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.handlerposition == other.handlerposition and
                self.valuestackdepth == other.valuestackdepth)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.handlerposition, self.valuestackdepth))

    def cleanupstack(self, frame):
        frame.dropvaluesuntil(self.valuestackdepth)

    def cleanup(self, frame):
        "Clean up a frame when we normally exit the block."
        self.cleanupstack(frame)

    # internal pickling interface, not using the standard protocol
    def _get_state_(self, space):
        w = space.wrap
        return space.newtuple([w(self._opname), w(self.handlerposition),
                               w(self.valuestackdepth)])

    def handle(self, frame, unroller):
        """ Purely abstract method
        """
        raise NotImplementedError

class LoopBlock(FrameBlock):
    """A loop block.  Stores the end-of-loop pointer in case of 'break'."""

    _immutable_ = True
    _opname = 'SETUP_LOOP'
    handling_mask = SBreakLoop.kind | SContinueLoop.kind

    def handle(self, frame, unroller):
        if isinstance(unroller, SContinueLoop):
            # re-push the loop block without cleaning up the value stack,
            # and jump to the beginning of the loop, stored in the
            # exception's argument
            frame.append_block(self)
            jumpto = unroller.jump_to
            ec = frame.space.getexecutioncontext()
            return r_uint(frame.jump_absolute(jumpto, ec))
        else:
            # jump to the end of the loop
            self.cleanupstack(frame)
            return r_uint(self.handlerposition)


class ExceptBlock(FrameBlock):
    """An try:except: block.  Stores the position of the exception handler."""

    _immutable_ = True
    _opname = 'SETUP_EXCEPT'
    handling_mask = SApplicationException.kind

    def handle(self, frame, unroller):
        # push the exception to the value stack for inspection by the
        # exception handler (the code after the except:)
        self.cleanupstack(frame)
        assert isinstance(unroller, SApplicationException)
        operationerr = unroller.operr
        operationerr.normalize_exception(frame.space)
        # the stack setup is slightly different than in CPython:
        # instead of the traceback, we store the unroller object,
        # wrapped.
        frame.pushvalue(frame.space.wrap(unroller))
        frame.pushvalue(operationerr.get_w_value(frame.space))
        frame.pushvalue(operationerr.w_type)
        frame.last_exception = operationerr
        return r_uint(self.handlerposition)   # jump to the handler


class FinallyBlock(FrameBlock):
    """A try:finally: block.  Stores the position of the exception handler."""

    _immutable_ = True
    _opname = 'SETUP_FINALLY'
    handling_mask = -1     # handles every kind of SuspendedUnroller

    def handle(self, frame, unroller):
        # any abnormal reason for unrolling a finally: triggers the end of
        # the block unrolling and the entering the finally: handler.
        # see comments in cleanup().
        self.cleanupstack(frame)
        frame.pushvalue(frame.space.wrap(unroller))
        return r_uint(self.handlerposition)   # jump to the handler


class WithBlock(FinallyBlock):

    _immutable_ = True

    def handle(self, frame, unroller):
        if isinstance(unroller, SApplicationException):
            unroller.operr.normalize_exception(frame.space)
        return FinallyBlock.handle(self, frame, unroller)

block_classes = {'SETUP_LOOP': LoopBlock,
                 'SETUP_EXCEPT': ExceptBlock,
                 'SETUP_FINALLY': FinallyBlock,
                 'SETUP_WITH': WithBlock,
                 }

### helpers written at the application-level ###
# Some of these functions are expected to be generally useful if other
# parts of the code need to do the same thing as a non-trivial opcode,
# like finding out which metaclass a new class should have.
# This is why they are not methods of PyFrame.
# There are also a couple of helpers that are methods, defined in the
# class above.

app = gateway.applevel(r'''
    """ applevel implementation of certain system properties, imports
    and other helpers"""
    import sys

    def sys_stdout():
        try:
            return sys.stdout
        except AttributeError:
            raise RuntimeError("lost sys.stdout")

    def print_expr(obj):
        try:
            displayhook = sys.displayhook
        except AttributeError:
            raise RuntimeError("lost sys.displayhook")
        displayhook(obj)

    def print_item_to(x, stream):
        if file_softspace(stream, False):
           stream.write(" ")

        # give to write() an argument which is either a string or a unicode
        # (and let it deals itself with unicode handling).  The check "is
        # unicode" should not use isinstance() at app-level, because that
        # could be fooled by strange objects, so it is done at interp-level.
        stream.write(x)

        # add a softspace unless we just printed a string which ends in a '\t'
        # or '\n' -- or more generally any whitespace character but ' '
        if x:
            lastchar = x[-1]
            if lastchar.isspace() and lastchar != ' ':
                return
        file_softspace(stream, True)

    def print_item(x):
        print_item_to(x, sys_stdout())

    def print_newline_to(stream):
        stream.write("\n")
        file_softspace(stream, False)

    def print_newline():
        print_newline_to(sys_stdout())

    def file_softspace(file, newflag):
        try:
            softspace = file.softspace
        except AttributeError:
            softspace = 0
        try:
            file.softspace = newflag
        except AttributeError:
            pass
        return softspace
''', filename=__file__)

sys_stdout      = app.interphook('sys_stdout')
print_expr      = app.interphook('print_expr')
print_item      = app.interphook('print_item')
print_item_to   = app.interphook('print_item_to')
print_newline   = app.interphook('print_newline')
print_newline_to= app.interphook('print_newline_to')
file_softspace  = app.interphook('file_softspace')

app = gateway.applevel(r'''
    def find_metaclass(bases, namespace, globals, builtin):
        if '__metaclass__' in namespace:
            return namespace['__metaclass__']
        elif len(bases) > 0:
            base = bases[0]
            if hasattr(base, '__class__'):
                return base.__class__
            else:
                return type(base)
        elif '__metaclass__' in globals:
            return globals['__metaclass__']
        else:
            try:
                return builtin.__metaclass__
            except AttributeError:
                return type
''', filename=__file__)

find_metaclass  = app.interphook('find_metaclass')

app = gateway.applevel(r'''
    def import_all_from(module, into_locals):
        try:
            all = module.__all__
        except AttributeError:
            try:
                dict = module.__dict__
            except AttributeError:
                raise ImportError("from-import-* object has no __dict__ "
                                  "and no __all__")
            all = dict.keys()
            skip_leading_underscores = True
        else:
            skip_leading_underscores = False
        for name in all:
            if skip_leading_underscores and name[0]=='_':
                continue
            into_locals[name] = getattr(module, name)
''', filename=__file__)

import_all_from = app.interphook('import_all_from')

app = gateway.applevel(r'''
    def prepare_exec(f, prog, globals, locals, compile_flags, builtin, codetype):
        """Manipulate parameters to exec statement to (codeobject, dict, dict).
        """
        if (globals is None and locals is None and
            isinstance(prog, tuple) and
            (len(prog) == 2 or len(prog) == 3)):
            globals = prog[1]
            if len(prog) == 3:
                locals = prog[2]
            prog = prog[0]
        if globals is None:
            globals = f.f_globals
            if locals is None:
                locals = f.f_locals
        if locals is None:
            locals = globals

        if not isinstance(globals, dict):
            if not hasattr(globals, '__getitem__'):
                raise TypeError("exec: arg 2 must be a dictionary or None")
        globals.setdefault('__builtins__', builtin)
        if not isinstance(locals, dict):
            if not hasattr(locals, '__getitem__'):
                raise TypeError("exec: arg 3 must be a dictionary or None")

        if not isinstance(prog, codetype):
            filename = '<string>'
            if not isinstance(prog, basestring):
                if isinstance(prog, file):
                    filename = prog.name
                    prog = prog.read()
                else:
                    raise TypeError("exec: arg 1 must be a string, file, "
                                    "or code object")
            prog = compile(prog, filename, 'exec', compile_flags, 1)
        return (prog, globals, locals)
''', filename=__file__)

prepare_exec    = app.interphook('prepare_exec')
