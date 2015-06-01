import py

from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.metainterp.optimizeopt.vectorize import (VecScheduleData,
        Pack, NotAProfitableLoop)
from rpython.jit.metainterp.optimizeopt.dependency import Node
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from rpython.jit.metainterp.optimizeopt.test.test_dependency import DependencyBaseTest
from rpython.jit.tool.oparser import parse as opparse
from rpython.jit.tool.oparser_model import get_model

class SchedulerBaseTest(DependencyBaseTest):

    def parse(self, source):
        ns = {
            'double': self.floatarraydescr,
            'float': self.singlefloatarraydescr,
            'long': self.intarraydescr,
        }
        loop = opparse("        [p0,p1,p2,p3,p4,p5,i0,i1,i2,i3,i4,i5,f0,f1,f2,f3,f4,f5]\n" + source + \
                       "\n        jump(p0,p1,p2,p3,p4,p5,i0,i1,i2,i3,i4,i5,f0,f1,f2,f3,f4,f5)",
                       cpu=self.cpu,
                       namespace=ns)
        del loop.operations[-1]
        return loop

    def pack(self, loop, l, r):
        return [Node(op,l+i) for i,op in enumerate(loop.operations[l:r])]

    def schedule(self, loop_orig, packs, vec_reg_size=16):
        loop = get_model(False).ExtendedTreeLoop("loop")
        loop.original_jitcell_token = loop_orig.original_jitcell_token
        loop.inputargs = loop_orig.inputargs

        ops = []
        vsd = VecScheduleData(vec_reg_size)
        for pack in packs:
            if len(pack) == 1:
                ops.append(pack[0].getoperation())
            else:
                for op in vsd.as_vector_operation(Pack(pack)):
                    ops.append(op)
        loop.operations = ops
        return loop

    def assert_operations_match(self, loop_a, loop_b):
        assert equaloplists(loop_a.operations, loop_b.operations)

    def test_schedule_split_load(self):
        loop1 = self.parse("""
        i10 = raw_load(p0, i0, descr=float)
        i11 = raw_load(p0, i1, descr=float)
        i12 = raw_load(p0, i2, descr=float)
        i13 = raw_load(p0, i3, descr=float)
        i14 = raw_load(p0, i4, descr=float)
        i15 = raw_load(p0, i5, descr=float)
        """)
        pack1 = self.pack(loop1, 0, 6)
        loop2 = self.schedule(loop1, [pack1])
        loop3 = self.parse("""
        v1[i32#4] = vec_raw_load(p0, i0, 4, descr=float)
        i14 = raw_load(p0, i4, descr=float)
        i15 = raw_load(p0, i5, descr=float)
        """)
        self.assert_equal(loop2, loop3)

    def test_int_to_float(self):
        loop1 = self.parse("""
        i10 = raw_load(p0, i0, descr=long)
        i11 = raw_load(p0, i1, descr=long)
        f10 = cast_int_to_float(i10)
        f11 = cast_int_to_float(i11)
        """)
        pack1 = self.pack(loop1, 0, 2)
        pack2 = self.pack(loop1, 2, 4)
        print pack1
        print pack2
        loop2 = self.schedule(loop1, [pack1, pack2])
        loop3 = self.parse("""
        v1[i64#2] = vec_raw_load(p0, i0, 2, descr=long)
        v2[i32#2] = vec_int_signext(v1[i64#2], 4)
        v3[f64#2] = vec_cast_int_to_float(v2[i32#2])
        """)
        self.assert_equal(loop2, loop3)

    def test_cost_model_reject_only_load_vectorizable(self):
        loop1 = self.parse("""
        f10 = raw_load(p0, i0, descr=long)
        f11 = raw_load(p0, i1, descr=long)
        guard_true(i0) [f10]
        guard_true(i1) [f11]
        """)
        try:
            pack1 = self.pack(loop1, 0, 2)
            pack2 = self.pack(loop1, 2, 3)
            pack3 = self.pack(loop1, 3, 4)
            loop2 = self.schedule(loop1, [pack1, pack2, pack3])
            py.test.fail("this loops should have bailed out")
        except NotAProfitableLoop:
            pass

class TestLLType(SchedulerBaseTest, LLtypeMixin):
    pass
