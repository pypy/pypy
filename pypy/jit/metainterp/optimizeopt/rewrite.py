from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.resoperation import opboolinvers, opboolreflex
from pypy.jit.metainterp.history import ConstInt
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.codewriter.effectinfo import EffectInfo

class OptRewrite(Optimization):
    """Rewrite operations into equivalent, cheaper operations.
       This includes already executed operations and constants.
    """

    def reconstruct_for_next_iteration(self, optimizer, valuemap):
        return self
    
    def propagate_forward(self, op):
        args = self.optimizer.make_args_key(op)
        if self.find_rewritable_bool(op, args):
            return

        opnum = op.getopnum()
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.emit_operation(op)
        
    def try_boolinvers(self, op, targs):
        oldop = self.optimizer.pure_operations.get(targs, None)
        if oldop is not None and oldop.getdescr() is op.getdescr():
            value = self.getvalue(oldop.result)
            if value.is_constant():
                if value.box.same_constant(CONST_1):
                    self.make_constant(op.result, CONST_0)
                    return True
                elif value.box.same_constant(CONST_0):
                    self.make_constant(op.result, CONST_1)
                    return True

        return False


    def find_rewritable_bool(self, op, args):
        try:
            oldopnum = opboolinvers[op.getopnum()]
            targs = [args[0], args[1], ConstInt(oldopnum)]
            if self.try_boolinvers(op, targs):
                return True
        except KeyError:
            pass

        try:
            oldopnum = opboolreflex[op.getopnum()] # FIXME: add INT_ADD, INT_MUL
            targs = [args[1], args[0], ConstInt(oldopnum)]
            oldop = self.optimizer.pure_operations.get(targs, None)
            if oldop is not None and oldop.getdescr() is op.getdescr():
                self.make_equal_to(op.result, self.getvalue(oldop.result))
                return True
        except KeyError:
            pass

        try:
            oldopnum = opboolinvers[opboolreflex[op.getopnum()]]
            targs = [args[1], args[0], ConstInt(oldopnum)]
            if self.try_boolinvers(op, targs):
                return True
        except KeyError:
            pass

        return False

    def optimize_INT_AND(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.is_null() or v2.is_null():
            self.make_constant_int(op.result, 0)
        else:
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
        else:
            self.emit_operation(op)

        # Synthesize the reverse ops for optimize_default to reuse
        self.pure(rop.INT_ADD, [op.result, op.getarg(1)], op.getarg(0))
        self.pure(rop.INT_SUB, [op.getarg(0), op.result], op.getarg(1))

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

        # Synthesize the reverse op for optimize_default to reuse
        self.pure(rop.INT_SUB, [op.result, op.getarg(1)], op.getarg(0))
        self.pure(rop.INT_SUB, [op.result, op.getarg(0)], op.getarg(1))

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
            self.emit_operation(op)

    def optimize_CALL_PURE(self, op):
        for i in range(op.numargs()):
            arg = op.getarg(i)
            if self.get_constant_box(arg) is None:
                break
        else:
            # all constant arguments: constant-fold away
            self.make_constant(op.result, op.getarg(0))
            return
        # replace CALL_PURE with just CALL
        args = op.getarglist()[1:]
        self.emit_operation(ResOperation(rop.CALL, args, op.result,
                                         op.getdescr()))

    def optimize_guard(self, op, constbox, emit_operation=True):
        value = self.getvalue(op.getarg(0))
        if value.is_constant():
            box = value.box
            assert isinstance(box, Const)
            if not box.same_constant(constbox):
                raise InvalidLoop
            return
        if emit_operation:
            self.emit_operation(op)
        value.make_constant(constbox)
        self.optimizer.turned_constant(value)

    def optimize_GUARD_ISNULL(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_null():
            return
        elif value.is_nonnull():
            raise InvalidLoop
        self.emit_operation(op)
        value.make_constant(self.optimizer.cpu.ts.CONST_NULL)

    def optimize_GUARD_NONNULL(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_nonnull():
            return
        elif value.is_null():
            raise InvalidLoop
        self.emit_operation(op)
        value.make_nonnull(len(self.optimizer.newoperations) - 1)

    def optimize_GUARD_VALUE(self, op):
        value = self.getvalue(op.getarg(0))
        emit_operation = True
        if value.last_guard_index != -1:
            # there already has been a guard_nonnull or guard_class or
            # guard_nonnull_class on this value, which is rather silly.
            # replace the original guard with a guard_value
            old_guard_op = self.optimizer.newoperations[value.last_guard_index]
            new_guard_op = old_guard_op.copy_and_change(rop.GUARD_VALUE,
                                             args = [old_guard_op.getarg(0), op.getarg(1)])
            self.optimizer.newoperations[value.last_guard_index] = new_guard_op
            # hack hack hack.  Change the guard_opnum on
            # new_guard_op.getdescr() so that when resuming,
            # the operation is not skipped by pyjitpl.py.
            descr = new_guard_op.getdescr()
            assert isinstance(descr, compile.ResumeGuardDescr)
            descr.guard_opnum = rop.GUARD_VALUE
            descr.make_a_counter_per_value(new_guard_op)
            emit_operation = False
        constbox = op.getarg(1)
        assert isinstance(constbox, Const)
        self.optimize_guard(op, constbox, emit_operation)

    def optimize_GUARD_TRUE(self, op):
        self.optimize_guard(op, CONST_1)

    def optimize_GUARD_FALSE(self, op):
        self.optimize_guard(op, CONST_0)

    def optimize_GUARD_CLASS(self, op):
        value = self.getvalue(op.getarg(0))
        expectedclassbox = op.getarg(1)
        assert isinstance(expectedclassbox, Const)
        realclassbox = value.get_constant_class(self.optimizer.cpu)
        if realclassbox is not None:
            if realclassbox.same_constant(expectedclassbox):
                return
            raise InvalidLoop
        emit_operation = True
        if value.last_guard_index != -1:
            # there already has been a guard_nonnull or guard_class or
            # guard_nonnull_class on this value.
            old_guard_op = self.optimizer.newoperations[value.last_guard_index]
            if old_guard_op.getopnum() == rop.GUARD_NONNULL:
                # it was a guard_nonnull, which we replace with a
                # guard_nonnull_class.
                new_guard_op = old_guard_op.copy_and_change (rop.GUARD_NONNULL_CLASS,
                                         args = [old_guard_op.getarg(0), op.getarg(1)])
                self.optimizer.newoperations[value.last_guard_index] = new_guard_op
                # hack hack hack.  Change the guard_opnum on
                # new_guard_op.getdescr() so that when resuming,
                # the operation is not skipped by pyjitpl.py.
                descr = new_guard_op.getdescr()
                assert isinstance(descr, compile.ResumeGuardDescr)
                descr.guard_opnum = rop.GUARD_NONNULL_CLASS
                emit_operation = False
        if emit_operation:
            self.emit_operation(op)
            last_guard_index = len(self.optimizer.newoperations) - 1
        else:
            last_guard_index = value.last_guard_index
        value.make_constant_class(expectedclassbox, last_guard_index)

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if not self.optimizer.exception_might_have_happened:
            return
        self.emit_operation(op)
        self.optimizer.exception_might_have_happened = False

    def optimize_CALL_LOOPINVARIANT(self, op):
        arg = op.getarg(0)
        # 'arg' must be a Const, because residual_call in codewriter
        # expects a compile-time constant
        assert isinstance(arg, Const)
        key = make_hashable_int(arg.getint())
        resvalue = self.optimizer.loop_invariant_results.get(key, None)
        if resvalue is not None:
            self.make_equal_to(op.result, resvalue)
            return
        # change the op to be a normal call, from the backend's point of view
        # there is no reason to have a separate operation for this
        op = op.copy_and_change(rop.CALL)
        self.emit_operation(op)
        resvalue = self.getvalue(op.result)
        self.optimizer.loop_invariant_results[key] = resvalue
    
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

    def _optimize_oois_ooisnot(self, op, expect_isnot):
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
            cls0 = value0.get_constant_class(self.optimizer.cpu)
            if cls0 is not None:
                cls1 = value1.get_constant_class(self.optimizer.cpu)
                if cls1 is not None and not cls0.same_constant(cls1):
                    # cannot be the same object, as we know that their
                    # class is different
                    self.make_constant_int(op.result, expect_isnot)
                    return
            self.emit_operation(op)

    def optimize_PTR_NE(self, op):
        self._optimize_oois_ooisnot(op, True)

    def optimize_PTR_EQ(self, op):
        self._optimize_oois_ooisnot(op, False)

##    def optimize_INSTANCEOF(self, op):
##        value = self.getvalue(op.args[0])
##        realclassbox = value.get_constant_class(self.optimizer.cpu)
##        if realclassbox is not None:
##            checkclassbox = self.optimizer.cpu.typedescr2classbox(op.descr)
##            result = self.optimizer.cpu.ts.subclassOf(self.optimizer.cpu,
##                                                      realclassbox, 
##                                                      checkclassbox)
##            self.make_constant_int(op.result, result)
##            return
##        self.emit_operation(op)

    def optimize_CALL(self, op):
        # dispatch based on 'oopspecindex' to a method that handles
        # specifically the given oopspec call.  For non-oopspec calls,
        # oopspecindex is just zero.
        effectinfo = op.getdescr().get_extra_info()
        if effectinfo is not None:
            oopspecindex = effectinfo.oopspecindex
            if oopspecindex == EffectInfo.OS_ARRAYCOPY:
                if self._optimize_CALL_ARRAYCOPY(op):
                    return
        self.emit_operation(op)

    def _optimize_CALL_ARRAYCOPY(self, op):
        source_value = self.getvalue(op.getarg(1))
        dest_value = self.getvalue(op.getarg(2))
        source_start_box = self.get_constant_box(op.getarg(3))
        dest_start_box = self.get_constant_box(op.getarg(4))
        length = self.get_constant_box(op.getarg(5))
        if (source_value.is_virtual() and source_start_box and dest_start_box
            and length and dest_value.is_virtual()):
            # XXX optimize the case where dest value is not virtual,
            #     but we still can avoid a mess
            source_start = source_start_box.getint()
            dest_start = dest_start_box.getint()
            for index in range(length.getint()):
                val = source_value.getitem(index + source_start)
                dest_value.setitem(index + dest_start, val)
            return True
        if length and length.getint() == 0:
            return True # 0-length arraycopy
        return False

optimize_ops = _findall(OptRewrite, 'optimize_')

