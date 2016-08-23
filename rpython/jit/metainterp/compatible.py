from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.metainterp.history import newconst
from rpython.jit.codewriter import longlong
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.debug import (have_debug_prints, debug_start, debug_stop,
    debug_print)

def do_call(cpu, argboxes, descr):
    from rpython.jit.metainterp.history import INT, REF, FLOAT, VOID
    from rpython.jit.metainterp.blackhole import NULL
    from rpython.jit.metainterp.executor import _separate_call_arguments
    rettype = descr.get_result_type()
    # count the number of arguments of the different types
    args_i, args_r, args_f = _separate_call_arguments(argboxes)
    # get the function address as an integer
    func = argboxes[0].getint()
    # do the call using the correct function from the cpu
    if rettype == INT:
        return newconst(cpu.bh_call_i(func, args_i, args_r, args_f, descr))
    if rettype == REF:
        return newconst(cpu.bh_call_r(func, args_i, args_r, args_f, descr))
    if rettype == FLOAT:
        return newconst(cpu.bh_call_f(func, args_i, args_r, args_f, descr))
    if rettype == VOID:
        # don't even need to call the void function, result will always match
        return None
    raise AssertionError("bad rettype")


class CompatibilityCondition(object):
    """ A collections of conditions that an object needs to fulfil. """
    def __init__(self, ptr):
        self.known_valid = ptr
        self.conditions = []
        self.last_quasi_immut_field_op = None
        # -1 means "stay on the original trace"
        self.jump_target = -1
        self.frozen = False


    def frozen_copy(self):
        res = CompatibilityCondition(self.known_valid)
        res.conditions = self.conditions[:]
        assert self.jump_target == -1
        res.frozen = True
        return res

    def contains_condition(self, cond, res=None):
        for oldcond in self.conditions:
            if oldcond.same_cond(cond, res):
                return True
        return False

    def record_condition(self, cond, res, optimizer):
        if self.contains_condition(cond, res):
            return True
        if self.frozen:
            return False
        cond.activate(res, optimizer)
        if self.conditions and self.conditions[-1].debug_mp_str == cond.debug_mp_str:
            cond.debug_mp_str = ''
        self.conditions.append(cond)
        return True

    def register_quasi_immut_field(self, op):
        self.last_quasi_immut_field_op = op

    def check_compat(self, cpu, ref):
        for i, cond in enumerate(self.conditions):
            res = cond.check_and_return_result_if_different(cpu, ref)
            if res is not None:
                if have_debug_prints():
                    debug_print("incompatible condition", i, ", got", cond._repr_const(res), ":", cond.repr())
                return False
        return True

    def check_compat_and_activate(self, cpu, ref, loop_token):
        if not self.check_compat(cpu, ref):
            return False
        # need to tell all conditions, in case a quasi-immut needs to be
        # registered
        for cond in self.conditions:
            cond.activate_secondary(ref, loop_token)
        return True

    def prepare_const_arg_call(self, op, optimizer):
        copied_op, cond = self._prepare_const_arg_call(op, optimizer)
        if copied_op:
            result = optimizer._can_optimize_call_pure(copied_op)
            if result is None:
                # just call it, we can do that with an @elidable_compatible
                # function
                result = do_call(
                        optimizer.cpu, copied_op.getarglist(),
                        copied_op.getdescr())
            return copied_op, cond, result
        else:
            return None, None, None

    def _prepare_const_arg_call(self, op, optimizer):
        from rpython.jit.metainterp.quasiimmut import QuasiImmutDescr
        # replace further arguments by constants, if the optimizer knows them
        # already
        last_nonconst_index = -1
        for i in range(2, op.numargs()):
            arg = op.getarg(i)
            constarg = optimizer.get_constant_box(arg)
            if constarg is not None:
                op.setarg(i, constarg)
            else:
                last_nonconst_index = i
        copied_op = op.copy()
        copied_op.setarg(1, self.known_valid)
        if op.numargs() == 2:
            return copied_op, PureCallCondition(op, optimizer)
        arg2 = copied_op.getarg(2)
        if arg2.is_constant():
            # already a constant, can just use PureCallCondition
            if last_nonconst_index != -1:
                return None, None # a non-constant argument, can't optimize
            return copied_op, PureCallCondition(op, optimizer)
        if last_nonconst_index != 2:
            return None, None

        # really simple-minded pattern matching
        # the order of things is like this:
        # GUARD_COMPATIBLE(x)
        # QUASIIMMUT_FIELD(x)
        # y = GETFIELD_GC(x, f)
        # z = CALL_PURE(x, y, ...)
        # we want to discover this (and so far precisely this) situation and
        # make it possible for the GUARD_COMPATIBLE to still remove the call,
        # even though the second argument is not constant
        if arg2.getopnum() not in (rop.GETFIELD_GC_R, rop.GETFIELD_GC_I, rop.GETFIELD_GC_F):
            return None, None
        if not self.last_quasi_immut_field_op:
            return None, None
        qmutdescr = self.last_quasi_immut_field_op.getdescr()
        assert isinstance(qmutdescr, QuasiImmutDescr)
        fielddescr = qmutdescr.fielddescr # XXX
        same_arg = self.last_quasi_immut_field_op.getarg(0) is arg2.getarg(0)
        if arg2.getdescr() is not fielddescr or not same_arg:
            return None, None
        if not qmutdescr.is_still_valid_for(self.known_valid):
            return None, None
        copied_op.setarg(2, qmutdescr.constantfieldbox)
        return copied_op, QuasiimmutGetfieldAndPureCallCondition(
                op, qmutdescr, optimizer)

    def emit_conditions(self, op, short, optimizer):
        """ re-emit the conditions about variable op into the short preamble
        """
        from rpython.jit.metainterp.resoperation import rop, ResOperation
        localshort = []
        localshort.append(
            ResOperation(rop.GUARD_COMPATIBLE, [
                op, self.known_valid]))
        for cond in self.conditions:
            cond.emit_condition(op, localshort, short, optimizer)
        short.extend(localshort)

    def emit_needed_conditions_if_const_matches(
            self, other, const, op, extra_guards, optimizer, cpu):
        """ go through self.conditions. if the condition is present in other,
        do nothing. If it is not, check whether ref matches the condition. If
        not return False, otherwise emit guards for the condition. Return True
        at the end. """
        from rpython.jit.metainterp.resoperation import rop, ResOperation
        have_guard = False
        local_extra_guards = []
        for cond in self.conditions:
            if other is None or not other.contains_condition(cond):
                if const is None:
                    return False
                ref = const.getref_base()
                if cond.check_and_return_result_if_different(cpu, ref) is None:
                    if not have_guard:
                        # NB: the guard_compatible here needs to use const,
                        # otherwise the optimizer will just complain
                        local_extra_guards.append(ResOperation(
                            rop.GUARD_COMPATIBLE,
                                [op, const]))
                        have_guard = True
                    cond.emit_condition(
                            op, local_extra_guards,
                            extra_guards, optimizer, const)
                else:
                    return False
        extra_guards.extend(local_extra_guards)
        return True

    def attach_to_descr(self, descr, guard_value_op, optimizer):
        from rpython.jit.metainterp.resoperation import AbstractResOp
        assert descr._compatibility_conditions is None
        descr._compatibility_conditions = self
        try:
            descr.failarg_index = guard_value_op.getfailargs().index(
                    guard_value_op.getarg(0))
        except ValueError:
            return # too bad
        arg = guard_value_op.getarg(0)
        if not isinstance(arg, AbstractResOp):
            return
        if arg.getopnum() not in (rop.GETFIELD_GC_R, rop.GETFIELD_GC_I, rop.GETFIELD_GC_F):
            return
        # again, a bit of pattern matching. The trace quite often looks like this:
        # x = getfield(obj, <fielddescr>)
        # guard_compatible(x) [x, obj]

        # if this guard fails, we lose the connection between obj and x, which
        # means that the new bridge will do two things: a guard_compatible on
        # x, then later do the read again and have a guard_compatible on the
        # newly read field. This is bad, because one guard_compatible would be
        # enough. Thus we keep track of this connection, and seed the heapcache
        # when starting to trace the bridge with that info.

        source_op = arg.getarg(0)
        try:
            source_index = guard_value_op.getfailargs().index(source_op)
        except ValueError:
            return
        fielddescr = arg.getdescr()
        # check whether the same getfield would still yield the same result at
        # this point in the trace
        optheap = optimizer.optheap
        structinfo = optheap.getptrinfo(source_op)
        cf = optheap.field_cache(fielddescr)
        field = cf.getfield_from_cache(optheap, structinfo, fielddescr)
        if field is arg:
            # yay! we can pass this info on
            descr.source_failarg_index = source_index
            descr.source_fielddescr = fielddescr

    def repr_of_conditions(self, argrepr="?"):
        return "\n".join([cond.repr(argrepr) for cond in self.conditions])


    def repr_of_conditions_as_jit_debug(self, argrepr="?"):
        conditions = [cond.repr(argrepr) for cond in self.conditions]
        # slow but who cares
        conditions = "\n".join(conditions).split("\n")
        # make fake jit-debug ops to print
        for i in range(len(conditions)):
            conditions[i] = "jit_debug('%s')" % (conditions[i], )
        return conditions


class Condition(object):
    def __init__(self, optimizer):
        self.metainterp_sd = optimizer.metainterp_sd
        # XXX maybe too expensive
        op = optimizer._last_debug_merge_point
        if op:
            jd_sd = self.metainterp_sd.jitdrivers_sd[op.getarg(0).getint()]
            s = jd_sd.warmstate.get_location_str(op.getarglist()[3:])
            s = s.replace(',', '.') # we use comma for argument splitting
        else:
            s = ''
        self.debug_mp_str = s
        self.rpyfunc = None

    def check_and_return_result_if_different(self, cpu, ref):
        """ checks the condition using ref as an argument to the function. if
        the result is different, return the result. otherwise return None. """
        raise NotImplementedError

    def activate(self, ref, optimizer):
        self.res = ref

    def activate_secondary(self, ref, loop_token):
        pass

    def same_cond(self, other, res=None):
        return False

    def repr(self):
        return ""

    def emit_condition(self, op, guards, pre_guards, optimizer, const=None):
        raise NotImplementedError("abstract base class")

    def _repr_const(self, arg):
        from rpython.jit.metainterp.history import ConstInt, ConstFloat, ConstPtr
        from rpython.rtyper.annlowlevel import llstr, hlstr
        from rpython.rtyper.lltypesystem import llmemory, rstr, rffi, lltype

        if isinstance(arg, ConstInt):
            return str(arg.value)
        elif isinstance(arg, ConstPtr):
            if arg.value:
                # through all the layers and back
                if we_are_translated():
                    tid = self.metainterp_sd.cpu.get_actual_typeid(arg.getref_base())
                    sid = self.metainterp_sd.cpu.get_actual_typeid(rffi.cast(llmemory.GCREF, llstr("abc")))
                    if sid == tid:
                        return hlstr(rffi.cast(lltype.Ptr(rstr.STR), arg.getref_base()))
                return "<some const ptr>"
            else:
                return "None"
        elif isinstance(arg, ConstFloat):
            return str(arg.getfloat())
        return "<huh?>"

class PureCallCondition(Condition):
    const_args_start_at = 2

    def __init__(self, op, optimizer):
        from rpython.jit.metainterp.history import Const
        Condition.__init__(self, optimizer)
        args = op.getarglist()[:]
        args[1] = None
        self.args = args
        for index in range(self.const_args_start_at, len(args)):
            arg = args[index]
            assert isinstance(arg, Const)
        self.descr = op.getdescr()
        self.rpyfunc = op.rpyfunc

    def check_and_return_result_if_different(self, cpu, ref):
        calldescr = self.descr
        # change exactly the first argument
        arglist = self.args
        arglist[1] = newconst(ref)
        try:
            res = do_call(cpu, arglist, calldescr)
        except Exception:
            if have_debug_prints():
                debug_start("jit-guard-compatible")
                debug_print("call to elidable_compatible function raised")
                debug_print(self.repr())
                debug_stop("jit-guard-compatible")
            return False
        finally:
            arglist[1] = None
        if not res.same_constant(self.res):
            return res
        return None

    def same_cond(self, other, res=None):
        if type(other) is not PureCallCondition:
            return False
        if len(self.args) != len(other.args):
            return False
        if res is None:
            res = other.res
        if not self.res.same_constant(res):
            return False
        if self.descr is not other.descr:
            return False
        assert self.args[1] is other.args[1] is None
        for i in range(len(self.args)):
            if i == 1:
                continue
            if not self.args[i].same_constant(other.args[i]):
                return False
        return True

    def emit_condition(self, op, short, pre_short, optimizer, const=None):
        from rpython.jit.metainterp.history import INT, REF, FLOAT, VOID
        from rpython.jit.metainterp.resoperation import rop, ResOperation
        # woah, mess
        args = self.args[:]
        args[1] = op
        descr = self.descr
        rettype = descr.get_result_type()
        if rettype == INT:
            call_op = ResOperation(rop.CALL_PURE_I, args, descr)
        elif rettype == FLOAT:
            call_op = ResOperation(rop.CALL_PURE_F, args, descr)
        elif rettype == REF:
            call_op = ResOperation(rop.CALL_PURE_R, args, descr)
        else:
            assert rettype == VOID
            # XXX maybe we should forbid this
            call_op = ResOperation(rop.CALL_PURE_N, args, descr)
            short.append(call_op)
            return
        # add result to call_pure_results
        if const is not None:
            args = args[:]
            args[1] = const
            optimizer.call_pure_results[args] = self.res
        short.append(call_op)
        short.append(ResOperation(rop.GUARD_VALUE, [call_op, self.res]))


    def repr(self, argrepr="?"):
        addr = self.args[0].getaddr()
        funcname = self.metainterp_sd.get_name_from_address(addr)
        if not funcname:
            funcname = hex(self.args[0].getint())
        result = self._repr_const(self.res)
        if len(self.args) == 2:
            extra = ''
        else:
            extra = ', ' + ', '.join([self._repr_const(arg) for arg in self.args[2:]])
        res = "compatible if %s == %s(%s%s)" % (result, funcname, argrepr, extra)
        if self.rpyfunc:
            res = "%s: %s" % (self.rpyfunc, res)
        if self.debug_mp_str:
            res = self.debug_mp_str + "\n" + res
        return res

class UnsupportedInfoInGuardCompatible(Exception):
    pass

class QuasiimmutGetfieldAndPureCallCondition(PureCallCondition):
    const_args_start_at = 3

    def __init__(self, op, qmutdescr, optimizer):
        from rpython.jit.metainterp.optimizeopt import info
        PureCallCondition.__init__(self, op, optimizer)
        self.args[2] = None
        # XXX not 100% sure whether it's save to store the whole descr
        self.qmutdescr = qmutdescr
        self.qmut = qmutdescr.qmut
        self.mutatefielddescr = qmutdescr.mutatefielddescr
        self.fielddescr = qmutdescr.fielddescr
        self.need_nonnull_arg2 = False
        if self.fielddescr.is_pointer_field():
            fieldinfo = optimizer.getptrinfo(op.getarg(2))
            if fieldinfo is not None:
                if type(fieldinfo) is not info.NonNullPtrInfo:
                    # XXX PyPy only needs non-null versions. if another
                    # interpreter needs something more specific we need to
                    # generalize this code
                    raise UnsupportedInfoInGuardCompatible()
                else:
                    self.need_nonnull_arg2 = True

    def activate(self, ref, optimizer):
        # record the quasi-immutable
        optimizer.record_quasi_immutable_dep(self.qmut)
        # XXX can set self.qmut to None here?
        Condition.activate(self, ref, optimizer)

    def activate_secondary(self, ref, loop_token):
        from rpython.jit.metainterp.quasiimmut import get_current_qmut_instance
        # need to register the loop for invalidation as well!
        qmut = get_current_qmut_instance(loop_token.cpu, ref,
                                         self.mutatefielddescr)
        qmut.register_loop_token(loop_token.loop_token_wref)

    def check_and_return_result_if_different(self, cpu, ref):
        from rpython.rlib.debug import debug_print, debug_start, debug_stop
        from rpython.jit.metainterp.quasiimmut import QuasiImmutDescr
        calldescr = self.descr
        # change exactly the first argument
        arglist = self.args
        arglist[1] = newconst(ref)
        arglist[2] = QuasiImmutDescr._get_fieldvalue(self.fielddescr, ref, cpu)
        try:
            res = do_call(cpu, arglist, calldescr)
        except Exception:
            if have_debug_prints():
                debug_start("jit-guard-compatible")
                debug_print("call to elidable_compatible function raised")
                debug_print(self.repr())
                debug_stop("jit-guard-compatible")
            return False
        finally:
            arglist[1] = arglist[2] = None
        if not res.same_constant(self.res):
            return res
        return None

    def same_cond(self, other, res=None):
        if type(other) is not QuasiimmutGetfieldAndPureCallCondition:
            return False
        if len(self.args) != len(other.args):
            return False
        if res is None:
            res = other.res
        if not self.res.same_constant(res):
            return False
        if self.descr is not other.descr:
            return False
        if self.fielddescr is not other.fielddescr:
            return False
        if self.mutatefielddescr is not other.mutatefielddescr:
            return False
        assert self.args[1] is other.args[1] is None
        assert self.args[2] is other.args[2] is None
        for i in range(len(self.args)):
            if i == 1 or i == 2:
                continue
            if not self.args[i].same_constant(other.args[i]):
                return False
        return True

    def emit_condition(self, op, short, pre_short, optimizer, const=None):
        from rpython.jit.metainterp.resoperation import rop, ResOperation
        from rpython.jit.metainterp.quasiimmut import QuasiImmutDescr
        # more mess
        fielddescr = self.fielddescr
        if fielddescr.is_pointer_field():
            getfield_op = ResOperation(
                rop.GETFIELD_GC_R, [op], fielddescr)
            if self.need_nonnull_arg2:
                # XXX atm it's emmitted n times
                getfield_op2 = ResOperation(
                    rop.GETFIELD_GC_R, [op], fielddescr)
                guard_nonnull = ResOperation(rop.GUARD_NONNULL, [getfield_op2])
                pre_short.append(getfield_op2)
                pre_short.append(guard_nonnull)
        elif fielddescr.is_float_field():
            getfield_op = ResOperation(
                rop.GETFIELD_GC_F, [op], fielddescr)
        else:
            getfield_op = ResOperation(
                rop.GETFIELD_GC_I, [op], fielddescr)
        if const is not None:
            ref = const.getref_base()
            qmutdescr = QuasiImmutDescr(
                    optimizer.cpu, ref, self.fielddescr, self.mutatefielddescr)
        else:
            qmutdescr = self.qmutdescr
        short.extend([
            ResOperation(
                rop.QUASIIMMUT_FIELD, [op], qmutdescr),
            ResOperation(
                rop.GUARD_NOT_INVALIDATED, []),
            getfield_op])
        index = len(short)
        PureCallCondition.emit_condition(self, op, short, pre_short, optimizer, const)
        call_op = short[index]
        # puh, not pretty
        args = call_op.getarglist()[:]
        if const is not None:
            args[1] = const
            del optimizer.call_pure_results[args]
        assert call_op.opnum in (
                rop.CALL_PURE_I, rop.CALL_PURE_R,
                rop.CALL_PURE_F, rop.CALL_PURE_N)
        call_op.setarg(2, getfield_op)
        if const is not None:
            ref = const.getref_base()
            args[2] = QuasiImmutDescr._get_fieldvalue(
                self.fielddescr, ref, optimizer.cpu)
            optimizer.call_pure_results[args] = self.res

    def repr(self, argrepr="?"):
        addr = self.args[0].getaddr()
        funcname = self.metainterp_sd.get_name_from_address(addr)
        result = self._repr_const(self.res)
        if len(self.args) == 3:
            extra = ''
        else:
            extra = ', ' + ', '.join([self._repr_const(arg) for arg in self.args[3:]])
        attrname = self.fielddescr.repr_of_descr()
        res = "compatible if %s == %s(%s, %s.%s%s)" % (
                result, funcname, argrepr, argrepr, attrname, extra)
        if self.rpyfunc:
            res = "%s: %s" % (self.rpyfunc, res)
        if self.debug_mp_str:
            res = self.debug_mp_str + "\n" + res
        return res
