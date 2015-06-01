import py

from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.metainterp.optimizeopt.vectorize import (VecScheduleData,
        Pack, NotAProfitableLoop, VectorizingOptimizer)
from rpython.jit.metainterp.optimizeopt.dependency import Node
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from rpython.jit.metainterp.optimizeopt.test.test_schedule import SchedulerBaseTest
from rpython.jit.metainterp.optimizeopt.test.test_vectorize import (FakeMetaInterpStaticData,
        FakeJitDriverStaticData)
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.tool.oparser import parse as opparse
from rpython.jit.tool.oparser_model import get_model

class FakeMemoryRef(object):
    def __init__(self, iv):
        self.index_var = iv

    def is_adjacent_to(self, other):
        iv = self.index_var
        ov = other.index_var
        val = (int(str(ov.var)[1:]) - int(str(iv.var)[1:]))
        print iv, ov, "adja?", val == 1
        # i0 and i1 are adjacent
        # i1 and i2 ...
        # but not i0, i2
        # ...
        return val == 1

class CostModelBaseTest(SchedulerBaseTest):
    def savings(self, loop):
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        jitdriver_sd = FakeJitDriverStaticData()
        opt = VectorizingOptimizer(metainterp_sd, jitdriver_sd, loop, [])
        opt.build_dependency_graph()
        graph = opt.dependency_graph
        for k,m in graph.memory_refs.items():
            graph.memory_refs[k] = FakeMemoryRef(m.index_var)
            print "memory ref", k, m
        opt.find_adjacent_memory_refs()
        opt.extend_packset()
        opt.combine_packset()
        for pack in opt.packset.packs:
            print "apck:"
            print '\n'.join([str(op.getoperation()) for op in pack.operations])
            print
        return opt.costmodel.calculate_savings(opt.packset)

    def assert_operations_match(self, loop_a, loop_b):
        assert equaloplists(loop_a.operations, loop_b.operations)

    def test_load_2_unpack(self):
        loop1 = self.parse("""
        f10 = raw_load(p0, i0, descr=double)
        f11 = raw_load(p0, i1, descr=double)
        guard_true(i0) [f10]
        guard_true(i1) [f11]
        """)
        # for double the costs are
        # unpack index 1 savings: -2
        # unpack index 0 savings: -1
        savings = self.savings(loop1)
        assert savings == -2

    def test_load_4_unpack(self):
        loop1 = self.parse("""
        i10 = raw_load(p0, i0, descr=float)
        i11 = raw_load(p0, i1, descr=float)
        i12 = raw_load(p0, i2, descr=float)
        i13 = raw_load(p0, i3, descr=float)
        guard_true(i0) [i10]
        guard_true(i1) [i11]
        guard_true(i2) [i12]
        guard_true(i3) [i13]
        """)
        savings = self.savings(loop1)
        assert savings == -1

    def test_load_2_unpack_1(self):
        loop1 = self.parse("""
        f10 = raw_load(p0, i0, descr=double)
        f11 = raw_load(p0, i1, descr=double)
        guard_true(i0) [f10]
        """)
        savings = self.savings(loop1)
        assert savings == 0

    def test_load_2_unpack_1_index1(self):
        loop1 = self.parse("""
        f10 = raw_load(p0, i0, descr=double)
        f11 = raw_load(p0, i1, descr=double)
        guard_true(i0) [f11]
        """)
        savings = self.savings(loop1)
        assert savings == -1

    def test_load_arith(self):
        loop1 = self.parse("""
        i10 = raw_load(p0, i0, descr=int)
        i11 = raw_load(p0, i1, descr=int)
        i12 = raw_load(p0, i2, descr=int)
        i13 = raw_load(p0, i3, descr=int)
        i15 = int_add(i10, 1)
        i16 = int_add(i11, 1)
        i17 = int_add(i12, 1)
        i18 = int_add(i13, 1)
        """)
        savings = self.savings(loop1)
        assert savings == 6

    def test_load_arith_store(self):
        loop1 = self.parse("""
        i10 = raw_load(p0, i0, descr=int)
        i11 = raw_load(p0, i1, descr=int)
        i12 = raw_load(p0, i2, descr=int)
        i13 = raw_load(p0, i3, descr=int)
        i15 = int_add(i10, 1)
        i16 = int_add(i11, 1)
        i17 = int_add(i12, 1)
        i18 = int_add(i13, 1)
        raw_store(p1, i4, i15, descr=int)
        raw_store(p1, i5, i16, descr=int)
        raw_store(p1, i6, i17, descr=int)
        raw_store(p1, i7, i18, descr=int)
        """)
        savings = self.savings(loop1)
        assert savings == 6

class Test(CostModelBaseTest, LLtypeMixin):
    pass
