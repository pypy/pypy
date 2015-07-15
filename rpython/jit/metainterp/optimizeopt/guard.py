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
        BoxFloat, BoxInt, ConstFloat, Box, Const)
from rpython.rlib.objectmodel import we_are_translated

class Guard(object):
    """ An object wrapper around a guard. Helps to determine
        if one guard implies another
    """
    def __init__(self, index, op, cmp_op, lhs_arg, rhs_arg):
        self.index = index
        self.op = op
        self.cmp_op = cmp_op
        self.lhs_arg = lhs_arg
        self.rhs_arg = rhs_arg
        self.lhs_key = None
        self.rhs_key = None

    def implies(self, guard, opt):
        if self.op.getopnum() != guard.op.getopnum():
            return False

        if self.lhs_key == guard.lhs_key:
            # same operation
            valid, lc = self.compare(self.lhs, guard.lhs)
            if not valid:
                return False
            valid, rc = self.compare(self.rhs, guard.rhs)
            if not valid:
                return False
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
        self.index = other.index

        descr = myop.getdescr()
        if we_are_translated():
            descr.copy_all_attributes_from(other.op.getdescr())
            myop.rd_frame_info_list = otherop.rd_frame_info_list
            myop.rd_snapshot = otherop.rd_snapshot
            myop.setfailargs(otherop.getfailargs())

    def compare(self, key1, key2):
        if isinstance(key1, Box):
            if isinstance(key2, Box) and key1 is key2:
                return True, 0
            return False, 0
        #
        if isinstance(key1, ConstInt):
            if not isinstance(key2, ConstInt):
                return False, 0
            v1 = key1.value
            v2 = key2.value
            if v1 == v2:
                return True, 0
            elif v1 < v2:
                return True, -1
            else:
                return True, 1
        #
        if isinstance(key1, IndexVar):
            assert isinstance(key2, IndexVar)
            return True, key1.compare(key2)
        #
        raise AssertionError("cannot compare: " + str(key1) + " <=> " + str(key2))

    def emit_varops(self, opt, var, old_arg):
        if isinstance(var, IndexVar):
            if var.is_identity():
                return var.var
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

    def update_keys(self, index_vars):
        self.lhs = index_vars.get(self.lhs_arg, self.lhs_arg)
        if isinstance(self.lhs, IndexVar):
            self.lhs = self.lhs.var
        self.lhs_key = self.lhs
        #
        self.rhs = index_vars.get(self.rhs_arg, self.rhs_arg)
        if isinstance(self.rhs, IndexVar):
            self.rhs = self.rhs.var
        self.rhs_key = self.rhs

    @staticmethod
    def of(boolarg, operations, index):
        guard_op = operations[index]
        i = index - 1
        # most likely hit in the first iteration
        while i > 0:
            op = operations[i]
            if op.result and op.result == boolarg:
                if rop.INT_LT <= op.getopnum() <= rop.INT_GE:
                    cmp_op = op
                    break
                return None
            i -= 1
        else:
            raise AssertionError("guard_true/false first arg not defined")
        #
        lhs_arg = cmp_op.getarg(0)
        rhs_arg = cmp_op.getarg(1)
        return Guard(i, guard_op, cmp_op, lhs_arg, rhs_arg)

class GuardStrengthenOpt(object):
    def __init__(self, index_vars):
        self.index_vars = index_vars
        self._newoperations = []
        self.strength_reduced = 0 # how many guards could be removed?
        self.strongest_guards = {}
        self.guards = {}

    #def _get_key(self, cmp_op):
    #    assert cmp_op
    #    lhs_arg = cmp_op.getarg(0)
    #    rhs_arg = cmp_op.getarg(1)
    #    lhs_index_var = self.index_vars.get(lhs_arg, None)
    #    rhs_index_var = self.index_vars.get(rhs_arg, None)

    #    cmp_opnum = cmp_op.getopnum()
    #    # get the key, this identifies the guarded operation
    #    if lhs_index_var and rhs_index_var:
    #        return (lhs_index_var.getvariable(), cmp_opnum, rhs_index_var.getvariable())
    #    elif lhs_index_var:
    #        return (lhs_index_var.getvariable(), cmp_opnum, None)
    #    elif rhs_index_var:
    #        return (None, cmp_opnum, rhs_index_var)
    #    else:
    #        return (None, cmp_opnum, None)
    #    return key

    def collect_guard_information(self, loop):
        operations = loop.operations
        last_guard = None
        for i,op in enumerate(operations):
            op = operations[i]
            if not op.is_guard():
                continue
            if op.getopnum() in (rop.GUARD_TRUE, rop.GUARD_FALSE):
                guard = Guard.of(op.getarg(0), operations, i)
                if guard is None:
                    continue
                guard.update_keys(self.index_vars)
                self.record_guard(guard.lhs_key, guard)
                self.record_guard(guard.rhs_key, guard)

    def record_guard(self, key, guard):
        if key is None:
            return
        # the operations are processed from 1..n (forward),
        # thus if the key is not present (1), the guard is saved
        # (2) guard(s) with this key is/are already present,
        # thus each of is seen as possible candidate to strengthen
        # or imply the current. in both cases the current guard is
        # not emitted and the original is replaced with the current
        others = self.strongest_guards.setdefault(key, [])
        if len(others) > 0: # (2)
            for i,other in enumerate(others):
                if guard.implies(other, self):
                    # strengthend
                    guard.inhert_attributes(other)
                    others[i] = guard
                    self.guards[other.index] = guard
                    self.guards[guard.index] = None # mark as 'do not emit'
                    continue
                elif other.implies(guard, self):
                    # implied
                    self.guards[guard.index] = None # mark as 'do not emit'
                    continue
        else: # (2)
            others.append(guard)

    def eliminate_guards(self, loop):
        self.renamer = Renamer()
        for i,op in enumerate(loop.operations):
            op = loop.operations[i]
            if op.is_guard():
                if i in self.guards:
                    # either a stronger guard has been saved
                    # or it should not be emitted
                    guard = self.guards[i]
                    # this guard is implied or marked as not emitted (= None)
                    self.strength_reduced += 1
                    if guard is None:
                        continue
                    guard.emit_operations(self)
                    continue
                else:
                    self.emit_operation(op)
                    continue
            if op.result:
                index_var = self.index_vars.get(op.result, None)
                if index_var:
                    if not index_var.is_identity():
                        index_var.emit_operations(self, op.result)
                        continue
            self.emit_operation(op)
        #
        loop.operations = self._newoperations[:]

    def propagate_all_forward(self, loop):
        """ strengthens the guards that protect an integral value """
        # the guards are ordered. guards[i] is before guards[j] iff i < j
        self.collect_guard_information(loop)
        #
        self.eliminate_guards(loop)

    def emit_operation(self, op):
        self.renamer.rename(op)
        self._newoperations.append(op)

