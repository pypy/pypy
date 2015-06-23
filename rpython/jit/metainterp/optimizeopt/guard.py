"""
NOTE this strengthing optimization is only used in the vecopt.
It needs also the information about integral modifications
gathered with IntegralForwardModification
"""

from rpython.jit.metainterp.optimizeopt.util import Renamer
from rpython.jit.metainterp.optimizeopt.dependency import (DependencyGraph,
        MemoryRef, Node, IndexVar)
from rpython.jit.metainterp.resoperation import (rop, ResOperation, GuardResOp)
from rpython.jit.metainterp.history import (ConstInt, BoxVector, 
        BoxFloat, BoxInt, ConstFloat, Box)

class Guard(object):
    """ An object wrapper around a guard. Helps to determine
        if one guard implies another
    """
    def __init__(self, index, op, cmp_op, lhs, lhs_arg, rhs, rhs_arg):
        self.index = index
        self.op = op
        self.cmp_op = cmp_op
        self.lhs = lhs
        self.rhs = rhs
        self.lhs_arg = lhs_arg
        self.rhs_arg = rhs_arg
        self.implied = False
        self.stronger = False

    def implies(self, guard, opt):
        if self.op.getopnum() != guard.op.getopnum():
            return False

        my_key = opt._get_key(self.cmp_op)
        ot_key = opt._get_key(guard.cmp_op)

        if my_key[1] == ot_key[1]:
            # same operation
            lc = self.compare(self.lhs, guard.lhs)
            rc = self.compare(self.rhs, guard.rhs)
            opnum = self.get_compare_opnum()
            if opnum == -1:
                return False
            # x < y  = -1,-2,...
            # x == y = 0
            # x > y  = 1,2,...
            if opnum == rop.INT_LT:
                return (lc > 0 and rc >= 0) or (lc == 0 and rc >= 0)
            if opnum == rop.INT_LE:
                return (lc >= 0 and rc >= 0) or (lc == 0 and rc >= 0)
            if opnum == rop.INT_GT:
                return (lc < 0 and rc >= 0) or (lc == 0 and rc > 0)
            if opnum == rop.INT_GE:
                return (lc <= 0 and rc >= 0) or (lc == 0 and rc >= 0)
        return False

    def get_compare_opnum(self):
        opnum = self.op.getopnum()
        if opnum == rop.GUARD_TRUE:
            return self.cmp_op.getopnum()
        else:
            return self.cmp_op.boolinverse

    def inhert_attributes(self, other):
        myop = self.op
        otherop = other.op
        assert isinstance(otherop, GuardResOp)
        assert isinstance(myop, GuardResOp)
        self.stronger = True
        self.index = other.index

        descr = myop.getdescr()
        descr.copy_all_attributes_from(other.op.getdescr())
        myop.rd_frame_info_list = otherop.rd_frame_info_list
        myop.rd_snapshot = otherop.rd_snapshot
        myop.setfailargs(otherop.getfailargs())

    def compare(self, key1, key2):
        if isinstance(key1, Box):
            assert isinstance(key2, Box)
            assert key1 is key2 # key of hash enforces this
            return 0
        #
        if isinstance(key1, ConstInt):
            assert isinstance(key2, ConstInt)
            v1 = key1.value
            v2 = key2.value
            if v1 == v2:
                return 0
            elif v1 < v2:
                return -1
            else:
                return 1
        #
        if isinstance(key1, IndexVar):
            assert isinstance(key2, IndexVar)
            return key1.compare(key2)
        #
        raise AssertionError("cannot compare: " + str(key1) + " <=> " + str(key2))

    def emit_varops(self, opt, var, old_arg):
        if isinstance(var, IndexVar):
            box = var.emit_operations(opt)
            opt.renamer.start_renaming(old_arg, box)
            return box
        else:
            return var

    def emit_operations(self, opt):
        lhs, opnum, rhs = opt._get_key(self.cmp_op)
        # create trace instructions for the index
        box_lhs = self.emit_varops(opt, self.lhs, self.lhs_arg)
        box_rhs = self.emit_varops(opt, self.rhs, self.rhs_arg)
        box_result = self.cmp_op.result.clonebox()
        opt.emit_operation(ResOperation(opnum, [box_lhs, box_rhs], box_result))
        # guard
        guard = self.op.clone()
        guard.setarg(0, box_result)
        opt.emit_operation(guard)

class GuardStrengthenOpt(object):
    def __init__(self, index_vars):
        self.index_vars = index_vars
        self._newoperations = []
        self._same_as = {}
        self.strength_reduced = 0 # how many guards could be removed?

    def find_compare_guard_bool(self, boolarg, operations, index):
        i = index - 1
        # most likely hit in the first iteration
        while i > 0:
            op = operations[i]
            if op.result and op.result == boolarg:
                return op
            i -= 1

        raise AssertionError("guard_true/false first arg not defined")

    def _get_key(self, cmp_op):
        if cmp_op and rop.INT_LT <= cmp_op.getopnum() <= rop.INT_GE:
            lhs_arg = cmp_op.getarg(0)
            rhs_arg = cmp_op.getarg(1)
            lhs_index_var = self.index_vars.get(lhs_arg, None)
            rhs_index_var = self.index_vars.get(rhs_arg, None)

            cmp_opnum = cmp_op.getopnum()
            # get the key, this identifies the guarded operation
            if lhs_index_var and rhs_index_var:
                key = (lhs_index_var.getvariable(), cmp_opnum, rhs_index_var.getvariable())
            elif lhs_index_var:
                key = (lhs_index_var.getvariable(), cmp_opnum, rhs_arg)
            elif rhs_index_var:
                key = (lhs_arg, cmp_opnum, rhs_index_var)
            else:
                key = (lhs_arg, cmp_opnum, rhs_arg)
            return key
        return (None, 0, None)

    def get_key(self, guard_bool, operations, i):
        cmp_op = self.find_compare_guard_bool(guard_bool.getarg(0), operations, i)
        return self._get_key(cmp_op)

    def propagate_all_forward(self, loop):
        """ strengthens the guards that protect an integral value """
        strongest_guards = {}
        guards = {}
        # the guards are ordered. guards[i] is before guards[j] iff i < j
        operations = loop.operations
        last_guard = None
        for i,op in enumerate(operations):
            op = operations[i]
            if op.is_guard() and op.getopnum() in (rop.GUARD_TRUE, rop.GUARD_FALSE):
                cmp_op = self.find_compare_guard_bool(op.getarg(0), operations, i)
                key = self._get_key(cmp_op)
                if key[0] is not None:
                    lhs_arg = cmp_op.getarg(0)
                    lhs = self.index_vars.get(lhs_arg, lhs_arg)
                    rhs_arg = cmp_op.getarg(1)
                    rhs = self.index_vars.get(rhs_arg, rhs_arg)
                    other = strongest_guards.get(key, None)
                    if not other:
                        guard = Guard(i, op, cmp_op,
                                      lhs, lhs_arg,
                                      rhs, rhs_arg)
                        strongest_guards[key] = guard
                        # nothing known, at this position emit the guard
                        guards[i] = guard
                    else: # implicit index(strongest) < index(current)
                        guard = Guard(i, op, cmp_op,
                                      lhs, lhs_arg, rhs, rhs_arg)
                        if guard.implies(other, self):
                            guard.inhert_attributes(other)

                            strongest_guards[key] = guard
                            guards[other.index] = guard
                            # do not mark as emit
                            continue
                        elif other.implies(guard, self):
                            guard.implied = True
                        # mark as emit
                        guards[i] = guard
                else:
                    # emit non guard_true/false guards
                    guards[i] = Guard(i, op, None, None, None, None, None)

        strongest_guards = None
        #
        self.renamer = Renamer()
        last_op_idx = len(operations)-1
        for i,op in enumerate(operations):
            op = operations[i]
            if op.is_guard() and op.getopnum() in (rop.GUARD_TRUE, rop.GUARD_FALSE):
                guard = guards.get(i, None)
                if not guard or guard.implied:
                    # this guard is implied or marked as not emitted (= None)
                    self.strength_reduced += 1
                    continue
                if guard.stronger:
                    guard.emit_operations(self)
                    continue
            if op.result:
                index_var = self.index_vars.get(op.result, None)
                if index_var:
                    if not index_var.is_identity():
                        index_var.emit_operations(self, op.result)
                        continue
            self.emit_operation(op)

        loop.operations = self._newoperations[:]

    def emit_operation(self, op):
        self.renamer.rename(op)
        self._newoperations.append(op)

