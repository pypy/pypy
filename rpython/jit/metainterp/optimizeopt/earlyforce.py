from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.optimizeopt.optimizer import Optimization
from rpython.jit.metainterp.resoperation import rop


def is_raw_free(op, opnum):
    if opnum != rop.CALL:
        return False
    einfo = op.getdescr().get_extra_info()
    return einfo.oopspecindex == EffectInfo.OS_RAW_FREE


class OptEarlyForce(Optimization):
    def propagate_forward(self, op):
        opnum = op.getopnum()

        if (opnum != rop.SETFIELD_GC and
            opnum != rop.SETARRAYITEM_GC and
            opnum != rop.SETARRAYITEM_RAW and
            opnum != rop.QUASIIMMUT_FIELD and
            opnum != rop.SAME_AS and
            opnum != rop.MARK_OPAQUE_PTR and
            not is_raw_free(op, opnum)):

            for arg in op.getarglist():
                if arg in self.optimizer.values:
                    value = self.getvalue(arg)
                    value.force_box(self)
        self.emit_operation(op)

    def setup(self):
        self.optimizer.optearlyforce = self
