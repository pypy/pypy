from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.libffi import Func
from pypy.rlib.debug import debug_start, debug_stop, debug_print
from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.optimizeopt.util import make_dispatcher_method
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization


class FuncInfo(object):

    argtypes = None
    restype = None
    descr = None
    prepare_op = None

    def __init__(self, funcval, cpu, prepare_op):
        self.funcval = funcval
        self.opargs = []
        argtypes, restype = self._get_signature(funcval)
        self.descr = cpu.calldescrof_dynamic(argtypes, restype)
        # ^^^ may be None if unsupported
        self.prepare_op = prepare_op
        self.delayed_ops = []

    def _get_signature(self, funcval):
        """
        given the funcval, return a tuple (argtypes, restype), where the
        actuall types are libffi.types.*

        The implementation is tricky because we have three possible cases:

        - translated: the easiest case, we can just cast back the pointer to
          the original Func instance and read .argtypes and .restype

        - completely untranslated: this is what we get from test_optimizeopt
          tests. funcval contains a FakeLLObject whose _fake_class is Func,
          and we can just get .argtypes and .restype

        - partially translated: this happens when running metainterp tests:
          funcval contains the low-level equivalent of a Func, and thus we
          have to fish inst_argtypes and inst_restype by hand.  Note that
          inst_argtypes is actually a low-level array, but we can use it
          directly since the only thing we do with it is to read its items
        """

        llfunc = funcval.box.getref_base()
        if we_are_translated():
            func = cast_base_ptr_to_instance(Func, llfunc)
            return func.argtypes, func.restype
        elif getattr(llfunc, '_fake_class', None) is Func:
            # untranslated
            return llfunc.argtypes, llfunc.restype
        else:
            # partially translated
            # llfunc contains an opaque pointer to something like the following:
            # <GcStruct pypy.rlib.libffi.Func { super, inst_argtypes, inst_funcptr,
            #                                   inst_funcsym, inst_restype }>
            #
            # Unfortunately, we cannot use the proper lltype.cast_opaque_ptr,
            # because we don't have the exact TYPE to cast to.  Instead, we
            # just fish it manually :-(
            f = llfunc._obj.container
            return f.inst_argtypes, f.inst_restype


class OptFfiCall(Optimization):

    def setup(self):
        self.funcinfo = None
        if self.optimizer.loop is not None:
            self.logops = self.optimizer.loop.logops
        else:
            self.logops = None

    def reconstruct_for_next_iteration(self, optimizer, valuemap):
        return OptFfiCall()
        # FIXME: Should any status be saved for next iteration?

    def begin_optimization(self, funcval, op):
        self.rollback_maybe('begin_optimization', op)
        self.funcinfo = FuncInfo(funcval, self.optimizer.cpu, op)

    def commit_optimization(self):
        self.funcinfo = None

    def rollback_maybe(self, msg, op):
        if self.funcinfo is None:
            return # nothing to rollback
        #
        # we immediately set funcinfo to None to prevent recursion when
        # calling emit_op
        if self.logops is not None:
            debug_print('rollback: ' + msg + ': ', self.logops.repr_of_resop(op))
        funcinfo = self.funcinfo
        self.funcinfo = None
        self.emit_operation(funcinfo.prepare_op)
        for op in funcinfo.opargs:
            self.emit_operation(op)
        for delayed_op in funcinfo.delayed_ops:
            self.emit_operation(delayed_op)

    def emit_operation(self, op):
        # we cannot emit any operation during the optimization
        self.rollback_maybe('invalid op', op)
        Optimization.emit_operation(self, op)

    def optimize_CALL(self, op):
        oopspec = self._get_oopspec(op)
        ops = [op]
        if oopspec == EffectInfo.OS_LIBFFI_PREPARE:
            ops = self.do_prepare_call(op)
        elif oopspec == EffectInfo.OS_LIBFFI_PUSH_ARG:
            ops = self.do_push_arg(op)
        elif oopspec == EffectInfo.OS_LIBFFI_CALL:
            ops = self.do_call(op)
        #
        for op in ops:
            self.emit_operation(op)

    optimize_CALL_MAY_FORCE = optimize_CALL

    def optimize_FORCE_TOKEN(self, op):
        # The handling of force_token needs a bit of exaplanation.
        # The original trace which is getting optimized looks like this:
        #    i1 = force_token()
        #    setfield_gc(p0, i1, ...)
        #    call_may_force(...)
        #
        # In theory, fficall should take care of both force_token and
        # setfield_gc.  However, the lazy setfield optimization in heap.py
        # delays the setfield_gc, with the effect that fficall.py sees them in
        # this order:
        #    i1 = force_token()
        #    call_may_force(...)
        #    setfield_gc(p0, i1, ...)
        #
        # This means that see the setfield_gc only the call_may_force, when
        # the optimization has already been done, and thus we need to take
        # special care just of force_token.
        #
        # Finally, the method force_lazy_setfield in heap.py reorders the
        # call_may_force and the setfield_gc, so the final result we get is
        # again force_token/setfield_gc/call_may_force.
        #
        # However, note that nowadays we also allow to have any setfield_gc
        # between libffi_prepare and libffi_call, so while the comment above
        # it's a bit superfluous, it has been left there for future reference.
        if self.funcinfo is None:
            self.emit_operation(op)
        else:
            self.funcinfo.delayed_ops.append(op)

    optimize_SETFIELD_GC = optimize_FORCE_TOKEN

    def do_prepare_call(self, op):
        self.rollback_maybe('prepare call', op)
        funcval = self._get_funcval(op)
        if not funcval.is_constant():
            return [op] # cannot optimize
        self.begin_optimization(funcval, op)
        return []

    def do_push_arg(self, op):
        funcval = self._get_funcval(op)
        if not self.funcinfo or self.funcinfo.funcval is not funcval:
            return [op] # cannot optimize
        self.funcinfo.opargs.append(op)
        return []

    def do_call(self, op):
        funcval = self._get_funcval(op)
        funcinfo = self.funcinfo
        if (not funcinfo or funcinfo.funcval is not funcval or
            funcinfo.descr is None):
            return [op] # cannot optimize
        funcsymval = self.getvalue(op.getarg(2))
        arglist = [funcsymval.force_box()]
        for push_op in funcinfo.opargs:
            argval = self.getvalue(push_op.getarg(2))
            arglist.append(argval.force_box())
        newop = ResOperation(rop.CALL_RELEASE_GIL, arglist, op.result,
                             descr=funcinfo.descr)
        self.commit_optimization()
        ops = []
        for delayed_op in funcinfo.delayed_ops:
            ops.append(delayed_op)
        ops.append(newop)
        return ops

    def propagate_forward(self, op):
        if self.logops is not None:
            debug_print(self.logops.repr_of_resop(op))
        dispatch_opt(self, op)

    def _get_oopspec(self, op):
        effectinfo = op.getdescr().get_extra_info()
        if effectinfo is not None:
            return effectinfo.oopspecindex
        return EffectInfo.OS_NONE

    def _get_funcval(self, op):
        return self.getvalue(op.getarg(1))

dispatch_opt = make_dispatcher_method(OptFfiCall, 'optimize_',
        default=OptFfiCall.emit_operation)
