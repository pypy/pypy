"""
Implementation of a part of the standard Python opcodes.

The rest, dealing with variables in optimized ways, is in nestedscope.py.
"""

import sys
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import gateway, function, eval, pyframe, pytraceback
from pypy.interpreter.pycode import PyCode, BytecodeCorruption
from rpython.tool.sourcetools import func_with_new_name
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib import jit, rstackovf
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.debug import check_nonneg
from pypy.tool.stdlib_opcode import (bytecode_spec,
                                     unrolling_all_opcode_descs)

CANNOT_CATCH_MSG = ("catching classes that don't inherit from BaseException "
                    "is not allowed in 3.x")

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

compare_dispatch_table = [
    "cmp_lt",   # "<"
    "cmp_le",   # "<="
    "cmp_eq",   # "=="
    "cmp_ne",   # "!="
    "cmp_gt",   # ">"
    "cmp_ge",   # ">="
    "cmp_in",
    "cmp_not_in",
    "cmp_is",
    "cmp_is_not",
    "cmp_exc_match",
    ]

unrolling_compare_dispatch_table = unrolling_iterable(
    enumerate(compare_dispatch_table))


class __extend__(pyframe.PyFrame):
    """A PyFrame that knows about interpretation of standard Python opcodes
    minus the ones related to nested scopes."""

    bytecode_spec = bytecode_spec
    opcode_method_names = bytecode_spec.method_names
    opcodedesc = bytecode_spec.opcodedesc
    opdescmap = bytecode_spec.opdescmap
    HAVE_ARGUMENT = bytecode_spec.HAVE_ARGUMENT

    ### opcode dispatch ###

    def dispatch(self, pycode, next_instr, ec):
        # For the sequel, force 'next_instr' to be unsigned for performance
        next_instr = r_uint(next_instr)
        co_code = pycode.co_code

        try:
            while True:
                next_instr = self.handle_bytecode(co_code, next_instr, ec)
        except ExitFrame:
            return self.popvalue()

    def handle_bytecode(self, co_code, next_instr, ec):
        try:
            next_instr = self.dispatch_bytecode(co_code, next_instr, ec)
        except OperationError, operr:
            next_instr = self.handle_operation_error(ec, operr)
        except RaiseWithExplicitTraceback, e:
            next_instr = self.handle_operation_error(ec, e.operr,
                                                     attach_tb=False)
        except KeyboardInterrupt:
            next_instr = self.handle_asynchronous_error(ec,
                self.space.w_KeyboardInterrupt)
        except MemoryError:
            next_instr = self.handle_asynchronous_error(ec,
                self.space.w_MemoryError)
        except rstackovf.StackOverflow, e:
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
                    trace = self.w_f_trace
                    if trace is not None:
                        self.w_f_trace = None
                    try:
                        ec.bytecode_trace_after_exception(self)
                    finally:
                        if trace is not None:
                            self.w_f_trace = trace
                except OperationError, e:
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
        space = self.space
        while True:
            self.last_instr = intmask(next_instr)
            if not jit.we_are_jitted():
                ec.bytecode_trace(self)
                next_instr = r_uint(self.last_instr)
            opcode = ord(co_code[next_instr])
            #print 'executing', self.last_instr, bytecode_spec.method_names[opcode]
            next_instr += 1

            if opcode >= self.HAVE_ARGUMENT:
                lo = ord(co_code[next_instr])
                hi = ord(co_code[next_instr+1])
                next_instr += 2
                oparg = (hi * 256) | lo
            else:
                oparg = 0

            # note: the structure of the code here is such that it makes
            # (after translation) a big "if/elif" chain, which is then
            # turned into a switch().  It starts here: even if the first
            # one is not an "if" but a "while" the effect is the same.

            while opcode == self.opcodedesc.EXTENDED_ARG.index:
                opcode = ord(co_code[next_instr])
                if opcode < self.HAVE_ARGUMENT:
                    raise BytecodeCorruption
                lo = ord(co_code[next_instr+1])
                hi = ord(co_code[next_instr+2])
                next_instr += 3
                oparg = (oparg * 65536) | (hi * 256) | lo

            if opcode == self.opcodedesc.RETURN_VALUE.index:
                w_returnvalue = self.popvalue()
                block = self.unrollstack(SReturnValue.kind)
                if block is None:
                    self.pushvalue(w_returnvalue)   # XXX ping pong
                    raise Return
                else:
                    unroller = SReturnValue(w_returnvalue)
                    next_instr = block.handle(self, unroller)
                    return next_instr    # now inside a 'finally' block

            if opcode == self.opcodedesc.END_FINALLY.index:
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

            if opcode == self.opcodedesc.JUMP_ABSOLUTE.index:
                return self.jump_absolute(oparg, ec)

            if we_are_translated():
                for opdesc in unrolling_all_opcode_descs:
                    # static checks to skip this whole case if necessary
                    if opdesc.bytecode_spec is not self.bytecode_spec:
                        continue
                    if not opdesc.is_enabled(space):
                        continue
                    if opdesc.methodname in (
                        'EXTENDED_ARG', 'RETURN_VALUE',
                        'END_FINALLY', 'JUMP_ABSOLUTE'):
                        continue   # opcodes implemented above

                    # the following "if" is part of the big switch described
                    # above.
                    if opcode == opdesc.index:
                        # dispatch to the opcode method
                        meth = getattr(self, opdesc.methodname)
                        res = meth(oparg, next_instr)
                        # !! warning, for the annotator the next line is not
                        # comparing an int and None - you can't do that.
                        # Instead, it's constant-folded to either True or False
                        if res is not None:
                            next_instr = res
                        break
                else:
                    self.MISSING_OPCODE(oparg, next_instr)

            else:  # when we are not translated, a list lookup is much faster
                methodname = self.opcode_method_names[opcode]
                try:
                    meth = getattr(self, methodname)
                except AttributeError:
                    raise BytecodeCorruption("unimplemented opcode, ofs=%d, "
                                             "code=%d, name=%s" %
                                             (self.last_instr, opcode,
                                              methodname))
                try:
                    res = meth(oparg, next_instr)
                except Exception:
                    if 0:
                        import dis, sys
                        print "*** %s at offset %d (%s)" % (sys.exc_info()[0],
                                                            self.last_instr,
                                                            methodname)
                        try:
                            dis.dis(co_code)
                        except:
                            pass
                    raise
                if res is not None:
                    next_instr = res

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

    def LOAD_FAST(self, varindex, next_instr):
        # access a local variable directly
        w_value = self.locals_stack_w[varindex]
        if w_value is None:
            self._load_fast_failed(varindex)
        self.pushvalue(w_value)
    LOAD_FAST._always_inline_ = True

    def _load_fast_failed(self, varindex):
        varname = self.getlocalvarname(varindex)
        message = "local variable '%s' referenced before assignment"
        raise operationerrfmt(self.space.w_UnboundLocalError, message, varname)
    _load_fast_failed._dont_inline_ = True

    def LOAD_CONST(self, constindex, next_instr):
        w_const = self.getconstant_w(constindex)
        self.pushvalue(w_const)

    def STORE_FAST(self, varindex, next_instr):
        w_newvalue = self.popvalue()
        assert w_newvalue is not None
        self.locals_stack_w[varindex] = w_newvalue

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

    def DUP_TOP(self, oparg, next_instr):
        w_1 = self.peekvalue()
        self.pushvalue(w_1)

    def DUP_TOP_TWO(self, oparg, next_instr):
        self.dupvalues(2)

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
        print_item_to(self.space, w_item, w_stream)

    def PRINT_ITEM(self, oparg, next_instr):
        w_item = self.popvalue()
        print_item(self.space, w_item)

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

    @jit.unroll_safe
    def RAISE_VARARGS(self, nbargs, next_instr):
        space = self.space
        if nbargs > 2:
            raise BytecodeCorruption("bad RAISE_VARARGS oparg")
        if nbargs == 0:
            frame = self
            ec = self.space.getexecutioncontext()
            while frame:
                if frame.last_exception is not None:
                    operror = frame.last_exception
                    break
                frame = frame.f_backref()
            else:
                raise OperationError(space.w_RuntimeError,
                    space.wrap("No active exception to reraise"))
            # re-raise, no new traceback obj will be attached
            self.last_exception = operror
            raise RaiseWithExplicitTraceback(operror)
        if nbargs == 2:
            w_cause = self.popvalue()
            if space.exception_is_valid_obj_as_class_w(w_cause):
                w_cause = space.call_function(w_cause)
        else:
            w_cause = None
        w_value = self.popvalue()
        if space.exception_is_valid_obj_as_class_w(w_value):
            w_type = w_value
            w_value = space.call_function(w_type)
        else:
            w_type = space.type(w_value)
        operror = OperationError(w_type, w_value, w_cause=w_cause)
        operror.normalize_exception(space)
        tb = space.getattr(w_value, space.wrap('__traceback__'))
        if not space.is_w(tb, space.w_None):
            operror.set_traceback(tb)
        raise operror

    def LOAD_LOCALS(self, oparg, next_instr):
        self.pushvalue(self.w_locals)

    def STORE_LOCALS(self, oparg, next_instr):
        self.w_locals = self.popvalue()

    def exec_(self, w_prog, w_globals, w_locals):
        """The builtins.exec function."""
        space = self.space
        ec = space.getexecutioncontext()
        flags = ec.compiler.getcodeflags(self.pycode)

        if space.isinstance_w(w_prog, space.gettypeobject(PyCode.typedef)):
            code = space.interp_w(PyCode, w_prog)
        else:
            from pypy.interpreter.astcompiler import consts
            flags |= consts.PyCF_SOURCE_IS_UTF8
            source, flags = source_as_str(space, w_prog, 'exec',
                                          "string, bytes or code", flags)
            code = ec.compiler.compile(source, "<string>", 'exec', flags)

        w_globals, w_locals = ensure_ns(space, w_globals, w_locals, 'exec',
                                        self)
        space.call_method(w_globals, 'setdefault', space.wrap('__builtins__'),
                          space.wrap(self.get_builtin()))

        plain = (self.w_locals is not None and
                 space.is_w(w_locals, self.w_locals))
        if plain:
            w_locals = self.getdictscope()
        code.exec_code(space, w_globals, w_locals)
        if plain:
            self.setdictscope(w_locals)

    def POP_EXCEPT(self, oparg, next_instr):
        assert self.space.py3k
        block = self.pop_block()
        block.cleanup(self)
        return

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
        # the following logic is a mess for the flow objspace,
        # so we hide it specially in the space :-/
        if self.space._check_constant_interp_w_or_w_None(SuspendedUnroller, w_top):
            # case of a finally: block
            unroller = self.space.interpclass_w(w_top)
            return unroller
        else:
            # case of an except: block.  We popped the exception type
            self.popvalue()        #     Now we pop the exception value
            unroller = self.space.interpclass_w(self.popvalue())
            assert unroller is not None
            return unroller

    def LOAD_BUILD_CLASS(self, oparg, next_instr):
        w_build_class = self.get_builtin().getdictvalue(
            self.space, '__build_class__')
        if w_build_class is None:
            raise OperationError(self.space.w_ImportError,
                                 self.space.wrap("__build_class__ not found"))
        self.pushvalue(w_build_class)

    def STORE_NAME(self, varindex, next_instr):
        varname = self.getname_u(varindex)
        w_newvalue = self.popvalue()
        self.space.setitem_str(self.w_locals, varname, w_newvalue)

    def DELETE_NAME(self, varindex, next_instr):
        w_varname = self.getname_w(varindex)
        try:
            self.space.delitem(self.w_locals, w_varname)
        except OperationError, e:
            # catch KeyErrors and turn them into NameErrors
            if not e.match(self.space, self.space.w_KeyError):
                raise
            message = "name '%s' is not defined"
            raise operationerrfmt(self.space.w_NameError, message,
                                  self.space.str_w(w_varname))

    def UNPACK_SEQUENCE(self, itemcount, next_instr):
        w_iterable = self.popvalue()
        items = self.space.fixedview_unroll(w_iterable, itemcount)
        self.pushrevvalues(itemcount, items)

    @jit.unroll_safe
    def UNPACK_EX(self, oparg, next_instr):
        "a, *b, c = range(10)"
        left = oparg & 0xFF
        right = (oparg & 0xFF00) >> 8
        w_iterable = self.popvalue()
        items = self.space.fixedview(w_iterable)
        itemcount = len(items)
        if right > itemcount:
            count = left + right
            if count == 1:
                plural = ''
            else:
                plural = 's'
            raise operationerrfmt(self.space.w_ValueError,
                                  "need more than %d value%s to unpack",
                                  left + right, plural)
        right = itemcount - right
        assert right >= 0
        # push values in reverse order
        i = itemcount - 1
        while i >= right:
            self.pushvalue(items[i])
            i -= 1
        self.pushvalue(self.space.newlist(items[left:right]))
        i = left - 1
        while i >= 0:
            self.pushvalue(items[i])
            i -= 1

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
        self.space.setitem_str(self.w_globals, varname, w_newvalue)

    def DELETE_GLOBAL(self, nameindex, next_instr):
        w_varname = self.getname_w(nameindex)
        self.space.delitem(self.w_globals, w_varname)

    def LOAD_NAME(self, nameindex, next_instr):
        w_varname = self.getname_w(nameindex)
        if self.w_locals is not self.w_globals:
            w_value = self.space.finditem(self.w_locals, w_varname)
            if w_value is not None:
                self.pushvalue(w_value)
                return
        # fall-back
        varname = self.space.str_w(w_varname)
        w_value = self._load_global(varname)
        if w_value is None:
            message = "name '%s' is not defined"
            raise operationerrfmt(self.space.w_NameError, message, varname)
        self.pushvalue(w_value)

    def _load_global(self, varname):
        w_value = self.space.finditem_str(self.w_globals, varname)
        if w_value is None:
            # not in the globals, now look in the built-ins
            w_value = self.get_builtin().getdictvalue(self.space, varname)
        return w_value
    _load_global._always_inline_ = True

    def _load_global_failed(self, varname):
        message = "global name '%s' is not defined"
        raise operationerrfmt(self.space.w_NameError, message, varname)
    _load_global_failed._dont_inline_ = True

    def LOAD_GLOBAL(self, nameindex, next_instr):
        varname = self.getname_u(nameindex)
        w_value = self._load_global(varname)
        if w_value is None:
            self._load_global_failed(varname)
        self.pushvalue(w_value)
    LOAD_GLOBAL._always_inline_ = True

    def DELETE_FAST(self, varindex, next_instr):
        if self.locals_stack_w[varindex] is None:
            varname = self.getlocalvarname(varindex)
            message = "local variable '%s' referenced before assignment"
            raise operationerrfmt(self.space.w_UnboundLocalError, message,
                                  varname)
        self.locals_stack_w[varindex] = None

    def BUILD_TUPLE(self, itemcount, next_instr):
        items = self.popvalues(itemcount)
        w_tuple = self.space.newtuple(items)
        self.pushvalue(w_tuple)

    def BUILD_LIST(self, itemcount, next_instr):
        items = self.popvalues_mutable(itemcount)
        w_list = self.space.newlist(items)
        self.pushvalue(w_list)

    def BUILD_LIST_FROM_ARG(self, _, next_instr):
        # this is a little dance, because list has to be before the
        # value
        last_val = self.popvalue()
        try:
            lgt = self.space.len_w(last_val)
        except OperationError, e:
            if e.async(self.space):
                raise
            lgt = 0 # oh well
        self.pushvalue(self.space.newlist([], sizehint=lgt))
        self.pushvalue(last_val)

    def LOAD_ATTR(self, nameindex, next_instr):
        "obj.attributename"
        w_obj = self.popvalue()
        if (self.space.config.objspace.std.withmapdict
            and not jit.we_are_jitted()):
            from pypy.objspace.std.mapdict import LOAD_ATTR_caching
            w_value = LOAD_ATTR_caching(self.getcode(), w_obj, nameindex)
        else:
            w_attributename = self.getname_w(nameindex)
            w_value = self.space.getattr(w_obj, w_attributename)
        self.pushvalue(w_value)
    LOAD_ATTR._always_inline_ = True

    def cmp_lt(self, w_1, w_2):
        return self.space.lt(w_1, w_2)

    def cmp_le(self, w_1, w_2):
        return self.space.le(w_1, w_2)

    def cmp_eq(self, w_1, w_2):
        return self.space.eq(w_1, w_2)

    def cmp_ne(self, w_1, w_2):
        return self.space.ne(w_1, w_2)

    def cmp_gt(self, w_1, w_2):
        return self.space.gt(w_1, w_2)

    def cmp_ge(self, w_1, w_2):
        return self.space.ge(w_1, w_2)

    def cmp_in(self, w_1, w_2):
        return self.space.contains(w_2, w_1)

    def cmp_not_in(self, w_1, w_2):
        return self.space.not_(self.space.contains(w_2, w_1))

    def cmp_is(self, w_1, w_2):
        return self.space.is_(w_1, w_2)

    def cmp_is_not(self, w_1, w_2):
        return self.space.not_(self.space.is_(w_1, w_2))

    @jit.unroll_safe
    def cmp_exc_match(self, w_1, w_2):
        space = self.space
        if space.isinstance_w(w_2, space.w_tuple):
            for w_type in space.fixedview(w_2):
                if not space.exception_is_valid_class_w(w_type):
                    raise OperationError(space.w_TypeError,
                                         space.wrap(CANNOT_CATCH_MSG))
        elif not space.exception_is_valid_class_w(w_2):
            raise OperationError(space.w_TypeError,
                                 space.wrap(CANNOT_CATCH_MSG))
        return space.newbool(space.exception_match(w_1, w_2))

    def COMPARE_OP(self, testnum, next_instr):
        w_2 = self.popvalue()
        w_1 = self.popvalue()
        w_result = None
        for i, attr in unrolling_compare_dispatch_table:
            if i == testnum:
                w_result = getattr(self, attr)(w_1, w_2)
                break
        else:
            raise BytecodeCorruption, "bad COMPARE_OP oparg"
        self.pushvalue(w_result)

    def IMPORT_NAME(self, nameindex, next_instr):
        space = self.space
        w_modulename = self.getname_w(nameindex)
        w_fromlist = self.popvalue()

        w_flag = self.popvalue()
        try:
            if space.int_w(w_flag) == -1:
                w_flag = None
        except OperationError, e:
            if e.async(space):
                raise

        w_import = self.get_builtin().getdictvalue(space, '__import__')
        if w_import is None:
            raise OperationError(space.w_ImportError,
                                 space.wrap("__import__ not found"))
        w_locals = self.w_locals
        if w_locals is None:            # CPython does this
            w_locals = space.w_None
        w_globals = self.w_globals
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
        except OperationError, e:
            if not e.match(self.space, self.space.w_AttributeError):
                raise
            raise operationerrfmt(self.space.w_ImportError,
                                  "cannot import name '%s'",
                                  self.space.str_w(w_name))
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

    def GET_ITER(self, oparg, next_instr):
        w_iterable = self.popvalue()
        w_iterator = self.space.iter(w_iterable)
        self.pushvalue(w_iterator)

    def FOR_ITER(self, jumpby, next_instr):
        w_iterator = self.peekvalue()
        try:
            w_nextitem = self.space.next(w_iterator)
        except OperationError, e:
            if not e.match(self.space, self.space.w_StopIteration):
                raise
            # iterator exhausted
            self.popvalue()
            next_instr += jumpby
        else:
            self.pushvalue(w_nextitem)
        return next_instr

    def FOR_LOOP(self, oparg, next_instr):
        raise BytecodeCorruption, "old opcode, no longer in use"

    def SETUP_LOOP(self, offsettoend, next_instr):
        block = LoopBlock(self.valuestackdepth,
                          next_instr + offsettoend, self.lastblock)
        self.lastblock = block

    def SETUP_EXCEPT(self, offsettoend, next_instr):
        block = ExceptBlock(self.valuestackdepth,
                            next_instr + offsettoend, self.lastblock)
        self.lastblock = block

    def SETUP_FINALLY(self, offsettoend, next_instr):
        block = FinallyBlock(self.valuestackdepth,
                             next_instr + offsettoend, self.lastblock)
        self.lastblock = block

    def SETUP_WITH(self, offsettoend, next_instr):
        w_manager = self.peekvalue()
        w_enter = self.space.lookup(w_manager, "__enter__")
        w_descr = self.space.lookup(w_manager, "__exit__")
        if w_enter is None or w_descr is None:
            typename = self.space.type(w_manager).getname(self.space)
            raise operationerrfmt(self.space.w_AttributeError,
                "'%s' object is not a context manager"
                " (no __enter__/__exit__ method)", typename)
        w_exit = self.space.get(w_descr, w_manager)
        self.settopvalue(w_exit)
        w_result = self.space.get_and_call_function(w_enter, w_manager)
        block = WithBlock(self.valuestackdepth,
                          next_instr + offsettoend, self.lastblock)
        self.lastblock = block
        self.pushvalue(w_result)

    def WITH_CLEANUP(self, oparg, next_instr):
        # see comment in END_FINALLY for stack state
        w_unroller = self.popvalue()
        w_exitfunc = self.popvalue()
        self.pushvalue(w_unroller)
        unroller = self.space.interpclass_w(w_unroller)
        is_app_exc = (unroller is not None and
                      isinstance(unroller, SApplicationException))
        if is_app_exc:
            operr = unroller.operr
            old_last_exception = self.last_exception
            self.last_exception = operr
            w_traceback = self.space.wrap(operr.get_traceback())
            w_suppress = self.call_contextmanager_exit_function(
                w_exitfunc,
                operr.w_type,
                operr.get_w_value(self.space),
                w_traceback)
            self.last_exception = old_last_exception
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
                key = self.space.identifier_w(w_key)
                keywords[n_keywords] = key
                keywords_w[n_keywords] = w_value
        else:
            keywords = None
            keywords_w = None
        arguments = self.popvalues(n_arguments)
        args = self.argument_factory(arguments, keywords, keywords_w, w_star,
                                     w_starstar)
        w_function  = self.popvalue()
        if self.is_being_profiled and function.is_builtin_code(w_function):
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

    @jit.unroll_safe
    def _make_function(self, oparg, freevars=None):
        space = self.space
        w_codeobj = self.popvalue()
        codeobj = self.space.interp_w(PyCode, w_codeobj)
        if freevars is not None:
            # Pop freevars
            self.popvalue()
        posdefaults = oparg & 0xFF
        kwdefaults = (oparg >> 8) & 0xFF
        num_annotations = (oparg >> 16) & 0xFF
        w_ann = None
        if num_annotations:
            names_w = space.fixedview(self.popvalue())
            w_ann = space.newdict(strdict=True)
            for i in range(len(names_w) - 1, -1, -1):
                space.setitem(w_ann, names_w[i], self.popvalue())
        defaultarguments = self.popvalues(posdefaults)
        w_kw_defs = None
        if kwdefaults:
            w_kw_defs = space.newdict(strdict=True)
            for i in range(kwdefaults - 1, -1, -1):
                w_name = self.popvalue()
                w_def = self.popvalue()
                space.setitem(w_kw_defs, w_def, w_name)
        fn = function.Function(space, codeobj, self.w_globals, defaultarguments,
                               w_kw_defs, freevars, w_ann)
        self.pushvalue(space.wrap(fn))

    def MAKE_FUNCTION(self, oparg, next_instr):
        return self._make_function(oparg)

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
        for i in range(itemcount):
            w_item = self.popvalue()
            self.space.call_method(w_set, 'add', w_item)
        self.pushvalue(w_set)

    def STORE_MAP(self, oparg, next_instr):
        w_key = self.popvalue()
        w_value = self.popvalue()
        w_dict = self.peekvalue()
        self.space.setitem(w_dict, w_key, w_value)


class __extend__(pyframe.CPythonFrame):

    def JUMP_IF_FALSE(self, stepby, next_instr):
        w_cond = self.peekvalue()
        if not self.space.is_true(w_cond):
            next_instr += stepby
        return next_instr

    def JUMP_IF_TRUE(self, stepby, next_instr):
        w_cond = self.peekvalue()
        if self.space.is_true(w_cond):
            next_instr += stepby
        return next_instr

    def BUILD_MAP(self, itemcount, next_instr):
        if sys.version_info >= (2, 6):
            # We could pre-allocate a dict here
            # but for the moment this code is not translated.
            pass
        else:
            if itemcount != 0:
                raise BytecodeCorruption
        w_dict = self.space.newdict()
        self.pushvalue(w_dict)

    def STORE_MAP(self, zero, next_instr):
        if sys.version_info >= (2, 6):
            w_key = self.popvalue()
            w_value = self.popvalue()
            w_dict = self.peekvalue()
            self.space.setitem(w_dict, w_key, w_value)
        else:
            raise BytecodeCorruption

    def LIST_APPEND(self, oparg, next_instr):
        w = self.popvalue()
        if sys.version_info < (2, 7):
            v = self.popvalue()
        else:
            v = self.peekvalue(oparg - 1)
        self.space.call_method(v, 'append', w)


### ____________________________________________________________ ###

class ExitFrame(Exception):
    pass

class Return(ExitFrame):
    """Raised when exiting a frame via a 'return' statement."""
class Yield(ExitFrame):
    """Raised when exiting a frame via a 'yield' statement."""

class RaiseWithExplicitTraceback(Exception):
    """Raised at interp-level by a 0-argument 'raise' statement."""
    def __init__(self, operr):
        self.operr = operr


### Frame Blocks ###

class SuspendedUnroller(Wrappable):
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

    def __init__(self, valuestackdepth, handlerposition, previous):
        self.handlerposition = handlerposition
        self.valuestackdepth = valuestackdepth
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


class ExceptHandlerBlock(FrameBlock):
    """
    This is a special, implicit block type which is created when entering an
    except handler. It does not belong to any opcode
    """

    _immutable_ = True
    _opname = 'EXCEPT_HANDLER_BLOCK' # it's not associated to any opcode
    handling_mask = 0 # this block is never handled, only popped by POP_EXCEPT

    def handle(self, frame, unroller):
        assert False # never called

    def cleanupstack(self, frame):
        frame.dropvaluesuntil(self.valuestackdepth+1)
        w_last_exception = frame.popvalue()
        if not isinstance(w_last_exception, W_OperationError):
            msg = "expected an OperationError, got %s" % (
                frame.space.str_w(w_last_exception))
            raise BytecodeCorruption(msg)
        frame.last_exception = w_last_exception.operr
        FrameBlock.cleanupstack(self, frame)


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
        if frame.space.py3k:
            # this is popped by POP_EXCEPT, which is present only in py3k
            w_last_exception = W_OperationError(frame.last_exception)
            w_last_exception = frame.space.wrap(w_last_exception)
            frame.pushvalue(w_last_exception)
            block = ExceptHandlerBlock(self.valuestackdepth,
                                       0, frame.lastblock)
            frame.lastblock = block
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
    restore_last_exception = True # set to False by WithBlock

    def handle(self, frame, unroller):
        # any abnormal reason for unrolling a finally: triggers the end of
        # the block unrolling and the entering the finally: handler.
        # see comments in cleanup().
        self.cleanupstack(frame)
        operationerr = None
        if isinstance(unroller, SApplicationException):
            operationerr = unroller.operr
            operationerr.normalize_exception(frame.space)
        frame.pushvalue(frame.space.wrap(unroller))
        if operationerr and self.restore_last_exception:
            frame.last_exception = operationerr
        return r_uint(self.handlerposition)   # jump to the handler



class WithBlock(FinallyBlock):

    _immutable_ = True
    restore_last_exception = False

    def handle(self, frame, unroller):
        if isinstance(unroller, SApplicationException):
            unroller.operr.normalize_exception(frame.space)
        return FinallyBlock.handle(self, frame, unroller)

block_classes = {'SETUP_LOOP': LoopBlock,
                 'SETUP_EXCEPT': ExceptBlock,
                 'SETUP_FINALLY': FinallyBlock,
                 'SETUP_WITH': WithBlock,
                 }


class W_OperationError(Wrappable):
    """
    Tiny applevel wrapper around an OperationError.
    """

    def __init__(self, operr):
        self.operr = operr


def source_as_str(space, w_source, funcname, what, flags):
    """Return source code as str0 with adjusted compiler flags

    w_source must be a str or support the buffer interface
    """
    from pypy.interpreter.astcompiler import consts

    if space.isinstance_w(w_source, space.w_unicode):
        from pypy.objspace.std.unicodetype import encode_object
        w_source = encode_object(space, w_source, None, None)
        source = space.bytes0_w(w_source)
        flags |= consts.PyCF_IGNORE_COOKIE
    elif space.isinstance_w(w_source, space.w_bytes):
        source = space.bytes0_w(w_source)
    else:
        try:
            source = space.bufferstr0_new_w(w_source)
        except OperationError as e:
            if not e.match(space, space.w_TypeError):
                raise
            raise operationerrfmt(space.w_TypeError,
                                  "%s() arg 1 must be a %s object",
                                  funcname, what)
    return source, flags


def ensure_ns(space, w_globals, w_locals, funcname, caller=None):
    """Ensure globals/locals exist and are of the correct type"""
    if (not space.is_none(w_globals) and
        not space.isinstance_w(w_globals, space.w_dict)):
        raise operationerrfmt(space.w_TypeError,
                              '%s() arg 2 must be a dict, not %s',
                              funcname, space.type(w_globals).getname(space))
    if (not space.is_none(w_locals) and
        space.lookup(w_locals, '__getitem__') is None):
        raise operationerrfmt(space.w_TypeError,
                              '%s() arg 3 must be a mapping or None, not %s',
                              funcname, space.type(w_locals).getname(space))

    if space.is_none(w_globals):
        if caller is None:
            caller = space.getexecutioncontext().gettopframe_nohidden()
        if caller is None:
            w_globals = space.newdict()
            if space.is_none(w_locals):
                w_locals = w_globals
        else:
            w_globals = caller.w_globals
            if space.is_none(w_locals):
                w_locals = caller.getdictscope()
    elif space.is_none(w_locals):
        w_locals = w_globals

    return w_globals, w_locals


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
        # give to write() an argument which is either a string or a unicode
        # (and let it deals itself with unicode handling)
        if not isinstance(x, str):
            x = str(x)
        try:
            stream.write(x)
        except UnicodeEncodeError:
            print_unencodable_to(x, stream)

    def print_unencodable_to(x, stream):
        encoding = stream.encoding
        encoded = x.encode(encoding, 'backslashreplace')
        buffer = getattr(stream, 'buffer', None)
        if buffer is not None:
             buffer.write(encoded)
        else:
            escaped = encoded.decode(encoding, 'strict')
            stream.write(escaped)

    def print_item(x):
        print_item_to(x, sys_stdout())

    def print_newline_to(stream):
        stream.write("\n")

    def print_newline():
        print_newline_to(sys_stdout())
''', filename=__file__)

sys_stdout      = app.interphook('sys_stdout')
print_expr      = app.interphook('print_expr')
print_item      = app.interphook('print_item')
print_item_to   = app.interphook('print_item_to')
print_newline   = app.interphook('print_newline')
print_newline_to= app.interphook('print_newline_to')

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
