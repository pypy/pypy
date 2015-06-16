import py

from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt.util import equaloplists, Renamer
from rpython.jit.metainterp.optimizeopt.vectorize import (VecScheduleData,
        Pack, NotAProfitableLoop, VectorizingOptimizer, X86_CostModel)
from rpython.jit.metainterp.optimizeopt.dependency import Node
from rpython.jit.metainterp.optimizeopt.schedule import PackType
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from rpython.jit.metainterp.optimizeopt.test.test_dependency import DependencyBaseTest
from rpython.jit.metainterp.optimizeopt.test.test_vectorize import (FakeMetaInterpStaticData,
        FakeJitDriverStaticData)
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.tool.oparser import parse as opparse
from rpython.jit.tool.oparser_model import get_model

class SchedulerBaseTest(DependencyBaseTest):

    def parse(self, source, inc_label_jump=True):
        ns = {
            'double': self.floatarraydescr,
            'float': self.singlefloatarraydescr,
            'long': self.intarraydescr,
            'int': self.int32arraydescr,
            'short': self.int16arraydescr,
            'char': self.chararraydescr,
        }
        loop = opparse("        [p0,p1,p2,p3,p4,p5,i0,i1,i2,i3,i4,i5,i6,i7,i8,i9,f0,f1,f2,f3,f4,f5,v103204[i32|4]]\n" + source + \
                       "\n        jump(p0,p1,p2,p3,p4,p5,i0,i1,i2,i3,i4,i5,i6,i7,i8,i9,f0,f1,f2,f3,f4,f5,v103204[i32|4])",
                       cpu=self.cpu,
                       namespace=ns)
        if inc_label_jump:
            token = JitCellToken()
            loop.operations = \
                [ResOperation(rop.LABEL, loop.inputargs, None, descr=TargetToken(token))] + \
                loop.operations
            return loop

        del loop.operations[-1]
        return loop

    def pack(self, loop, l, r):
        return Pack([Node(op,1+l+i) for i,op in enumerate(loop.operations[1+l:1+r])], None, None)

    def schedule(self, loop_orig, packs, vec_reg_size=16, prepend_invariant=False, getvboxfunc=None):
        loop = get_model(False).ExtendedTreeLoop("loop")
        loop.original_jitcell_token = loop_orig.original_jitcell_token
        loop.inputargs = loop_orig.inputargs

        ops = []
        cm = X86_CostModel(0, vec_reg_size)
        vsd = VecScheduleData(vec_reg_size, cm)
        if getvboxfunc is not None:
            vsd.getvector_of_box = getvboxfunc
        renamer = Renamer()
        for pack in packs:
            if pack.opcount() == 1:
                ops.append(pack.operations[0].getoperation())
            else:
                for op in vsd.as_vector_operation(pack, renamer):
                    ops.append(op)
        loop.operations = ops
        if prepend_invariant:
            loop.operations = vsd.invariant_oplist + ops
        return loop

    def assert_operations_match(self, loop_a, loop_b):
        assert equaloplists(loop_a.operations, loop_b.operations)

class Test(SchedulerBaseTest, LLtypeMixin):
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
        v10[i32|4] = vec_raw_load(p0, i0, 4, descr=float)
        i14 = raw_load(p0, i4, descr=float)
        i15 = raw_load(p0, i5, descr=float)
        """, False)
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
        loop2 = self.schedule(loop1, [pack1, pack2])
        loop3 = self.parse("""
        v10[i64|2] = vec_raw_load(p0, i0, 2, descr=long)
        v20[i32|2] = vec_int_signext(v10[i64|2], 4)
        v30[f64|2] = vec_cast_int_to_float(v20[i32|2])
        """, False)
        self.assert_equal(loop2, loop3)

    def test_scalar_pack(self):
        loop1 = self.parse("""
        i10 = int_add(i0, 73)
        i11 = int_add(i1, 73)
        """)
        pack1 = self.pack(loop1, 0, 2)
        loop2 = self.schedule(loop1, [pack1], prepend_invariant=True)
        loop3 = self.parse("""
        v10[i64|2] = vec_box(2)
        v20[i64|2] = vec_int_pack(v10[i64|2], i0, 0, 1)
        v30[i64|2] = vec_int_pack(v20[i64|2], i1, 1, 1)
        v40[i64|2] = vec_int_expand(73)
        #
        v50[i64|2] = vec_int_add(v30[i64|2], v40[i64|2])
        """, False)
        self.assert_equal(loop2, loop3)

        loop1 = self.parse("""
        f10 = float_add(f0, 73.0)
        f11 = float_add(f1, 73.0)
        """)
        pack1 = self.pack(loop1, 0, 2)
        loop2 = self.schedule(loop1, [pack1], prepend_invariant=True)
        loop3 = self.parse("""
        v10[f64|2] = vec_box(2)
        v20[f64|2] = vec_float_pack(v10[f64|2], f0, 0, 1)
        v30[f64|2] = vec_float_pack(v20[f64|2], f1, 1, 1)
        v40[f64|2] = vec_float_expand(73.0)
        #
        v50[f64|2] = vec_float_add(v30[f64|2], v40[f64|2])
        """, False)
        self.assert_equal(loop2, loop3)

    def test_scalar_remember_expansion(self):
        loop1 = self.parse("""
        f10 = float_add(f0, f5)
        f11 = float_add(f1, f5)
        f12 = float_add(f10, f5)
        f13 = float_add(f11, f5)
        """)
        pack1 = self.pack(loop1, 0, 2)
        pack2 = self.pack(loop1, 2, 4)
        loop2 = self.schedule(loop1, [pack1, pack2], prepend_invariant=True)
        loop3 = self.parse("""
        v10[f64|2] = vec_box(2)
        v20[f64|2] = vec_float_pack(v10[f64|2], f0, 0, 1)
        v30[f64|2] = vec_float_pack(v20[f64|2], f1, 1, 1)
        v40[f64|2] = vec_float_expand(f5) # only expaned once
        #
        v50[f64|2] = vec_float_add(v30[f64|2], v40[f64|2])
        v60[f64|2] = vec_float_add(v50[f64|2], v40[f64|2])
        """, False)
        self.assert_equal(loop2, loop3)

    def find_input_arg(self, name, loop):
        for arg in loop.inputargs:
            if str(arg).startswith(name):
                return arg
        raise Exception("could not find %s in args %s" % (name, loop.inputargs))

    def test_signext_int16(self):
        loop1 = self.parse("""
        i10 = int_signext(i1, 2)
        i11 = int_signext(i1, 2)
        i12 = int_signext(i1, 2)
        i13 = int_signext(i1, 2)
        """)
        pack1 = self.pack(loop1, 0, 4)
        v103204 = self.find_input_arg('v103204', loop1)
        def i1inv103204(var):
            return 0, v103204
        loop2 = self.schedule(loop1, [pack1], prepend_invariant=True, getvboxfunc=i1inv103204)
        loop3 = self.parse("""
        v11[i16|4] = vec_int_signext(v103204[i32|4], 2)
        """, False)
        self.assert_equal(loop2, loop3)

    def test_float_to_int(self):
        loop1 = self.parse("""
        f10 = raw_load(p0, i1, descr=double)
        f11 = raw_load(p0, i2, descr=double)
        f12 = raw_load(p0, i3, descr=double)
        f13 = raw_load(p0, i4, descr=double)
        f14 = raw_load(p0, i5, descr=double)
        f15 = raw_load(p0, i6, descr=double)
        f16 = raw_load(p0, i7, descr=double)
        f17 = raw_load(p0, i8, descr=double)
        #
        i10 = cast_float_to_int(f10)
        i11 = cast_float_to_int(f11)
        i12 = cast_float_to_int(f12)
        i13 = cast_float_to_int(f13)
        i14 = cast_float_to_int(f14)
        i15 = cast_float_to_int(f15)
        i16 = cast_float_to_int(f16)
        i17 = cast_float_to_int(f17)
        #
        i18 = int_signext(i10, 2)
        i19 = int_signext(i11, 2)
        i20 = int_signext(i12, 2)
        i21 = int_signext(i13, 2)
        i22 = int_signext(i14, 2)
        i23 = int_signext(i15, 2)
        i24 = int_signext(i17, 2)
        i25 = int_signext(i18, 2)
        #
        raw_store(p1, i1, i18, descr=short)
        raw_store(p1, i2, i19, descr=short)
        raw_store(p1, i3, i20, descr=short)
        raw_store(p1, i4, i21, descr=short)
        raw_store(p1, i5, i22, descr=short)
        raw_store(p1, i6, i23, descr=short)
        raw_store(p1, i7, i24, descr=short)
        raw_store(p1, i8, i25, descr=short)
        """)
        pack1 = self.pack(loop1, 0, 8)
        pack2 = self.pack(loop1, 8, 16)
        pack3 = self.pack(loop1, 16, 24)
        pack4 = self.pack(loop1, 24, 32)
        loop2 = self.schedule(loop1, [pack1,pack2,pack3,pack4])
        loop3 = self.parse("""
        v10[f64|2] = vec_raw_load(p0, i1, 2, descr=double)
        v11[f64|2] = vec_raw_load(p0, i3, 2, descr=double)
        v12[f64|2] = vec_raw_load(p0, i5, 2, descr=double)
        v13[f64|2] = vec_raw_load(p0, i7, 2, descr=double)
        v14[i32|2] = vec_cast_float_to_int(v10[f64|2])
        v15[i32|2] = vec_cast_float_to_int(v11[f64|2])
        v16[i32|2] = vec_cast_float_to_int(v12[f64|2])
        v17[i32|2] = vec_cast_float_to_int(v13[f64|2])
        v18[i16|2] = vec_int_signext(v14[i32|2],2)
        v19[i16|2] = vec_int_signext(v15[i32|2],2)
        v20[i16|2] = vec_int_signext(v16[i32|2],2)
        v21[i16|2] = vec_int_signext(v17[i32|2],2)
        v22[i16|4] = vec_int_pack(v18[i16|2], v19[i16|2], 2, 2)
        v23[i16|6] = vec_int_pack(v22[i16|4], v20[i16|2], 4, 2)
        v24[i16|8] = vec_int_pack(v23[i16|6], v20[i16|2], 6, 2)
        vec_raw_store(p1, i1, v24[i16|8], descr=short)
        """, False)
        self.assert_equal(loop2, loop3)
