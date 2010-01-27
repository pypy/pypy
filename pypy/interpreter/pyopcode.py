"""
Implementation of a part of the standard Python opcodes.

The rest, dealing with variables in optimized ways, is in nestedscope.py.
"""

import sys
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import UnpackValueError, Wrappable
from pypy.interpreter import gateway, function, eval
from pypy.interpreter import pyframe, pytraceback
from pypy.interpreter.pycode import PyCode
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib import jit
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.tool.stdlib_opcode import opcodedesc, HAVE_ARGUMENT
from pypy.tool.stdlib_opcode import unrolling_opcode_descs
from pypy.tool.stdlib_opcode import opcode_method_names
from pypy.rlib.unroll import unrolling_iterable

def unaryoperation(operationname):
    """NOT_RPYTHON"""
    def opimpl(f, *ignored):
        operation = getattr(f.space, operationname)
        w_1 = f.popvalue()
        w_result = operation(w_1)
        f.pushvalue(w_result)
    opimpl.unaryop = operationname

    return func_with_new_name(opimpl, "opcode_impl_for_%s" % operationname)

def binaryoperation(operationname):
    """NOT_RPYTHON"""    
    def opimpl(f, *ignored):
        operation = getattr(f.space, operationname)
        w_2 = f.popvalue()
        w_1 = f.popvalue()
        w_result = operation(w_1, w_2)
        f.pushvalue(w_result)
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
    
    # for logbytecode:
    last_opcode = -1
    
    ### opcode dispatch ###

    def dispatch(self, pycode, next_instr, ec):
        # For the sequel, force 'next_instr' to be unsigned for performance
        from pypy.rlib import rstack # for resume points

        next_instr = r_uint(next_instr)
        co_code = pycode.co_code

        try:
            while True:
                next_instr = self.handle_bytecode(co_code, next_instr, ec)
                rstack.resume_point("dispatch", self, co_code, ec,
                                    returns=next_instr)
        except ExitFrame:
            return self.popvalue()

    def handle_bytecode(self, co_code, next_instr, ec):
        from pypy.rlib import rstack # for resume points

        try:
            next_instr = self.dispatch_bytecode(co_code, next_instr, ec)
            rstack.resume_point("handle_bytecode", self, co_code, ec,
                                returns=next_instr)
        except OperationError, operr:
            next_instr = self.handle_operation_error(ec, operr)
        except Reraise:
            operr = self.last_exception
            next_instr = self.handle_operation_error(ec, operr,
                                                     attach_tb=False)
        except RaiseWithExplicitTraceback, e:
            next_instr = self.handle_operation_error(ec, e.operr,
                                                     attach_tb=False)
        except KeyboardInterrupt:
            next_instr = self.handle_asynchronous_error(ec,
                self.space.w_KeyboardInterrupt)
        except MemoryError:
            next_instr = self.handle_asynchronous_error(ec,
                self.space.w_MemoryError)
        except NotImplementedError:
            raise
        except RuntimeError, e:
            if we_are_translated():
                # stack overflows should be the only kind of RuntimeErrors
                # in translated PyPy
                msg = "internal error (stack overflow?)"
            else:
                msg = str(e)
            next_instr = self.handle_asynchronous_error(ec,
                self.space.w_RuntimeError,
                self.space.wrap(msg))
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
                    self.w_f_trace = None
                    try:
                        ec.bytecode_trace_after_exception(self)
                    finally:
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

    @jit.unroll_safe
    def dispatch_bytecode(self, co_code, next_instr, ec):
        space = self.space
        while True:
            self.last_instr = intmask(next_instr)
            if not jit.we_are_jitted():
                ec.bytecode_trace(self)
                next_instr = r_uint(self.last_instr)
            opcode = ord(co_code[next_instr])
            next_instr += 1
            if space.config.objspace.logbytecodes:
                space.bytecodecounts[opcode] += 1
                try:
                    probs = space.bytecodetransitioncount[self.last_opcode]
                except KeyError:
                    probs = space.bytecodetransitioncount[self.last_opcode] = {}
                probs[opcode] = probs.get(opcode, 0) + 1
                self.last_opcode = opcode

            if opcode >= HAVE_ARGUMENT:
                lo = ord(co_code[next_instr])
                hi = ord(co_code[next_instr+1])
                next_instr += 2
                oparg = (hi << 8) | lo
            else:
                oparg = 0

            while opcode == opcodedesc.EXTENDED_ARG.index:
                opcode = ord(co_code[next_instr])
                if opcode < HAVE_ARGUMENT:
                    raise BytecodeCorruption
                lo = ord(co_code[next_instr+1])
                hi = ord(co_code[next_instr+2])
                next_instr += 3
                oparg = (oparg << 16) | (hi << 8) | lo

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

            if opcode == opcodedesc.YIELD_VALUE.index:
                #self.last_instr = intmask(next_instr - 1) XXX clean up!
                raise Yield

            if opcode == opcodedesc.END_FINALLY.index:
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

            if opcode == opcodedesc.JUMP_ABSOLUTE.index:
                return self.JUMP_ABSOLUTE(oparg, next_instr, ec)

            if we_are_translated():
                from pypy.rlib import rstack # for resume points

                for opdesc in unrolling_opcode_descs:
                    # static checks to skip this whole case if necessary
                    if not opdesc.is_enabled(space):
                        continue
                    if not hasattr(pyframe.PyFrame, opdesc.methodname):
                        continue   # e.g. for JUMP_FORWARD, implemented above

                    if opcode == opdesc.index:
                        # dispatch to the opcode method
                        meth = getattr(self, opdesc.methodname)
                        res = meth(oparg, next_instr)
                        if opdesc.index == opcodedesc.CALL_FUNCTION.index:
                            rstack.resume_point("dispatch_call", self, co_code, next_instr, ec)
                        # !! warning, for the annotator the next line is not
                        # comparing an int and None - you can't do that.
                        # Instead, it's constant-folded to either True or False
                        if res is not None:
                            next_instr = res
                        break
                else:
                    self.MISSING_OPCODE(oparg, next_instr)

            else:  # when we are not translated, a list lookup is much faster
                methodname = opcode_method_names[opcode]
                res = getattr(self, methodname)(oparg, next_instr)
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

    #  the 'self' argument of opcode implementations is called 'f'
    #  for historical reasons

    def NOP(f, *ignored):
        pass

    def LOAD_FAST(f, varindex, *ignored):
        # access a local variable directly
        w_value = f.fastlocals_w[varindex]
        if w_value is None:
            f._load_fast_failed(varindex)
        f.pushvalue(w_value)
    LOAD_FAST._always_inline_ = True

    def _load_fast_failed(f, varindex):
        varname = f.getlocalvarname(varindex)
        message = "local variable '%s' referenced before assignment"
        raise operationerrfmt(f.space.w_UnboundLocalError, message, varname)
    _load_fast_failed._dont_inline_ = True

    def LOAD_CONST(f, constindex, *ignored):
        w_const = f.getconstant_w(constindex)
        f.pushvalue(w_const)

    def STORE_FAST(f, varindex, *ignored):
        w_newvalue = f.popvalue()
        assert w_newvalue is not None
        f.fastlocals_w[varindex] = w_newvalue
        #except:
        #    print "exception: got index error"
        #    print " varindex:", varindex
        #    print " len(locals_w)", len(f.locals_w)
        #    import dis
        #    print dis.dis(f.pycode)
        #    print "co_varnames", f.pycode.co_varnames
        #    print "co_nlocals", f.pycode.co_nlocals
        #    raise

    def POP_TOP(f, *ignored):
        f.popvalue()

    def ROT_TWO(f, *ignored):
        w_1 = f.popvalue()
        w_2 = f.popvalue()
        f.pushvalue(w_1)
        f.pushvalue(w_2)

    def ROT_THREE(f, *ignored):
        w_1 = f.popvalue()
        w_2 = f.popvalue()
        w_3 = f.popvalue()
        f.pushvalue(w_1)
        f.pushvalue(w_3)
        f.pushvalue(w_2)

    def ROT_FOUR(f, *ignored):
        w_1 = f.popvalue()
        w_2 = f.popvalue()
        w_3 = f.popvalue()
        w_4 = f.popvalue()
        f.pushvalue(w_1)
        f.pushvalue(w_4)
        f.pushvalue(w_3)
        f.pushvalue(w_2)

    def DUP_TOP(f, *ignored):
        w_1 = f.peekvalue()
        f.pushvalue(w_1)

    def DUP_TOPX(f, itemcount, *ignored):
        assert 1 <= itemcount <= 5, "limitation of the current interpreter"
        f.dupvalues(itemcount)

    UNARY_POSITIVE = unaryoperation("pos")
    UNARY_NEGATIVE = unaryoperation("neg")
    UNARY_NOT      = unaryoperation("not_")
    UNARY_CONVERT  = unaryoperation("repr")
    UNARY_INVERT   = unaryoperation("invert")

    def BINARY_POWER(f, *ignored):
        w_2 = f.popvalue()
        w_1 = f.popvalue()
        w_result = f.space.pow(w_1, w_2, f.space.w_None)
        f.pushvalue(w_result)

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

    def INPLACE_POWER(f, *ignored):
        w_2 = f.popvalue()
        w_1 = f.popvalue()
        w_result = f.space.inplace_pow(w_1, w_2)
        f.pushvalue(w_result)

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

    def slice(f, w_start, w_end):
        w_obj = f.popvalue()
        w_result = f.space.getslice(w_obj, w_start, w_end)
        f.pushvalue(w_result)

    def SLICE_0(f, *ignored):
        f.slice(f.space.w_None, f.space.w_None)

    def SLICE_1(f, *ignored):
        w_start = f.popvalue()
        f.slice(w_start, f.space.w_None)

    def SLICE_2(f, *ignored):
        w_end = f.popvalue()
        f.slice(f.space.w_None, w_end)

    def SLICE_3(f, *ignored):
        w_end = f.popvalue()
        w_start = f.popvalue()
        f.slice(w_start, w_end)

    def storeslice(f, w_start, w_end):
        w_obj = f.popvalue()
        w_newvalue = f.popvalue()
        f.space.setslice(w_obj, w_start, w_end, w_newvalue)

    def STORE_SLICE_0(f, *ignored):
        f.storeslice(f.space.w_None, f.space.w_None)

    def STORE_SLICE_1(f, *ignored):
        w_start = f.popvalue()
        f.storeslice(w_start, f.space.w_None)

    def STORE_SLICE_2(f, *ignored):
        w_end = f.popvalue()
        f.storeslice(f.space.w_None, w_end)

    def STORE_SLICE_3(f, *ignored):
        w_end = f.popvalue()
        w_start = f.popvalue()
        f.storeslice(w_start, w_end)

    def deleteslice(f, w_start, w_end):
        w_obj = f.popvalue()
        f.space.delslice(w_obj, w_start, w_end)

    def DELETE_SLICE_0(f, *ignored):
        f.deleteslice(f.space.w_None, f.space.w_None)

    def DELETE_SLICE_1(f, *ignored):
        w_start = f.popvalue()
        f.deleteslice(w_start, f.space.w_None)

    def DELETE_SLICE_2(f, *ignored):
        w_end = f.popvalue()
        f.deleteslice(f.space.w_None, w_end)

    def DELETE_SLICE_3(f, *ignored):
        w_end = f.popvalue()
        w_start = f.popvalue()
        f.deleteslice(w_start, w_end)

    def STORE_SUBSCR(f, *ignored):
        "obj[subscr] = newvalue"
        w_subscr = f.popvalue()
        w_obj = f.popvalue()
        w_newvalue = f.popvalue()
        f.space.setitem(w_obj, w_subscr, w_newvalue)

    def DELETE_SUBSCR(f, *ignored):
        "del obj[subscr]"
        w_subscr = f.popvalue()
        w_obj = f.popvalue()
        f.space.delitem(w_obj, w_subscr)

    def PRINT_EXPR(f, *ignored):
        w_expr = f.popvalue()
        print_expr(f.space, w_expr)

    def PRINT_ITEM_TO(f, *ignored):
        w_stream = f.popvalue()
        w_item = f.popvalue()
        if f.space.is_w(w_stream, f.space.w_None):
            w_stream = sys_stdout(f.space)   # grumble grumble special cases
        print_item_to(f.space, w_item, w_stream)

    def PRINT_ITEM(f, *ignored):
        w_item = f.popvalue()
        print_item(f.space, w_item)

    def PRINT_NEWLINE_TO(f, *ignored):
        w_stream = f.popvalue()
        if f.space.is_w(w_stream, f.space.w_None):
            w_stream = sys_stdout(f.space)   # grumble grumble special cases
        print_newline_to(f.space, w_stream)

    def PRINT_NEWLINE(f, *ignored):
        print_newline(f.space)

    def BREAK_LOOP(f, *ignored):
        next_instr = f.unrollstack_and_jump(SBreakLoop.singleton)
        return next_instr

    def CONTINUE_LOOP(f, startofloop, *ignored):
        unroller = SContinueLoop(startofloop)
        next_instr = f.unrollstack_and_jump(unroller)
        return next_instr

    def RAISE_VARARGS(f, nbargs, *ignored):
        space = f.space
        if nbargs == 0:
            operror = space.getexecutioncontext().sys_exc_info()
            if operror is None:
                raise OperationError(space.w_TypeError,
                    space.wrap("raise: no active exception to re-raise"))
            # re-raise, no new traceback obj will be attached
            f.last_exception = operror
            raise Reraise

        w_value = w_traceback = space.w_None
        if nbargs >= 3: w_traceback = f.popvalue()
        if nbargs >= 2: w_value     = f.popvalue()
        if 1:           w_type      = f.popvalue()
        operror = OperationError(w_type, w_value)
        operror.normalize_exception(space)
        if not space.full_exceptions or space.is_w(w_traceback, space.w_None):
            # common case
            raise operror
        else:
            from pypy.interpreter.pytraceback import check_traceback
            msg = "raise: arg 3 must be a traceback or None"
            tb = check_traceback(space, w_traceback, msg)
            operror.application_traceback = tb
            # special 3-arguments raise, no new traceback obj will be attached
            raise RaiseWithExplicitTraceback(operror)

    def LOAD_LOCALS(f, *ignored):
        f.pushvalue(f.w_locals)

    def EXEC_STMT(f, *ignored):
        w_locals  = f.popvalue()
        w_globals = f.popvalue()
        w_prog    = f.popvalue()
        flags = f.space.getexecutioncontext().compiler.getcodeflags(f.pycode)
        w_compile_flags = f.space.wrap(flags)
        w_resulttuple = prepare_exec(f.space, f.space.wrap(f), w_prog,
                                     w_globals, w_locals,
                                     w_compile_flags,
                                     f.space.wrap(f.get_builtin()),
                                     f.space.gettypeobject(PyCode.typedef))
        w_prog, w_globals, w_locals = f.space.fixedview(w_resulttuple, 3)

        plain = f.w_locals is not None and f.space.is_w(w_locals, f.w_locals)
        if plain:
            w_locals = f.getdictscope()
        co = f.space.interp_w(eval.Code, w_prog)
        co.exec_code(f.space, w_globals, w_locals)
        if plain:
            f.setdictscope(w_locals)

    def POP_BLOCK(f, *ignored):
        block = f.pop_block()
        block.cleanup(f)  # the block knows how to clean up the value stack

    def end_finally(f):
        # unlike CPython, when we reach this opcode the value stack has
        # always been set up as follows (topmost first):
        #   [exception type  or None]
        #   [exception value or None]
        #   [wrapped stack unroller ]
        f.popvalue()   # ignore the exception type
        f.popvalue()   # ignore the exception value
        w_unroller = f.popvalue()
        unroller = f.space.interpclass_w(w_unroller)
        return unroller

    def BUILD_CLASS(f, *ignored):
        w_methodsdict = f.popvalue()
        w_bases       = f.popvalue()
        w_name        = f.popvalue()
        w_metaclass = find_metaclass(f.space, w_bases,
                                     w_methodsdict, f.w_globals,
                                     f.space.wrap(f.get_builtin())) 
        w_newclass = f.space.call_function(w_metaclass, w_name,
                                           w_bases, w_methodsdict)
        f.pushvalue(w_newclass)

    def STORE_NAME(f, varindex, *ignored):
        varname = f.getname_u(varindex)
        w_newvalue = f.popvalue()
        f.space.set_str_keyed_item(f.w_locals, varname, w_newvalue)

    def DELETE_NAME(f, varindex, *ignored):
        w_varname = f.getname_w(varindex)
        try:
            f.space.delitem(f.w_locals, w_varname)
        except OperationError, e:
            # catch KeyErrors and turn them into NameErrors
            if not e.match(f.space, f.space.w_KeyError):
                raise
            message = "name '%s' is not defined"
            raise operationerrfmt(f.space.w_NameError, message,
                                  f.space.str_w(w_varname))

    def UNPACK_SEQUENCE(f, itemcount, *ignored):
        w_iterable = f.popvalue()
        try:
            items = f.space.fixedview(w_iterable, itemcount)
        except UnpackValueError, e:
            raise OperationError(f.space.w_ValueError, f.space.wrap(e.msg))
        f.pushrevvalues(itemcount, items)

    def STORE_ATTR(f, nameindex, *ignored):
        "obj.attributename = newvalue"
        w_attributename = f.getname_w(nameindex)
        w_obj = f.popvalue()
        w_newvalue = f.popvalue()
        f.space.setattr(w_obj, w_attributename, w_newvalue)

    def DELETE_ATTR(f, nameindex, *ignored):
        "del obj.attributename"
        w_attributename = f.getname_w(nameindex)
        w_obj = f.popvalue()
        f.space.delattr(w_obj, w_attributename)

    def STORE_GLOBAL(f, nameindex, *ignored):
        varname = f.getname_u(nameindex)
        w_newvalue = f.popvalue()
        f.space.set_str_keyed_item(f.w_globals, varname, w_newvalue)

    def DELETE_GLOBAL(f, nameindex, *ignored):
        w_varname = f.getname_w(nameindex)
        f.space.delitem(f.w_globals, w_varname)

    def LOAD_NAME(f, nameindex, *ignored):
        if f.w_locals is not f.w_globals:
            w_varname = f.getname_w(nameindex)
            w_value = f.space.finditem(f.w_locals, w_varname)
            if w_value is not None:
                f.pushvalue(w_value)
                return
        f.LOAD_GLOBAL(nameindex)    # fall-back

    def _load_global(f, varname):
        w_value = f.space.finditem_str(f.w_globals, varname)
        if w_value is None:
            # not in the globals, now look in the built-ins
            w_value = f.get_builtin().getdictvalue(f.space, varname)
            if w_value is None:
                f._load_global_failed(varname)
        return w_value
    _load_global._always_inline_ = True

    def _load_global_failed(f, varname):
        message = "global name '%s' is not defined"
        raise operationerrfmt(f.space.w_NameError, message, varname)
    _load_global_failed._dont_inline_ = True

    def LOAD_GLOBAL(f, nameindex, *ignored):
        f.pushvalue(f._load_global(f.getname_u(nameindex)))
    LOAD_GLOBAL._always_inline_ = True

    def DELETE_FAST(f, varindex, *ignored):
        if f.fastlocals_w[varindex] is None:
            varname = f.getlocalvarname(varindex)
            message = "local variable '%s' referenced before assignment"
            raise operationerrfmt(f.space.w_UnboundLocalError, message, varname)
        f.fastlocals_w[varindex] = None
        

    def BUILD_TUPLE(f, itemcount, *ignored):
        items = f.popvalues(itemcount)
        w_tuple = f.space.newtuple(items)
        f.pushvalue(w_tuple)

    def BUILD_LIST(f, itemcount, *ignored):
        items = f.popvalues_mutable(itemcount)
        w_list = f.space.newlist(items)
        f.pushvalue(w_list)

    def BUILD_MAP(f, itemcount, *ignored):
        if not we_are_translated() and sys.version_info >= (2, 6):
            # We could pre-allocate a dict here
            # but for the moment this code is not translated.
            pass
        else:
            if itemcount != 0:
                raise BytecodeCorruption
        w_dict = f.space.newdict()
        f.pushvalue(w_dict)

    def STORE_MAP(f, zero, *ignored):
        if not we_are_translated() and sys.version_info >= (2, 6):
            w_key = f.popvalue()
            w_value = f.popvalue()
            w_dict = f.peekvalue()
            f.space.setitem(w_dict, w_key, w_value)
        else:
            raise BytecodeCorruption

    def LOAD_ATTR(f, nameindex, *ignored):
        "obj.attributename"
        w_attributename = f.getname_w(nameindex)
        w_obj = f.popvalue()
        w_value = f.space.getattr(w_obj, w_attributename)
        f.pushvalue(w_value)
    LOAD_ATTR._always_inline_ = True

    def cmp_lt(f, w_1, w_2):  return f.space.lt(w_1, w_2)
    def cmp_le(f, w_1, w_2):  return f.space.le(w_1, w_2)
    def cmp_eq(f, w_1, w_2):  return f.space.eq(w_1, w_2)
    def cmp_ne(f, w_1, w_2):  return f.space.ne(w_1, w_2)
    def cmp_gt(f, w_1, w_2):  return f.space.gt(w_1, w_2)
    def cmp_ge(f, w_1, w_2):  return f.space.ge(w_1, w_2)

    def cmp_in(f, w_1, w_2):
        return f.space.contains(w_2, w_1)
    def cmp_not_in(f, w_1, w_2):
        return f.space.not_(f.space.contains(w_2, w_1))
    def cmp_is(f, w_1, w_2):
        return f.space.is_(w_1, w_2)
    def cmp_is_not(f, w_1, w_2):
        return f.space.not_(f.space.is_(w_1, w_2))
    def cmp_exc_match(f, w_1, w_2):
        return f.space.newbool(f.space.exception_match(w_1, w_2))

    def COMPARE_OP(f, testnum, *ignored):
        w_2 = f.popvalue()
        w_1 = f.popvalue()
        w_result = None
        for i, attr in unrolling_compare_dispatch_table:
            if i == testnum:
                w_result = getattr(f, attr)(w_1, w_2)
                break
        else:
            raise BytecodeCorruption, "bad COMPARE_OP oparg"
        f.pushvalue(w_result)

    def IMPORT_NAME(f, nameindex, *ignored):
        space = f.space
        w_modulename = f.getname_w(nameindex)
        modulename = f.space.str_w(w_modulename)
        w_fromlist = f.popvalue()

        # CPython 2.5 adds an extra argument consumed by this opcode
        if f.pycode.magic >= 0xa0df294:
            w_flag = f.popvalue()
        else:
            w_flag = None

        w_import = f.get_builtin().getdictvalue(f.space, '__import__')
        if w_import is None:
            raise OperationError(space.w_ImportError,
                                 space.wrap("__import__ not found"))
        w_locals = f.w_locals
        if w_locals is None:            # CPython does this
            w_locals = space.w_None
        w_modulename = space.wrap(modulename)
        w_globals = f.w_globals
        if w_flag is None:
            w_obj = space.call_function(w_import, w_modulename, w_globals,
                                        w_locals, w_fromlist)
        else:
            w_obj = space.call_function(w_import, w_modulename, w_globals,
                                        w_locals, w_fromlist, w_flag)

        f.pushvalue(w_obj)

    def IMPORT_STAR(f, *ignored):
        w_module = f.popvalue()
        w_locals = f.getdictscope()
        import_all_from(f.space, w_module, w_locals)
        f.setdictscope(w_locals)

    def IMPORT_FROM(f, nameindex, *ignored):
        w_name = f.getname_w(nameindex)
        w_module = f.peekvalue()
        try:
            w_obj = f.space.getattr(w_module, w_name)
        except OperationError, e:
            if not e.match(f.space, f.space.w_AttributeError):
                raise
            raise operationerrfmt(f.space.w_ImportError,
                                  "cannot import name '%s'",
                                  f.space.str_w(w_name))
        f.pushvalue(w_obj)

    def JUMP_FORWARD(f, jumpby, next_instr, *ignored):
        next_instr += jumpby
        return next_instr

    def JUMP_IF_FALSE(f, stepby, next_instr, *ignored):
        w_cond = f.peekvalue()
        if not f.space.is_true(w_cond):
            next_instr += stepby
        return next_instr

    def JUMP_IF_TRUE(f, stepby, next_instr, *ignored):
        w_cond = f.peekvalue()
        if f.space.is_true(w_cond):
            next_instr += stepby
        return next_instr

    def JUMP_ABSOLUTE(f, jumpto, next_instr, *ignored):
        return jumpto

    def GET_ITER(f, *ignored):
        w_iterable = f.popvalue()
        w_iterator = f.space.iter(w_iterable)
        f.pushvalue(w_iterator)

    def FOR_ITER(f, jumpby, next_instr, *ignored):
        w_iterator = f.peekvalue()
        try:
            w_nextitem = f.space.next(w_iterator)
        except OperationError, e:
            if not e.match(f.space, f.space.w_StopIteration):
                raise 
            # iterator exhausted
            f.popvalue()
            next_instr += jumpby
        else:
            f.pushvalue(w_nextitem)
        return next_instr

    def FOR_LOOP(f, oparg, *ignored):
        raise BytecodeCorruption, "old opcode, no longer in use"

    def SETUP_LOOP(f, offsettoend, next_instr, *ignored):
        block = LoopBlock(f, next_instr + offsettoend)
        f.append_block(block)

    def SETUP_EXCEPT(f, offsettoend, next_instr, *ignored):
        block = ExceptBlock(f, next_instr + offsettoend)
        f.append_block(block)

    def SETUP_FINALLY(f, offsettoend, next_instr, *ignored):
        block = FinallyBlock(f, next_instr + offsettoend)
        f.append_block(block)

    def WITH_CLEANUP(f, *ignored):
        # see comment in END_FINALLY for stack state
        w_exitfunc = f.popvalue()
        w_unroller = f.peekvalue(2)
        unroller = f.space.interpclass_w(w_unroller)
        if isinstance(unroller, SApplicationException):
            operr = unroller.operr
            w_result = f.space.call_function(w_exitfunc,
                                             operr.w_type,
                                             operr.get_w_value(f.space),
                                             operr.application_traceback)
            if f.space.is_true(w_result):
                # __exit__() returned True -> Swallow the exception.
                f.settopvalue(f.space.w_None, 2)
        else:
            f.space.call_function(w_exitfunc,
                                  f.space.w_None,
                                  f.space.w_None,
                                  f.space.w_None)
                      
    @jit.unroll_safe
    def call_function(f, oparg, w_star=None, w_starstar=None):
        from pypy.rlib import rstack # for resume points
        from pypy.interpreter.function import is_builtin_code
    
        n_arguments = oparg & 0xff
        n_keywords = (oparg>>8) & 0xff
        if n_keywords:
            keywords = [None] * n_keywords
            keywords_w = [None] * n_keywords
            while True:
                n_keywords -= 1
                if n_keywords < 0:
                    break
                w_value = f.popvalue()
                w_key   = f.popvalue()
                key = f.space.str_w(w_key)
                keywords[n_keywords] = key
                keywords_w[n_keywords] = w_value
        else:
            keywords = None
            keywords_w = None
        arguments = f.popvalues(n_arguments)
        args = f.argument_factory(arguments, keywords, keywords_w, w_star, w_starstar)
        w_function  = f.popvalue()
        if f.is_being_profiled and is_builtin_code(w_function):
            w_result = f.space.call_args_and_c_profile(f, w_function, args)
        else:
            w_result = f.space.call_args(w_function, args)
        rstack.resume_point("call_function", f, returns=w_result)
        f.pushvalue(w_result)
        
    def CALL_FUNCTION(f, oparg, *ignored):
        from pypy.rlib import rstack # for resume points

        # XXX start of hack for performance
        if (oparg >> 8) & 0xff == 0:
            # Only positional arguments
            nargs = oparg & 0xff
            w_function = f.peekvalue(nargs)
            try:
                w_result = f.space.call_valuestack(w_function, nargs, f)
                rstack.resume_point("CALL_FUNCTION", f, nargs, returns=w_result)
            finally:
                f.dropvalues(nargs + 1)
            f.pushvalue(w_result)
        # XXX end of hack for performance
        else:
            # general case
            f.call_function(oparg)

    def CALL_FUNCTION_VAR(f, oparg, *ignored):
        w_varargs = f.popvalue()
        f.call_function(oparg, w_varargs)

    def CALL_FUNCTION_KW(f, oparg, *ignored):
        w_varkw = f.popvalue()
        f.call_function(oparg, None, w_varkw)

    def CALL_FUNCTION_VAR_KW(f, oparg, *ignored):
        w_varkw = f.popvalue()
        w_varargs = f.popvalue()
        f.call_function(oparg, w_varargs, w_varkw)

    def MAKE_FUNCTION(f, numdefaults, *ignored):
        w_codeobj = f.popvalue()
        codeobj = f.space.interp_w(PyCode, w_codeobj)
        defaultarguments = f.popvalues(numdefaults)
        fn = function.Function(f.space, codeobj, f.w_globals, defaultarguments)
        f.pushvalue(f.space.wrap(fn))

    def BUILD_SLICE(f, numargs, *ignored):
        if numargs == 3:
            w_step = f.popvalue()
        elif numargs == 2:
            w_step = f.space.w_None
        else:
            raise BytecodeCorruption
        w_end   = f.popvalue()
        w_start = f.popvalue()
        w_slice = f.space.newslice(w_start, w_end, w_step)
        f.pushvalue(w_slice)

    def LIST_APPEND(f, *ignored):
        w = f.popvalue()
        v = f.popvalue()
        f.space.call_method(v, 'append', w)

    def SET_LINENO(f, lineno, *ignored):
        pass

    def CALL_LIKELY_BUILTIN(f, oparg, *ignored):
        # overridden by faster version in the standard object space.
        from pypy.module.__builtin__ import OPTIMIZED_BUILTINS
        varname = OPTIMIZED_BUILTINS[oparg >> 8]
        w_function = f._load_global(varname)
        nargs = oparg&0xFF
        try:
            w_result = f.space.call_valuestack(w_function, nargs, f)
        finally:
            f.dropvalues(nargs)
        f.pushvalue(w_result)

    def LOOKUP_METHOD(f, nameindex, *ignored):
        # overridden by faster version in the standard object space.
        space = f.space
        w_obj = f.popvalue()
        w_name = f.getname_w(nameindex)
        w_value = space.getattr(w_obj, w_name)
        f.pushvalue(w_value)
        #f.pushvalue(None)

    def CALL_METHOD(f, nargs, *ignored):
        # overridden by faster version in the standard object space.
        # 'nargs' is the argument count excluding the implicit 'self'
        w_callable = f.peekvalue(nargs)
        try:
            w_result = f.space.call_valuestack(w_callable, nargs, f)
        finally:
            f.dropvalues(nargs + 1)
        f.pushvalue(w_result)

##     def EXTENDED_ARG(f, oparg, *ignored):
##         opcode = f.nextop()
##         oparg = oparg<<16 | f.nextarg()
##         fn = f.dispatch_table_w_arg[opcode]
##         if fn is None:
##             raise BytecodeCorruption
##         fn(f, oparg)

    def MISSING_OPCODE(f, oparg, next_instr, *ignored):
        ofs = next_instr - 1
        c = f.pycode.co_code[ofs]
        name = f.pycode.co_name
        raise BytecodeCorruption("unknown opcode, ofs=%d, code=%d, name=%s" %
                                 (ofs, ord(c), name) )

    STOP_CODE = MISSING_OPCODE


### ____________________________________________________________ ###

class ExitFrame(Exception):
    pass

class Return(ExitFrame):
    """Raised when exiting a frame via a 'return' statement."""
class Yield(ExitFrame):
    """Raised when exiting a frame via a 'yield' statement."""

class Reraise(Exception):
    """Raised at interp-level by a bare 'raise' statement."""
class RaiseWithExplicitTraceback(Exception):
    """Raised at interp-level by a 3-arguments 'raise' statement."""
    def __init__(self, operr):
        self.operr = operr

class BytecodeCorruption(Exception):
    """Detected bytecode corruption.  Never caught; it's an error."""


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
    def nomoreblocks(self):
        raise BytecodeCorruption("misplaced bytecode - should not return")

    # NB. for the flow object space, the state_(un)pack_variables methods
    # give a way to "pickle" and "unpickle" the SuspendedUnroller by
    # enumerating the Variables it contains.

class SReturnValue(SuspendedUnroller):
    """Signals a 'return' statement.
    Argument is the wrapped object to return."""
    kind = 0x01
    def __init__(self, w_returnvalue):
        self.w_returnvalue = w_returnvalue
    def nomoreblocks(self):
        return self.w_returnvalue

    def state_unpack_variables(self, space):
        return [self.w_returnvalue]
    def state_pack_variables(space, w_returnvalue):
        return SReturnValue(w_returnvalue)
    state_pack_variables = staticmethod(state_pack_variables)

class SApplicationException(SuspendedUnroller):
    """Signals an application-level exception
    (i.e. an OperationException)."""
    kind = 0x02
    def __init__(self, operr):
        self.operr = operr
    def nomoreblocks(self):
        raise RaiseWithExplicitTraceback(self.operr)

    def state_unpack_variables(self, space):
        return [self.operr.w_type, self.operr.get_w_value(space)]
    def state_pack_variables(space, w_type, w_value):
        return SApplicationException(OperationError(w_type, w_value))
    state_pack_variables = staticmethod(state_pack_variables)

class SBreakLoop(SuspendedUnroller):
    """Signals a 'break' statement."""
    kind = 0x04

    def state_unpack_variables(self, space):
        return []
    def state_pack_variables(space):
        return SBreakLoop.singleton
    state_pack_variables = staticmethod(state_pack_variables)

SBreakLoop.singleton = SBreakLoop()

class SContinueLoop(SuspendedUnroller):
    """Signals a 'continue' statement.
    Argument is the bytecode position of the beginning of the loop."""
    kind = 0x08
    def __init__(self, jump_to):
        self.jump_to = jump_to

    def state_unpack_variables(self, space):
        return [space.wrap(self.jump_to)]
    def state_pack_variables(space, w_jump_to):
        return SContinueLoop(space.int_w(w_jump_to))
    state_pack_variables = staticmethod(state_pack_variables)


class FrameBlock:

    """Abstract base class for frame blocks from the blockstack,
    used by the SETUP_XXX and POP_BLOCK opcodes."""

    def __init__(self, frame, handlerposition):
        self.handlerposition = handlerposition
        self.valuestackdepth = frame.valuestackdepth
        self.previous = None # this makes a linked list of blocks

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
        next_instr = self.really_handle(frame, unroller)   # JIT hack
        return next_instr

    def really_handle(self, frame, unroller):
        """ Purely abstract method
        """
        raise NotImplementedError

class LoopBlock(FrameBlock):
    """A loop block.  Stores the end-of-loop pointer in case of 'break'."""

    _opname = 'SETUP_LOOP'
    handling_mask = SBreakLoop.kind | SContinueLoop.kind

    def really_handle(self, frame, unroller):
        if isinstance(unroller, SContinueLoop):
            # re-push the loop block without cleaning up the value stack,
            # and jump to the beginning of the loop, stored in the
            # exception's argument
            frame.append_block(self)
            return unroller.jump_to
        else:
            # jump to the end of the loop
            self.cleanupstack(frame)
            return self.handlerposition


class ExceptBlock(FrameBlock):
    """An try:except: block.  Stores the position of the exception handler."""

    _opname = 'SETUP_EXCEPT'
    handling_mask = SApplicationException.kind

    def really_handle(self, frame, unroller):
        # push the exception to the value stack for inspection by the
        # exception handler (the code after the except:)
        self.cleanupstack(frame)
        assert isinstance(unroller, SApplicationException)
        operationerr = unroller.operr
        if frame.space.full_exceptions:
            operationerr.normalize_exception(frame.space)
        # the stack setup is slightly different than in CPython:
        # instead of the traceback, we store the unroller object,
        # wrapped.
        frame.pushvalue(frame.space.wrap(unroller))
        frame.pushvalue(operationerr.get_w_value(frame.space))
        frame.pushvalue(operationerr.w_type)
        frame.last_exception = operationerr
        return self.handlerposition   # jump to the handler


class FinallyBlock(FrameBlock):
    """A try:finally: block.  Stores the position of the exception handler."""

    _opname = 'SETUP_FINALLY'
    handling_mask = -1     # handles every kind of SuspendedUnroller

    def cleanup(self, frame):
        # upon normal entry into the finally: part, the standard Python
        # bytecode pushes a single None for END_FINALLY.  In our case we
        # always push three values into the stack: the wrapped ctlflowexc,
        # the exception value and the exception type (which are all None
        # here).
        self.cleanupstack(frame)
        # one None already pushed by the bytecode
        frame.pushvalue(frame.space.w_None)
        frame.pushvalue(frame.space.w_None)

    def really_handle(self, frame, unroller):
        # any abnormal reason for unrolling a finally: triggers the end of
        # the block unrolling and the entering the finally: handler.
        # see comments in cleanup().
        self.cleanupstack(frame)
        frame.pushvalue(frame.space.wrap(unroller))
        frame.pushvalue(frame.space.w_None)
        frame.pushvalue(frame.space.w_None)
        return self.handlerposition   # jump to the handler


block_classes = {'SETUP_LOOP': LoopBlock,
                 'SETUP_EXCEPT': ExceptBlock,
                 'SETUP_FINALLY': FinallyBlock}

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
        stream.write(str(x))

        # add a softspace unless we just printed a string which ends in a '\t'
        # or '\n' -- or more generally any whitespace character but ' '
        if isinstance(x, str) and x and x[-1].isspace() and x[-1]!=' ':
            return 
        # XXX add unicode handling
        file_softspace(stream, True)
    print_item_to._annspecialcase_ = "specialize:argtype(0)"

    def print_item(x):
        print_item_to(x, sys_stdout())
    print_item._annspecialcase_ = "flowspace:print_item"

    def print_newline_to(stream):
        stream.write("\n")
        file_softspace(stream, False)

    def print_newline():
        print_newline_to(sys_stdout())
    print_newline._annspecialcase_ = "flowspace:print_newline"

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
        try:
            globals['__builtins__']
        except KeyError:
            globals['__builtins__'] = builtin
        if not isinstance(locals, dict):
            if not hasattr(locals, '__getitem__'):
                raise TypeError("exec: arg 3 must be a dictionary or None")

        if not isinstance(prog, codetype):
            filename = '<string>'
            if not isinstance(prog, str):
                if isinstance(prog, basestring):
                    prog = str(prog)
                elif isinstance(prog, file):
                    filename = prog.name
                    prog = prog.read()
                else:
                    raise TypeError("exec: arg 1 must be a string, file, "
                                    "or code object")
            prog = compile(prog, filename, 'exec', compile_flags, 1)
        return (prog, globals, locals)
''', filename=__file__)

prepare_exec    = app.interphook('prepare_exec')
