from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.codewriter import longlong
from rpython.jit.metainterp import compile
from rpython.jit.metainterp.history import (Const, ConstInt, BoxInt, BoxFloat,
    BoxPtr, make_hashable_int, ConstFloat)
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.optimizeopt.intutils import IntBound
from rpython.jit.metainterp.optimizeopt.optimizer import (Optimization, REMOVED,
    CONST_0, CONST_1, PtrOptValue)
from rpython.jit.metainterp.optimizeopt.util import _findall, make_dispatcher_method
from rpython.jit.metainterp.resoperation import rop, ResOperation, opclasses
from rpython.rlib.rarithmetic import highest_bit
import math

class OptRewrite(Optimization):
    """Rewrite operations into equivalent, cheaper operations.
       This includes already executed operations and constants.
    """
    def __init__(self):
        self.loop_invariant_results = {}
        self.loop_invariant_producer = {}

    def produce_potential_short_preamble_ops(self, sb):
        for op in self.loop_invariant_producer.values():
            sb.add_potential(op)

    def propagate_forward(self, op):
        if op.boolinverse != -1 or op.boolreflex != -1:
            args = self.optimizer.make_args_key(op)
            if self.find_rewritable_bool(op, args):
                return

        dispatch_opt(self, op)

    def try_boolinvers(self, op, targs):
        value = self.get_pure_result(targs)
        if value is not None:
            if value.is_constant():
                if value.box.same_constant(CONST_1):
                    self.make_constant(op.result, CONST_0)
                    return True
                elif value.box.same_constant(CONST_0):
                    self.make_constant(op.result, CONST_1)
                    return True

        return False


    def find_rewritable_bool(self, op, args):
        oldopnum = op.boolinverse
        if oldopnum != -1:
            targs = self.optimizer.make_args_key(ResOperation(oldopnum, [args[0], args[1]],
                                                              None))
            if self.try_boolinvers(op, targs):
                return True

        oldopnum = op.boolreflex # FIXME: add INT_ADD, INT_MUL
        if oldopnum != -1:
            targs = self.optimizer.make_args_key(ResOperation(oldopnum, [args[1], args[0]],
                                                              None))
            value = self.get_pure_result(targs)
            if value is not None:
                self.optimizer.make_equal_to(op.result, value, True)
                return True

        if op.boolreflex == -1:
            return False
        oldopnum = opclasses[op.boolreflex].boolinverse
        if oldopnum != -1:
            targs = self.optimizer.make_args_key(
                ResOperation(oldopnum, [args[1], args[0]], None))
            if self.try_boolinvers(op, targs):
                return True

        return False

    def optimize_INT_AND(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.is_null() or v2.is_null():
            self.make_constant_int(op.result, 0)
            return
        elif v2.is_constant():
            val = v2.box.getint()
            if val == -1 or v1.getintbound().lower >= 0 \
                and v1.getintbound().upper <= val & ~(val + 1):
                self.make_equal_to(op.result, v1)
                return
        elif v1.is_constant():
            val = v1.box.getint()
            if val == -1 or v2.getintbound().lower >= 0 \
                and v2.getintbound().upper <= val & ~(val + 1):
                self.make_equal_to(op.result, v2)
                return

        self.emit_operation(op)

    def optimize_INT_OR(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.is_null():
            self.make_equal_to(op.result, v2)
        elif v2.is_null():
            self.make_equal_to(op.result, v1)
        else:
            self.emit_operation(op)

    def optimize_INT_SUB(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v2.is_constant() and v2.box.getint() == 0:
            self.make_equal_to(op.result, v1)
        elif v1.is_constant() and v1.box.getint() == 0:
            op = op.copy_and_change(rop.INT_NEG, args=[v2.box])
            self.emit_operation(op)
        elif v1 is v2:
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)
            self.optimizer.pure_reverse(op)

    def optimize_INT_ADD(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        # If one side of the op is 0 the result is the other side.
        if v1.is_constant() and v1.box.getint() == 0:
            self.make_equal_to(op.result, v2)
        elif v2.is_constant() and v2.box.getint() == 0:
            self.make_equal_to(op.result, v1)
        else:
            self.emit_operation(op)
            self.optimizer.pure_reverse(op)

    def optimize_INT_MUL(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        # If one side of the op is 1 the result is the other side.
        if v1.is_constant() and v1.box.getint() == 1:
            self.make_equal_to(op.result, v2)
        elif v2.is_constant() and v2.box.getint() == 1:
            self.make_equal_to(op.result, v1)
        elif (v1.is_constant() and v1.box.getint() == 0) or \
             (v2.is_constant() and v2.box.getint() == 0):
            self.make_constant_int(op.result, 0)
        else:
            for lhs, rhs in [(v1, v2), (v2, v1)]:
                if lhs.is_constant():
                    x = lhs.box.getint()
                    # x & (x - 1) == 0 is a quick test for power of 2
                    if x & (x - 1) == 0:
                        new_rhs = ConstInt(highest_bit(lhs.box.getint()))
                        op = op.copy_and_change(rop.INT_LSHIFT, args=[rhs.box, new_rhs])
                        break
            self.emit_operation(op)

    def optimize_UINT_FLOORDIV(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        if v2.is_constant() and v2.box.getint() == 1:
            self.make_equal_to(op.result, v1)
        else:
            self.emit_operation(op)

    def optimize_INT_LSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        if v2.is_constant() and v2.box.getint() == 0:
            self.make_equal_to(op.result, v1)
        elif v1.is_constant() and v1.box.getint() == 0:
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_RSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        if v2.is_constant() and v2.box.getint() == 0:
            self.make_equal_to(op.result, v1)
        elif v1.is_constant() and v1.box.getint() == 0:
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_XOR(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        if v1.is_constant() and v1.box.getint() == 0:
            self.make_equal_to(op.result, v2)
        elif v2.is_constant() and v2.box.getint() == 0:
            self.make_equal_to(op.result, v1)
        else:
            self.emit_operation(op)

    def optimize_FLOAT_MUL(self, op):
        arg1 = op.getarg(0)
        arg2 = op.getarg(1)

        # Constant fold f0 * 1.0 and turn f0 * -1.0 into a FLOAT_NEG, these
        # work in all cases, including NaN and inf
        for lhs, rhs in [(arg1, arg2), (arg2, arg1)]:
            v1 = self.getvalue(lhs)
            v2 = self.getvalue(rhs)

            if v1.is_constant():
                if v1.box.getfloat() == 1.0:
                    self.make_equal_to(op.result, v2)
                    return
                elif v1.box.getfloat() == -1.0:
                    self.emit_operation(ResOperation(
                        rop.FLOAT_NEG, [rhs], op.result
                    ))
                    return
        self.emit_operation(op)
        self.optimizer.pure_reverse(op)

    def optimize_FLOAT_TRUEDIV(self, op):
        arg1 = op.getarg(0)
        arg2 = op.getarg(1)
        v2 = self.getvalue(arg2)

        # replace "x / const" by "x * (1/const)" if possible
        if v2.is_constant():
            divisor = v2.box.getfloat()
            fraction = math.frexp(divisor)[0]
            # This optimization is valid for powers of two
            # but not for zeroes, some denormals and NaN:
            if fraction == 0.5 or fraction == -0.5:
                reciprocal = 1.0 / divisor
                rfraction = math.frexp(reciprocal)[0]
                if rfraction == 0.5 or rfraction == -0.5:
                    c = ConstFloat(longlong.getfloatstorage(reciprocal))
                    op = op.copy_and_change(rop.FLOAT_MUL, args=[arg1, c])
        self.emit_operation(op)

    def optimize_FLOAT_NEG(self, op):
        self.emit_operation(op)
        self.optimizer.pure_reverse(op)

    def optimize_guard(self, op, constbox, emit_operation=True):
        value = self.getvalue(op.getarg(0))
        if value.is_constant():
            box = value.box
            assert isinstance(box, Const)
            if not box.same_constant(constbox):
                r = self.optimizer.metainterp_sd.logger_ops.repr_of_resop(op)
                raise InvalidLoop('A GUARD_{VALUE,TRUE,FALSE} (%s) was proven '
                                  'to always fail' % r)
            return
        if emit_operation:
            self.emit_operation(op)
        value.make_constant(constbox)
        if self.optimizer.optheap:
            self.optimizer.optheap.value_updated(value, self.getvalue(constbox))

    def optimize_GUARD_ISNULL(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_null():
            return
        elif value.is_nonnull():
            r = self.optimizer.metainterp_sd.logger_ops.repr_of_resop(op)
            raise InvalidLoop('A GUARD_ISNULL (%s) was proven to always fail'
                              % r)
        self.emit_operation(op)
        value.make_constant(self.optimizer.cpu.ts.CONST_NULL)

    def optimize_GUARD_NONNULL(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_nonnull():
            return
        elif value.is_null():
            r = self.optimizer.metainterp_sd.logger_ops.repr_of_resop(op)
            raise InvalidLoop('A GUARD_NONNULL (%s) was proven to always fail'
                              % r)
        self.emit_operation(op)
        value.make_nonnull(self.optimizer)

    def optimize_GUARD_VALUE(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_virtual():
            arg = value.get_constant_class(self.optimizer.cpu)
            if arg:
                addr = arg.getaddr()
                name = self.optimizer.metainterp_sd.get_name_from_address(addr)
            else:
                name = "<unknown>"
            raise InvalidLoop('A promote of a virtual %s (a recently allocated object) never makes sense!' % name)
        old_guard_op = value.get_last_guard(self.optimizer)
        if old_guard_op and not isinstance(old_guard_op.getdescr(),
                                           compile.ResumeAtPositionDescr):
            # there already has been a guard_nonnull or guard_class or
            # guard_nonnull_class on this value, which is rather silly.
            # replace the original guard with a guard_value
            if old_guard_op.getopnum() != rop.GUARD_NONNULL:
                # This is only safe if the class of the guard_value matches the
                # class of the guard_*_class, otherwise the intermediate ops might
                # be executed with wrong classes.
                previous_classbox = value.get_constant_class(self.optimizer.cpu)
                expected_classbox = self.optimizer.cpu.ts.cls_of_box(op.getarg(1))
                assert previous_classbox is not None
                assert expected_classbox is not None
                if not previous_classbox.same_constant(expected_classbox):
                    r = self.optimizer.metainterp_sd.logger_ops.repr_of_resop(op)
                    raise InvalidLoop('A GUARD_VALUE (%s) was proven to always fail' % r)
            descr = compile.ResumeGuardValueDescr()
            op = old_guard_op.copy_and_change(rop.GUARD_VALUE,
                        args = [old_guard_op.getarg(0), op.getarg(1)],
                        descr = descr)
            # Note: we give explicitly a new descr for 'op'; this is why the
            # old descr must not be ResumeAtPositionDescr (checked above).
            # Better-safe-than-sorry but it should never occur: we should
            # not put in short preambles guard_xxx and guard_value
            # on the same box.
            self.optimizer.replace_guard(op, value)
            descr.make_a_counter_per_value(op)
            # to be safe
            if isinstance(value, PtrOptValue):
                value.last_guard_pos = -1
        constbox = op.getarg(1)
        assert isinstance(constbox, Const)
        self.optimize_guard(op, constbox)

    def optimize_GUARD_TRUE(self, op):
        self.optimize_guard(op, CONST_1)

    def optimize_GUARD_FALSE(self, op):
        self.optimize_guard(op, CONST_0)

    def optimize_RECORD_KNOWN_CLASS(self, op):
        value = self.getvalue(op.getarg(0))
        expectedclassbox = op.getarg(1)
        assert isinstance(expectedclassbox, Const)
        realclassbox = value.get_constant_class(self.optimizer.cpu)
        if realclassbox is not None:
            assert realclassbox.same_constant(expectedclassbox)
            return
        value.make_constant_class(None, expectedclassbox)

    def optimize_GUARD_CLASS(self, op):
        value = self.getvalue(op.getarg(0))
        expectedclassbox = op.getarg(1)
        assert isinstance(expectedclassbox, Const)
        realclassbox = value.get_constant_class(self.optimizer.cpu)
        if realclassbox is not None:
            if realclassbox.same_constant(expectedclassbox):
                return
            r = self.optimizer.metainterp_sd.logger_ops.repr_of_resop(op)
            raise InvalidLoop('A GUARD_CLASS (%s) was proven to always fail'
                              % r)
        assert isinstance(value, PtrOptValue)
        old_guard_op = value.get_last_guard(self.optimizer)
        if old_guard_op and not isinstance(old_guard_op.getdescr(),
                                           compile.ResumeAtPositionDescr):
            # there already has been a guard_nonnull or guard_class or
            # guard_nonnull_class on this value.
            if old_guard_op.getopnum() == rop.GUARD_NONNULL:
                # it was a guard_nonnull, which we replace with a
                # guard_nonnull_class.
                descr = compile.ResumeGuardNonnullClassDescr()
                op = old_guard_op.copy_and_change (rop.GUARD_NONNULL_CLASS,
                            args = [old_guard_op.getarg(0), op.getarg(1)],
                            descr=descr)
                # Note: we give explicitly a new descr for 'op'; this is why the
                # old descr must not be ResumeAtPositionDescr (checked above).
                # Better-safe-than-sorry but it should never occur: we should
                # not put in short preambles guard_nonnull and guard_class
                # on the same box.
                self.optimizer.replace_guard(op, value)
                # not emitting the guard, so we have to pass None to
                # make_constant_class, so last_guard_pos is not updated
                self.emit_operation(op)
                value.make_constant_class(None, expectedclassbox)
                return
        self.emit_operation(op)
        value.make_constant_class(self.optimizer, expectedclassbox)

    def optimize_GUARD_NONNULL_CLASS(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_null():
            r = self.optimizer.metainterp_sd.logger_ops.repr_of_resop(op)
            raise InvalidLoop('A GUARD_NONNULL_CLASS (%s) was proven to '
                              'always fail' % r)
        self.optimize_GUARD_CLASS(op)

    def optimize_CALL_LOOPINVARIANT(self, op):
        arg = op.getarg(0)
        # 'arg' must be a Const, because residual_call in codewriter
        # expects a compile-time constant
        assert isinstance(arg, Const)
        key = make_hashable_int(arg.getint())

        resvalue = self.loop_invariant_results.get(key, None)
        if resvalue is not None:
            self.make_equal_to(op.result, resvalue)
            self.last_emitted_operation = REMOVED
            return
        # change the op to be a normal call, from the backend's point of view
        # there is no reason to have a separate operation for this
        self.loop_invariant_producer[key] = op
        op = op.copy_and_change(rop.CALL)
        self.emit_operation(op)
        resvalue = self.getvalue(op.result)
        self.loop_invariant_results[key] = resvalue

    def optimize_COND_CALL(self, op):
        arg = op.getarg(0)
        val = self.getvalue(arg)
        if val.is_constant():
            if val.box.same_constant(CONST_0):
                self.last_emitted_operation = REMOVED
                return
            op = op.copy_and_change(rop.CALL, args=op.getarglist()[1:])
        self.emit_operation(op)

    def _optimize_nullness(self, op, box, expect_nonnull):
        value = self.getvalue(box)
        if value.is_nonnull():
            self.make_constant_int(op.result, expect_nonnull)
        elif value.is_null():
            self.make_constant_int(op.result, not expect_nonnull)
        else:
            self.emit_operation(op)

    def optimize_INT_IS_TRUE(self, op):
        if self.getvalue(op.getarg(0)) in self.optimizer.bool_boxes:
            self.make_equal_to(op.result, self.getvalue(op.getarg(0)))
            return
        self._optimize_nullness(op, op.getarg(0), True)

    def optimize_INT_IS_ZERO(self, op):
        self._optimize_nullness(op, op.getarg(0), False)

    def _optimize_oois_ooisnot(self, op, expect_isnot, instance):
        value0 = self.getvalue(op.getarg(0))
        value1 = self.getvalue(op.getarg(1))
        if value0.is_virtual():
            if value1.is_virtual():
                intres = (value0 is value1) ^ expect_isnot
                self.make_constant_int(op.result, intres)
            else:
                self.make_constant_int(op.result, expect_isnot)
        elif value1.is_virtual():
            self.make_constant_int(op.result, expect_isnot)
        elif value1.is_null():
            self._optimize_nullness(op, op.getarg(0), expect_isnot)
        elif value0.is_null():
            self._optimize_nullness(op, op.getarg(1), expect_isnot)
        elif value0 is value1:
            self.make_constant_int(op.result, not expect_isnot)
        else:
            if instance:
                cls0 = value0.get_constant_class(self.optimizer.cpu)
                if cls0 is not None:
                    cls1 = value1.get_constant_class(self.optimizer.cpu)
                    if cls1 is not None and not cls0.same_constant(cls1):
                        # cannot be the same object, as we know that their
                        # class is different
                        self.make_constant_int(op.result, expect_isnot)
                        return
            self.emit_operation(op)

    def optimize_PTR_EQ(self, op):
        self._optimize_oois_ooisnot(op, False, False)

    def optimize_PTR_NE(self, op):
        self._optimize_oois_ooisnot(op, True, False)

    def optimize_INSTANCE_PTR_EQ(self, op):
        self._optimize_oois_ooisnot(op, False, True)

    def optimize_INSTANCE_PTR_NE(self, op):
        self._optimize_oois_ooisnot(op, True, True)

    def optimize_CALL(self, op):
        # dispatch based on 'oopspecindex' to a method that handles
        # specifically the given oopspec call.  For non-oopspec calls,
        # oopspecindex is just zero.
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex == EffectInfo.OS_ARRAYCOPY:
            if self._optimize_CALL_ARRAYCOPY(op):
                return
        self.emit_operation(op)

    def _optimize_CALL_ARRAYCOPY(self, op):
        length = self.get_constant_box(op.getarg(5))
        if length and length.getint() == 0:
            return True # 0-length arraycopy

        source_value = self.getvalue(op.getarg(1))
        dest_value = self.getvalue(op.getarg(2))
        source_start_box = self.get_constant_box(op.getarg(3))
        dest_start_box = self.get_constant_box(op.getarg(4))
        extrainfo = op.getdescr().get_extra_info()
        if (source_start_box and dest_start_box
            and length and (dest_value.is_virtual() or length.getint() <= 8) and
            (source_value.is_virtual() or length.getint() <= 8) and
            len(extrainfo.write_descrs_arrays) == 1):   # <-sanity check
            from rpython.jit.metainterp.optimizeopt.virtualize import VArrayValue
            source_start = source_start_box.getint()
            dest_start = dest_start_box.getint()
            # XXX fish fish fish
            arraydescr = extrainfo.write_descrs_arrays[0]
            if arraydescr.is_array_of_structs():
                return False       # not supported right now
            for index in range(length.getint()):
                if source_value.is_virtual():
                    assert isinstance(source_value, VArrayValue)
                    val = source_value.getitem(index + source_start)
                else:
                    if arraydescr.is_array_of_pointers():
                        resbox = BoxPtr()
                    elif arraydescr.is_array_of_floats():
                        resbox = BoxFloat()
                    else:
                        resbox = BoxInt()
                    newop = ResOperation(rop.GETARRAYITEM_GC,
                                      [op.getarg(1),
                                       ConstInt(index + source_start)], resbox,
                                       descr=arraydescr)
                    self.optimizer.send_extra_operation(newop)
                    val = self.getvalue(resbox)
                if val is None:
                    continue
                if dest_value.is_virtual():
                    dest_value.setitem(index + dest_start, val)
                else:
                    newop = ResOperation(rop.SETARRAYITEM_GC,
                                         [op.getarg(2),
                                          ConstInt(index + dest_start),
                                          val.get_key_box()], None,
                                         descr=arraydescr)
                    self.emit_operation(newop)
            return True
        return False

    def optimize_CALL_PURE(self, op):
        # this removes a CALL_PURE with all constant arguments.
        # Note that it's also done in pure.py.  For now we need both...
        result = self._can_optimize_call_pure(op)
        if result is not None:
            self.make_constant(op.result, result)
            self.last_emitted_operation = REMOVED
            return
        self.emit_operation(op)

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if self.last_emitted_operation is REMOVED:
            # it was a CALL_PURE or a CALL_LOOPINVARIANT that was killed;
            # so we also kill the following GUARD_NO_EXCEPTION
            return
        self.emit_operation(op)

    def optimize_GUARD_FUTURE_CONDITION(self, op):
        pass # just remove it

    def optimize_INT_FLOORDIV(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        if v2.is_constant() and v2.box.getint() == 1:
            self.make_equal_to(op.result, v1)
            return
        elif v1.is_constant() and v1.box.getint() == 0:
            self.make_constant_int(op.result, 0)
            return
        if v1.getintbound().known_ge(IntBound(0, 0)) and v2.is_constant():
            val = v2.box.getint()
            if val & (val - 1) == 0 and val > 0: # val == 2**shift
                op = op.copy_and_change(rop.INT_RSHIFT,
                                        args = [op.getarg(0), ConstInt(highest_bit(val))])
        self.emit_operation(op)

    def optimize_CAST_PTR_TO_INT(self, op):
        self.optimizer.pure_reverse(op)
        self.emit_operation(op)

    def optimize_CAST_INT_TO_PTR(self, op):
        self.optimizer.pure_reverse(op)
        self.emit_operation(op)

    def optimize_SAME_AS(self, op):
        self.make_equal_to(op.result, self.getvalue(op.getarg(0)))

dispatch_opt = make_dispatcher_method(OptRewrite, 'optimize_',
        default=OptRewrite.emit_operation)
optimize_guards = _findall(OptRewrite, 'optimize_', 'GUARD')
