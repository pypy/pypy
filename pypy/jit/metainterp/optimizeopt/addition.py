from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.history import ConstInt
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.resoperation import rop, ResOperation

class OptAddition(Optimization):
    def __init__(self):
        self.loperands = {}
        self.roperands = {} # roperands is only for int_sub(ConstInt(*), i*)
                            # and cases deriving from that

    def reconstruct_for_next_iteration(self, optimizer, valuemap):
        return OptAddition()

    def propagate_forward(self, op):
        opnum = op.getopnum()
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.emit_operation(op)

    def _int_operation(self, variable, constant, result):
        if constant < 0:
            constant = ConstInt(-constant)
            return ResOperation(rop.INT_SUB, [variable, constant], result)
        else:
            constant = ConstInt(constant)
            return ResOperation(rop.INT_ADD, [variable, constant], result)

    def _process_add(self, constant, variable, result):
        # int_add(ConstInt(*), int_sub(ConstInt(*), i*))
        try:
            stored_constant, root = self.roperands[variable]
            constant = constant + stored_constant

            self.roperands[result] = constant, root

            boxed_constant = ConstInt(constant)
            new_op = ResOperation(rop.INT_SUB, [boxed_constant, variable], result)
            self.emit_operation(new_op)
            return
        except KeyError:
            pass

        # int_add(ConstInt(*), int_add(ConstInt(*), i*))
        try:
            root, stored_constant = self.loperands[variable]
            constant = constant + stored_constant
        except KeyError:
            root = variable

        self.loperands[result] = root, constant

        new_op = self._int_operation(root, constant, result)
        self.emit_operation(new_op)

    def _process_sub(self, constant, variable, result):
        # int_sub(ConstInt(*), int_sub(ConstInt(*), i*))
        try:
            stored_constant, root = self.roperands[variable]
            constant = constant - stored_constant

            self.loperands[result] = root, constant

            new_op = self._int_operation(root, constant, result)
            self.emit_operation(new_op)
            return
        except KeyError:
            pass

        # int_sub(ConstInt(*), int_add(ConstInt(*), i*))
        try:
            root, stored_constant = self.loperands[variable]
            constant = constant - stored_constant
        except KeyError:
            root = variable

        self.roperands[result] = constant, root

        constant = ConstInt(constant)
        new_op = ResOperation(rop.INT_SUB, [constant, root], result)
        self.emit_operation(new_op)

    def optimize_INT_ADD(self, op):
        lv = self.getvalue(op.getarg(0))
        rv = self.getvalue(op.getarg(1))
        result = op.result
        if lv.is_constant() and rv.is_constant():
            self.emit_operation(op) # XXX: there's support for optimizing this elsewhere, right?
        elif lv.is_constant():
            constant = lv.box.getint()
            self._process_add(constant, op.getarg(1), result)
        elif rv.is_constant():
            constant = rv.box.getint()
            self._process_add(constant, op.getarg(0), result)
        else:
            self.emit_operation(op)

    def optimize_INT_SUB(self, op):
        lv = self.getvalue(op.getarg(0))
        rv = self.getvalue(op.getarg(1))
        result = op.result
        if lv.is_constant() and rv.is_constant():
            self.emit_operation(op) # XXX: there's support for optimizing this elsewhere, right?
        elif lv.is_constant():
            constant = lv.box.getint()
            self._process_sub(constant, op.getarg(1), result)
            #self.emit_operation(op)
        elif rv.is_constant():
            constant = rv.box.getint()
            self._process_add(-constant, op.getarg(0), result)
        else:
            self.emit_operation(op)

optimize_ops = _findall(OptAddition, 'optimize_')
