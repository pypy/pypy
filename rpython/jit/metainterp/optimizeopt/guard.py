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
    def __init__(self, index, op, cmp_op, index_vars):
        self.index = index
        self.op = op
        self.cmp_op = cmp_op
        self.lhs_key = None
        self.rhs_key = None
        lhs = cmp_op.getarg(0)
        self.lhs = index_vars.get(lhs, None)
        if self.lhs is None:
            self.lhs = IndexVar(lhs)
        #
        rhs = cmp_op.getarg(1)
        self.rhs = index_vars.get(rhs, None)
        if self.rhs is None:
            self.rhs = IndexVar(rhs)

    def getleftkey(self):
        return self.lhs.getvariable()

    def getrightkey(self):
        return self.rhs.getvariable()

    def implies(self, guard, opt):
        if self.op.getopnum() != guard.op.getopnum():
            return False

        if self.getleftkey() is guard.getleftkey():
            # same operation
            valid, lc = self.lhs.compare(guard.lhs)
            if not valid: return False
            valid, rc = self.rhs.compare(guard.rhs)
            if not valid: return False
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

    def transitive_imply(self, other, opt):
        if self.op.getopnum() != other.op.getopnum():
            # stronger restriction, intermixing e.g. <= and < would be possible
            return None
        if self.getleftkey() is not other.getleftkey():
            return None
        if not self.rhs.is_identity():
            # stronger restriction
            return None
        # this is a valid transitive guard that eliminates the loop guard
        opnum = self.transitive_cmpop(self.cmp_op.getopnum())
        box_rhs = self.emit_varops(opt, self.rhs, self.cmp_op.getarg(1))
        other_rhs = self.emit_varops(opt, other.rhs, other.cmp_op.getarg(1))
        box_result = self.cmp_op.result.clonebox()
        opt.emit_operation(ResOperation(opnum, [box_rhs, other_rhs], box_result))
        # guard
        guard = self.op.clone()
        guard.setarg(0, box_result)
        opt.emit_operation(guard)

        return guard

    def transitive_cmpop(self, opnum):
        if opnum == rop.INT_LT:
            return rop.INT_LE
        if opnum == rop.INT_GT:
            return rop.INT_GE
        return opnum

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

    def emit_varops(self, opt, var, old_arg):
        assert isinstance(var, IndexVar)
        if var.is_identity():
            return var.var
        box = var.emit_operations(opt)
        opt.renamer.start_renaming(old_arg, box)
        return box

    def emit_operations(self, opt):
        # create trace instructions for the index
        box_lhs = self.emit_varops(opt, self.lhs, self.cmp_op.getarg(0))
        box_rhs = self.emit_varops(opt, self.rhs, self.cmp_op.getarg(1))
        box_result = self.cmp_op.result.clonebox()
        opnum = self.cmp_op.getopnum()
        cmp_op = ResOperation(opnum, [box_lhs, box_rhs], box_result)
        opt.emit_operation(cmp_op)
        # emit that actual guard
        guard = self.op.clone()
        guard.setarg(0, box_result)
        opt.emit_operation(guard)
        guard.index = opt.operation_position()-1
        guard.op = guard
        guard.cmp_op = cmp_op

    def set_to_none(self, operations):
        assert operations[self.index] is self.op
        operations[self.index] = None
        if operations[self.index-1] is self.cmp_op:
            operations[self.index-1] = None

    @staticmethod
    def of(boolarg, operations, index, index_vars):
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
        return Guard(index, guard_op, cmp_op, index_vars)

class GuardStrengthenOpt(object):
    def __init__(self, index_vars):
        self.index_vars = index_vars
        self._newoperations = []
        self.strength_reduced = 0 # how many guards could be removed?
        self.strongest_guards = {}
        self.guards = {}

    def collect_guard_information(self, loop):
        operations = loop.operations
        last_guard = None
        for i,op in enumerate(operations):
            op = operations[i]
            if not op.is_guard():
                continue
            if op.getopnum() in (rop.GUARD_TRUE, rop.GUARD_FALSE):
                guard = Guard.of(op.getarg(0), operations, i, self.index_vars)
                if guard is None:
                    continue
                self.record_guard(guard.getleftkey(), guard)
                self.record_guard(guard.getrightkey(), guard)

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
            replaced = False
            for i,other in enumerate(others):
                if guard.implies(other, self):
                    # strengthend
                    others[i] = guard
                    self.guards[guard.index] = None # mark as 'do not emit'
                    guard.inhert_attributes(other)
                    self.guards[other.index] = guard
                    replaced = True
                    continue
                elif other.implies(guard, self):
                    # implied
                    self.guards[guard.index] = None # mark as 'do not emit'
                    replaced = True
                    continue
            if not replaced:
                others.append(guard)
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

    def propagate_all_forward(self, loop, user_code=False):
        """ strengthens the guards that protect an integral value """
        # the guards are ordered. guards[i] is before guards[j] iff i < j
        self.collect_guard_information(loop)
        self.eliminate_guards(loop)

        if user_code:
            version = loop.snapshot()
            self.eliminate_array_bound_checks(loop, version)

    def emit_operation(self, op):
        self.renamer.rename(op)
        self._newoperations.append(op)

    def operation_position(self):
        return len(self._newoperations)

    def eliminate_array_bound_checks(self, loop, version):
        self._newoperations = []
        for key, guards in self.strongest_guards.items():
            if len(guards) <= 1:
                continue
            # there is more than one guard for that key,
            # that is why we could imply the guards 2..n
            # iff we add invariant guards
            one = guards[0]
            for other in guards[1:]:
                transitive_guard = one.transitive_imply(other, self)
                if transitive_guard:
                    other.set_to_none(loop.operations)
                    version.register_guard(transitive_guard)

        loop.operations = self._newoperations + \
                [op for op in loop.operations if op]

    # OLD
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

