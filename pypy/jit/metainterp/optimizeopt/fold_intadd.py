from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.resoperation import opboolinvers, opboolreflex
from pypy.jit.metainterp.history import ConstInt
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.metainterp.optimizeopt.intutils import IntBound
from pypy.rlib.rarithmetic import highest_bit

class OptAddition(Optimization):
    def __init__(self):
        self.args = {}

    def reconstruct_for_next_iteration(self, optimizer, valuemap):
        return OptAddition()

    def propagate_forward(self, op):
        opnum = op.getopnum()
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.optimize_default(op)

    def _int_add(self, variable, constant, result):
        return ResOperation(rop.INT_ADD, [variable, constant], result)

    def _store_add(self, variable, constant, result):
        try:
            root, stored_constant = self.args[variable]
            constant = constant + stored_constant
        except KeyError:
            root = variable

        self.args[result] = root, constant

    def optimize_INT_ADD(self, op):
        lv = self.getvalue(op.getarg(0))
        rv = self.getvalue(op.getarg(1))
        print "lv = %s rv = %s" % (lv.box, rv.box)
        result = op.result
        if lv.is_constant() and rv.is_constant():
            self.emit_operation(op) # XXX: there's support for optimizing this elsewhere, right?
        elif lv.is_constant():
            constant = lv.box.getint()
            self._store_add(op.getarg(1), constant, result)
        elif rv.is_constant():
            constant = rv.box.getint()
            self._store_add(op.getarg(0), constant, result)
        else:
            self.emit_operation(op)

    def optimize_default(self, op):
        for i in range(op.numargs()):
            arg = self.getvalue(op.getarg(i))
            print 'type(%s) = %s' % (arg.box, type(arg))
            if arg.is_constant():
                continue

            try:
                variable = op.getarg(i)
                root, constant = self.args[variable]
                del self.args[variable] # TODO: mark as used instead of deleting

                constant = ConstInt(constant)
                new_op = self._int_add(root, constant, variable)
                print new_op
                self.emit_operation(new_op)
            except KeyError:
                pass
        print op
        self.emit_operation(op)

    #def optimize_INT_SUB(self, op): pass

optimize_ops = _findall(OptAddition, 'optimize_')
