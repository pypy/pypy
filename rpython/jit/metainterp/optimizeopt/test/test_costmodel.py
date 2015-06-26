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

class CostModelBaseTest(SchedulerBaseTest):
    def savings(self, loop):
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        jitdriver_sd = FakeJitDriverStaticData()
        opt = VectorizingOptimizer(metainterp_sd, jitdriver_sd, loop, [])
        opt.build_dependency_graph()
        graph = opt.dependency_graph
        for k,m in graph.memory_refs.items():
            graph.memory_refs[k] = FakeMemoryRef(m.array, m.index_var)
        opt.find_adjacent_memory_refs()
        opt.extend_packset()
        opt.combine_packset()
        for pack in opt.packset.packs:
            print "pack: \n   ",
            print '\n    '.join([str(op.getoperation()) for op in pack.operations])
            print
        opt.costmodel.reset_savings()
        opt.schedule(True)
        return opt.costmodel.savings

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
        f10 = raw_load(p0, i0, descr=double)
        f11 = raw_load(p0, i1, descr=double)
        i20 = cast_float_to_int(f10)
        i21 = cast_float_to_int(f11)
        i30 = int_signext(i20, 4)
        i31 = int_signext(i21, 4)
        raw_store(p0, i3, i30, descr=int)
        raw_store(p0, i4, i31, descr=int)
        """)
        savings = self.savings(loop1)
        assert savings >= 0

    def test_sum(self):
        loop1 = self.parse("""
        f10 = raw_load(p0, i0, descr=double)
        f11 = raw_load(p0, i1, descr=double)
        f12 = float_add(f1, f10)
        f13 = float_add(f12, f11)
        """)
        savings = self.savings(loop1)
        assert savings == 2

    @py.test.mark.parametrize("bytes,s", [(1,None),(2,None),(4,0),(8,-1)])
    def test_sum_float_to_int(self, bytes, s):
        loop1 = self.parse("""
        f10 = raw_load(p0, i0, descr=double)
        f11 = raw_load(p0, i1, descr=double)
        i10 = cast_float_to_int(f10)
        i11 = cast_float_to_int(f11)
        i12 = int_signext(i10, {c})
        i13 = int_signext(i11, {c})
        i14 = int_add(i1, i12)
        i16 = int_signext(i14, {c})
        i15 = int_add(i16, i13)
        i17 = int_signext(i15, {c})
        """.format(c=bytes))
        try:
            savings = self.savings(loop1)
            if s is None:
                py.test.fail("must fail")
            # it does not benefit because signext has
            # a very inefficient implementation (x86
            # does not provide nice instr to convert
            # integer sizes)
            # signext -> no benefit, + 2x unpack
            assert savings <= s
        except NotAProfitableLoop:
            if s is not None:
                py.test.fail("must not fail")

    def test_cast(self):
        loop1 = self.parse("""
        i100 = raw_load(p0, i1, descr=float)
        i101 = raw_load(p0, i2, descr=float)
        i102 = raw_load(p0, i3, descr=float)
        i103 = raw_load(p0, i4, descr=float)
        #
        i104 = raw_load(p1, i1, descr=short)
        i105 = raw_load(p1, i2, descr=short)
        i106 = raw_load(p1, i3, descr=short)
        i107 = raw_load(p1, i4, descr=short)
        i108 = raw_load(p1, i5, descr=short)
        i109 = raw_load(p1, i6, descr=short)
        i110 = raw_load(p1, i7, descr=short)
        i111 = raw_load(p1, i8, descr=short)
        #
        f100 = cast_int_to_float(i104)
        f101 = cast_int_to_float(i105)
        f102 = cast_int_to_float(i106)
        f103 = cast_int_to_float(i107)
        f104 = cast_int_to_float(i108)
        f105 = cast_int_to_float(i109)
        f106 = cast_int_to_float(i110)
        f107 = cast_int_to_float(i111)
        """)
        savings = self.savings(loop1)
        assert savings <= -2

class Test(CostModelBaseTest, LLtypeMixin):
    pass
