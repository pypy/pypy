import py

from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt.util import equaloplists, Renamer
from rpython.jit.metainterp.optimizeopt.vectorize import (VecScheduleData,
        Pack, Pair, NotAProfitableLoop, VectorizingOptimizer, X86_CostModel,
        PackSet)
from rpython.jit.metainterp.optimizeopt.dependency import Node, DependencyGraph
from rpython.jit.metainterp.optimizeopt.schedule import PackType
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from rpython.jit.metainterp.optimizeopt.test.test_dependency import DependencyBaseTest
from rpython.jit.metainterp.optimizeopt.test.test_vectorize import (FakeMetaInterpStaticData,
        FakeJitDriverStaticData)
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.tool.oparser import parse as opparse
from rpython.jit.tool.oparser_model import get_model

F64 = PackType('f',8,False,2)
F32 = PackType('f',4,False,4)
F32_2 =  PackType('f',4,False,2)
I64 = PackType('i',8,True,2)
I32 = PackType('i',4,True,4)
I32_2 =  PackType('i',4,True,2)
I16 = PackType('i',2,True,8)

class FakePackSet(PackSet):
    def __init__(self):
        self.packs = None

class FakeDependencyGraph(DependencyGraph):
    """ A dependency graph that is able to emit every instruction
    one by one. """
    def __init__(self, loop):
        self.nodes = [Node(op,i) for i,op in \
                        enumerate(loop.operations)]
        self.schedulable_nodes = list(reversed(self.nodes))
        self.guards = []

class SchedulerBaseTest(DependencyBaseTest):

    def namespace(self):
        return {
            'double': self.floatarraydescr,
            'float': self.singlefloatarraydescr,
            'long': self.intarraydescr,
            'int': self.int32arraydescr,
            'short': self.int16arraydescr,
            'char': self.chararraydescr,
        }

    def parse(self, source, inc_label_jump=True,
              pargs=2,
              iargs=10,
              fargs=6,
              additional_args=None,
              replace_args=None):
        args = []
        for prefix, rang in [('p',range(pargs)),
                             ('i',range(iargs)),
                             ('f',range(fargs))]:
            for i in rang:
                args.append(prefix + str(i))

        assert additional_args is None or isinstance(additional_args,list)
        for arg in additional_args or []:
            args.append(arg)
        for k,v in (replace_args or {}).items():
            for i,_ in enumerate(args):
                if k == args[i]:
                    args[i] = v
                    break
        indent = "        "
        joinedargs = ','.join(args)
        fmt = (indent, joinedargs, source, indent, joinedargs)
        src = "%s[%s]\n%s\n%sjump(%s)" % fmt
        loop = opparse(src, cpu=self.cpu, namespace=self.namespace())
        if inc_label_jump:
            token = JitCellToken()
            label = ResOperation(rop.LABEL, loop.inputargs,
                                 None, descr=TargetToken(token))
            loop.operations = [label] + loop.operations
            loop.graph = FakeDependencyGraph(loop)
            return loop
        else:
            loop.graph = FakeDependencyGraph(loop)
        del loop.operations[-1]
        return loop

    def pack(self, loop, l, r, input_type, output_type):
        return Pack(loop.graph.nodes[1+l:1+r], input_type, output_type)

    def schedule(self, loop, packs, vec_reg_size=16,
                 prepend_invariant=False, overwrite_funcs=None):
        ops = []
        cm = X86_CostModel(0, vec_reg_size)
        def profitable():
            return True
        cm.profitable = profitable
        vsd = VecScheduleData(vec_reg_size, cm, loop.inputargs[:])
        for name, overwrite in (overwrite_funcs or {}).items():
            setattr(vsd, name, overwrite)
        renamer = Renamer()
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        jitdriver_sd = FakeJitDriverStaticData()
        opt = VectorizingOptimizer(metainterp_sd, jitdriver_sd, loop, 0)
        opt.costmodel = cm
        opt.dependency_graph = loop.graph
        del loop.graph
        pairs = []
        for pack in packs:
            for i in range(len(pack.operations)-1):
                pack.clear()
                o1 = pack.operations[i]
                o2 = pack.operations[i+1]
                pair = Pair(o1,o2,pack.input_type,pack.output_type)
                pairs.append(pair)

        opt.packset = FakePackSet()
        opt.packset.packs = pairs

        if not prepend_invariant:
            def pio(oplist, labels):
                return oplist
            vsd.prepend_invariant_operations = pio

        opt.combine_packset()
        opt.schedule(True, sched_data=vsd)

        loop.operations = \
                [op for op in loop.operations \
                 if not (op.is_final() or op.is_label())]

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
        pack1 = self.pack(loop1, 0, 6, None, F32)
        loop2 = self.schedule(loop1, [pack1])
        loop3 = self.parse("""
        v10[i32|4] = vec_raw_load(p0, i0, 4, descr=float)
        v11[i32|2] = vec_raw_load(p0, i4, 2, descr=float)
        """, False)
        self.assert_equal(loop2, loop3)

    def test_int_to_float(self):
        loop1 = self.parse("""
        i10 = raw_load(p0, i0, descr=long)
        i11 = raw_load(p0, i1, descr=long)
        i12 = int_signext(i10, 4)
        i13 = int_signext(i11, 4)
        f10 = cast_int_to_float(i12)
        f11 = cast_int_to_float(i13)
        """)
        pack1 = self.pack(loop1, 0, 2, None, I64)
        pack2 = self.pack(loop1, 2, 4, I64, I32_2)
        pack3 = self.pack(loop1, 4, 6, I32_2, F32_2)
        loop2 = self.schedule(loop1, [pack1, pack2, pack3])
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
        pack1 = self.pack(loop1, 0, 2, I64, I64)
        loop2 = self.schedule(loop1, [pack1], prepend_invariant=True)
        loop3 = self.parse("""
        v10[i64|2] = vec_box(2)
        v20[i64|2] = vec_int_pack(v10[i64|2], i0, 0, 1)
        v30[i64|2] = vec_int_pack(v20[i64|2], i1, 1, 1)
        v40[i64|2] = vec_int_expand(73,2)
        #
        v50[i64|2] = vec_int_add(v30[i64|2], v40[i64|2])
        """, False)
        self.assert_equal(loop2, loop3)

        loop1 = self.parse("""
        f10 = float_add(f0, 73.0)
        f11 = float_add(f1, 73.0)
        """)
        pack1 = self.pack(loop1, 0, 2, F64, F64)
        loop2 = self.schedule(loop1, [pack1], prepend_invariant=True)
        loop3 = self.parse("""
        v10[f64|2] = vec_box(2)
        v20[f64|2] = vec_float_pack(v10[f64|2], f0, 0, 1)
        v30[f64|2] = vec_float_pack(v20[f64|2], f1, 1, 1)
        v40[f64|2] = vec_float_expand(73.0,2)
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
        pack1 = self.pack(loop1, 0, 2, F64, F64)
        pack2 = self.pack(loop1, 2, 4, F64, F64)
        loop2 = self.schedule(loop1, [pack1, pack2], prepend_invariant=True)
        loop3 = self.parse("""
        v10[f64|2] = vec_box(2)
        v20[f64|2] = vec_float_pack(v10[f64|2], f0, 0, 1)
        v30[f64|2] = vec_float_pack(v20[f64|2], f1, 1, 1)
        v40[f64|2] = vec_float_expand(f5,2) # only expaned once
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

    def test_signext_int32(self):
        loop1 = self.parse("""
        i10 = int_signext(i1, 4)
        i11 = int_signext(i1, 4)
        """, additional_args=['v10[i64|2]'])
        pack1 = self.pack(loop1, 0, 2, I64, I32_2)
        var = self.find_input_arg('v10', loop1)
        def i1inv103204(v):
            return 0, var
        loop2 = self.schedule(loop1, [pack1], prepend_invariant=True,
                              overwrite_funcs = {
                                'getvector_of_box': i1inv103204,
                              })
        loop3 = self.parse("""
        v11[i32|2] = vec_int_signext(v10[i64|2], 4)
        """, False, additional_args=['v10[i64|2]'])
        self.assert_equal(loop2, loop3)

    def test_cast_float_to_int(self):
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
        i24 = int_signext(i16, 2)
        i25 = int_signext(i17, 2)
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
        pack1 = self.pack(loop1, 0, 8, None, F64)
        pack2 = self.pack(loop1, 8, 16, F64, I32_2)
        I16_2 = PackType('i',2,True,2)
        pack3 = self.pack(loop1, 16, 24, I32_2, I16_2)
        pack4 = self.pack(loop1, 24, 32, I16, None)
        def void(b,c):
            pass
        loop2 = self.schedule(loop1, [pack1,pack2,pack3,pack4],
                              overwrite_funcs={
                                  '_prevent_signext': void
                              })
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
        v24[i16|8] = vec_int_pack(v23[i16|6], v21[i16|2], 6, 2)
        vec_raw_store(p1, i1, v24[i16|8], descr=short)
        """, False)
        self.assert_equal(loop2, loop3)

    def test_cast_float_to_single_float(self):
        loop1 = self.parse("""
        f10 = raw_load(p0, i1, descr=double)
        f11 = raw_load(p0, i2, descr=double)
        f12 = raw_load(p0, i3, descr=double)
        f13 = raw_load(p0, i4, descr=double)
        #
        i10 = cast_float_to_singlefloat(f10)
        i11 = cast_float_to_singlefloat(f11)
        i12 = cast_float_to_singlefloat(f12)
        i13 = cast_float_to_singlefloat(f13)
        #
        raw_store(p1, i1, i10, descr=float)
        raw_store(p1, i2, i11, descr=float)
        raw_store(p1, i3, i12, descr=float)
        raw_store(p1, i4, i13, descr=float)
        """)
        pack1 = self.pack(loop1, 0, 4, None, F64)
        pack2 = self.pack(loop1, 4, 8, F64, I32_2)
        pack3 = self.pack(loop1, 8, 12, I32, None)
        loop2 = self.schedule(loop1, [pack1,pack2,pack3])
        loop3 = self.parse("""
        v44[f64|2] = vec_raw_load(p0, i1, 2, descr=double) 
        v45[f64|2] = vec_raw_load(p0, i3, 2, descr=double) 
        v46[i32|2] = vec_cast_float_to_singlefloat(v44[f64|2]) 
        v47[i32|2] = vec_cast_float_to_singlefloat(v45[f64|2]) 
        v41[i32|4] = vec_int_pack(v46[i32|2], v47[i32|2], 2, 2) 
        vec_raw_store(p1, i1, v41[i32|4], descr=float)
        """, False)
        self.assert_equal(loop2, loop3)

    def test_all(self):
        loop1 = self.parse("""
        i10 = raw_load(p0, i1, descr=long)
        i11 = raw_load(p0, i2, descr=long)
        #
        i12 = int_and(i10, 255)
        i13 = int_and(i11, 255)
        #
        guard_true(i12) []
        guard_true(i13) []
        """)
        pack1 = self.pack(loop1, 0, 2, None, I64)
        pack2 = self.pack(loop1, 2, 4, I64, I64)
        pack3 = self.pack(loop1, 4, 6, I64, None)
        loop2 = self.schedule(loop1, [pack1,pack2,pack3], prepend_invariant=True)
        loop3 = self.parse("""
        v9[i64|2] = vec_int_expand(255,2)
        v10[i64|2] = vec_raw_load(p0, i1, 2, descr=long)
        v11[i64|2] = vec_int_and(v10[i64|2], v9[i64|2])
        guard_true(v11[i64|2]) []
        """, False)
        self.assert_equal(loop2, loop3)


    def test_split_load_store(self):
        loop1 = self.parse("""
        i10 = raw_load(p0, i1, descr=float)
        i11 = raw_load(p0, i2, descr=float)
        raw_store(p0, i3, i10, descr=float)
        raw_store(p0, i4, i11, descr=float)
        """)
        pack1 = self.pack(loop1, 0, 2, None, I32_2)
        pack2 = self.pack(loop1, 2, 4, I32_2, None)
        loop2 = self.schedule(loop1, [pack1,pack2], prepend_invariant=True)
        loop3 = self.parse("""
        v1[i32|2] = vec_raw_load(p0, i1, 2, descr=float)
        i10 = vec_int_unpack(v1[i32|2], 0, 1)
        raw_store(p0, i3, i10, descr=float)
        i11 = vec_int_unpack(v1[i32|2], 1, 1)
        raw_store(p0, i4, i11, descr=float)
        """, False)
        # unfortunate ui32 is the type for float32... the unsigned u is for
        # the tests
        self.assert_equal(loop2, loop3)

    def test_split_arith(self):
        loop1 = self.parse("""
        i10 = int_and(255, i1)
        i11 = int_and(255, i1)
        """)
        pack1 = self.pack(loop1, 0, 2, I64, I64)
        loop2 = self.schedule(loop1, [pack1], prepend_invariant=True)
        loop3 = self.parse("""
        v1[i64|2] = vec_int_expand(255,2)
        v2[i64|2] = vec_int_expand(i1,2)
        v3[i64|2] = vec_int_and(v1[i64|2], v2[i64|2])
        """, False)
        self.assert_equal(loop2, loop3)

    def test_split_arith(self):
        loop1 = self.parse("""
        i10 = int_and(255, i1)
        i11 = int_and(255, i1)
        """)
        pack1 = self.pack(loop1, 0, 2, I64, I64)
        loop2 = self.schedule(loop1, [pack1], prepend_invariant=True)
        loop3 = self.parse("""
        v1[i64|2] = vec_int_expand(255, 2)
        v2[i64|2] = vec_int_expand(i1, 2)
        v3[i64|2] = vec_int_and(v1[i64|2], v2[i64|2])
        """, False)
        self.assert_equal(loop2, loop3)

    def test_no_vec_impl(self):
        loop1 = self.parse("""
        i10 = int_and(255, i1)
        i11 = int_and(255, i2)
        i12 = uint_floordiv(i10,1)
        i13 = uint_floordiv(i11,1)
        i14 = int_and(i1, i12)
        i15 = int_and(i2, i13)
        """)
        pack1 = self.pack(loop1, 0, 2, I64, I64)
        pack4 = self.pack(loop1, 4, 6, I64, I64)
        loop2 = self.schedule(loop1, [pack1,pack4], prepend_invariant=True)
        loop3 = self.parse("""
        v1[i64|2] = vec_int_expand(255,2)
        v2[i64|2] = vec_box(2)
        v3[i64|2] = vec_int_pack(v2[i64|2], i1, 0, 1)
        v4[i64|2] = vec_int_pack(v3[i64|2], i2, 1, 1)
        v5[i64|2] = vec_int_and(v1[i64|2], v4[i64|2])
        i10 = vec_int_unpack(v5[i64|2], 0, 1)
        i12 = uint_floordiv(i10,1)
        i11 = vec_int_unpack(v5[i64|2], 1, 1)
        i13 = uint_floordiv(i11,1)
        v6[i64|2] = vec_box(2)
        v7[i64|2] = vec_int_pack(v6[i64|2], i12, 0, 1)
        v8[i64|2] = vec_int_pack(v7[i64|2], i13, 1, 1)
        v9[i64|2] = vec_int_and(v4[i64|2], v8[i64|2])
        """, False)
        self.assert_equal(loop2, loop3)
