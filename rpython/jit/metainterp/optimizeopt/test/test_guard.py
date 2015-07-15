import py

from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.metainterp.optimizeopt.vectorize import (VecScheduleData,
        Pack, NotAProfitableLoop, VectorizingOptimizer)
from rpython.jit.metainterp.optimizeopt.dependency import Node, DependencyGraph
from rpython.jit.metainterp.optimizeopt.guard import GuardStrengthenOpt
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from rpython.jit.metainterp.optimizeopt.test.test_schedule import SchedulerBaseTest
from rpython.jit.metainterp.optimizeopt.test.test_vectorize import (FakeMetaInterpStaticData,
        FakeJitDriverStaticData)
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.tool.oparser_model import get_model

class FakeMemoryRef(object):
    def __init__(self, array, iv):
        self.index_var = iv
        self.array = array

    def is_adjacent_to(self, other):
        if self.array is not other.array:
            return False
        iv = self.index_var
        ov = other.index_var
        val = (int(str(ov.var)[1:]) - int(str(iv.var)[1:]))
        # i0 and i1 are adjacent
        # i1 and i0 ...
        # but not i0, i2
        # ...
        return abs(val) == 1

class GuardBaseTest(SchedulerBaseTest):
    def optguards(self, loop):
        dep = DependencyGraph(loop)
        opt = GuardStrengthenOpt(dep.index_vars)
        opt.propagate_all_forward(loop)
        return opt

    def assert_guard_count(self, loop, count):
        guard = 0
        for op in loop.operations:
            if op.is_guard():
                guard += 1
        if guard != count:
            self.debug_print_operations(loop)
        assert guard == count

    def assert_contains_sequence(self, loop, instr):
        class Glob(object):
            def __repr__(self):
                return '*'
        from rpython.jit.tool.oparser import OpParser, default_fail_descr
        parser = OpParser(instr, self.cpu, self.namespace(), 'lltype', None, default_fail_descr, True, None)
        operations = []
        last_glob = None
        prev_op = None
        for line in instr.splitlines():
            line = line.strip()
            if line.startswith("#") or \
               line == "":
                continue
            if line.startswith("..."):
                last_glob = Glob()
                last_glob.prev = prev_op
                operations.append(last_glob)
                continue
            op = parser.parse_next_op(line)
            if last_glob is not None:
                last_glob.next = op
                last_glob = None
            operations.append(op)
            prev_op = op

        def check(op, candidate, rename):
            if isinstance(candidate, Glob):
                if candidate.next is None:
                    return 0 # consumes the rest
                if op.getopnum() != candidate.next.getopnum():
                    return 0
                candidate = candidate.next
            if op.getopnum() == candidate.getopnum():
                for i,arg in enumerate(op.getarglist()):
                    oarg = candidate.getarg(i)
                    if arg in rename:
                        assert rename[arg] is oarg
                    else:
                        rename[arg] = oarg

                if op.result:
                    rename[op.result] = candidate.result
                return 1
            return 0
        j = 0
        rename = {}
        for i, op in enumerate(loop.operations):
            candidate = operations[j]
            j += check(op, candidate, rename)
        if isinstance(operations[0], Glob):
            assert j == len(operations)-2
        else:
            assert j == len(operations)-1

    def test_basic(self):
        loop1 = self.parse("""
        i10 = int_lt(i1, 42)
        guard_true(i10) []
        i11 = int_add(i1, 1)
        i12 = int_lt(i11, 42)
        guard_true(i12) []
        """)
        opt = self.optguards(loop1)
        self.assert_guard_count(loop1, 1)
        self.assert_contains_sequence(loop1, """
        ...
        i11 = int_add(i1, 1)
        i12 = int_lt(i11, 42)
        guard_true(i12) []
        ...
        """)

    def test_basic_sub(self):
        loop1 = self.parse("""
        i10 = int_gt(i1, 42)
        guard_true(i10) []
        i11 = int_sub(i1, 1)
        i12 = int_gt(i11, 42)
        guard_true(i12) []
        """)
        opt = self.optguards(loop1)
        self.assert_guard_count(loop1, 1)
        self.assert_contains_sequence(loop1, """
        ...
        i11 = int_sub(i1, 1)
        i12 = int_gt(i11, 42)
        guard_true(i12) []
        ...
        """)

    def test_collapse(self):
        loop1 = self.parse("""
        i10 = int_gt(i1, 42)
        guard_true(i10) []
        i11 = int_sub(i1, 1)
        i12 = int_gt(i11, 42)
        guard_true(i12) []
        """)
        opt = self.optguards(loop1)
        self.assert_guard_count(loop1, 1)
        self.assert_contains_sequence(loop1, """
        ...
        i11 = int_sub(i1, 1)
        i12 = int_gt(i11, 42)
        guard_true(i12) []
        ...
        """)

class Test(GuardBaseTest, LLtypeMixin):
    pass
