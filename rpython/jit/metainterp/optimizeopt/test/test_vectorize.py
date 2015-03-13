import py
from rpython.rlib.objectmodel import instantiate
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, BaseTest, FakeMetaInterpStaticData, convert_old_style_to_targets)
from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt import optimize_trace
import rpython.jit.metainterp.optimizeopt.optimizer as optimizeopt
import rpython.jit.metainterp.optimizeopt.virtualize as virtualize
from rpython.jit.metainterp.optimizeopt.dependency import DependencyGraph
from rpython.jit.metainterp.optimizeopt.unroll import Inliner
from rpython.jit.metainterp.optimizeopt.vectorize import OptVectorize, MemoryRef
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.history import ConstInt, BoxInt, get_const_ptr_for_string
from rpython.jit.metainterp import executor, compile, resume
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.rlib.rarithmetic import LONG_BIT

class FakeJitDriverStaticData(object):
    vectorize=True

class DepTestHelper(BaseTest):

    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unfold"


    jitdriver_sd = FakeJitDriverStaticData()

    def build_dependency(self, ops):
        loop = self.parse_loop(ops)
        return DependencyGraph(None, loop)

    def parse_loop(self, ops):
        loop = self.parse(ops, postprocess=self.postprocess)
        token = JitCellToken()
        loop.operations = [ResOperation(rop.LABEL, loop.inputargs, None, 
                                   descr=TargetToken(token))] + loop.operations
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        return loop

    def assert_vectorize(self, loop, expected_loop, call_pure_results=None):
        self._do_optimize_loop(loop, call_pure_results, export_state=True)
        self.assert_equal(loop, expected_loop)

    def vec_optimizer(self, loop):
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        jitdriver_sd = FakeJitDriverStaticData()
        opt = OptVectorize(metainterp_sd, jitdriver_sd, loop, [])
        return opt

    def vec_optimizer_unrolled(self, loop, unroll_factor = -1):
        opt = self.vec_optimizer(loop)
        opt._gather_trace_information(loop)
        if unroll_factor == -1:
            unroll_factor = opt.get_estimated_unroll_factor()
        opt.unroll_loop_iterations(loop, unroll_factor)
        return opt

    def assert_unroll_loop_equals(self, loop, expected_loop, \
                     unroll_factor = -1):
        vec_optimizer = self.vec_optimizer_unrolled(loop, unroll_factor)
        self.assert_equal(loop, expected_loop)

    def assert_no_edge(self, graph, f, t = -1):
        if type(f) == list:
            for _f,_t in f:
                self.assert_no_edge(graph, _f, _t)
        else:
            assert graph.instr_dependency(f, t) is None, \
                   " it is expected that instruction at index" + \
                   " %d DOES NOT depend on instr on index %d but it does" \
                        % (f, t)

    def assert_def_use(self, graph, from_instr_index, to_instr_index = -1):

        if type(from_instr_index) == list:
            for f,t in from_instr_index:
                self.assert_def_use(graph, f, t)
        else:
            assert graph.instr_dependency(from_instr_index,
                                          to_instr_index) is not None, \
                   " it is expected that instruction at index" + \
                   " %d depends on instr on index %d but it is not" \
                        % (from_instr_index, to_instr_index)

    def assert_memory_ref_adjacent(self, m1, m2):
        assert m1.is_adjacent_to(m2)
        assert m2.is_adjacent_to(m1)

    def assert_memory_ref_not_adjacent(self, m1, m2):
        assert not m1.is_adjacent_to(m2)
        assert not m2.is_adjacent_to(m1)

    def debug_print_operations(self, loop):
        print('--- loop instr numbered ---')
        for i,op in enumerate(loop.operations):
            print(i,op)

class BaseTestDependencyGraph(DepTestHelper):
    def test_dependency_1(self):
        ops = """
        []
        i1 = int_add(1,1)
        i2 = int_add(i1,1)
        guard_value(i2,3) []
        jump()
        """
        dep_graph = self.build_dependency(ops)
        self.assert_no_edge(dep_graph, [(i,i) for i in range(5)])
        self.assert_def_use(dep_graph, [(1,2),(2,3)])
        self.assert_no_edge(dep_graph, [(0,1), (1,3),
                                        (0,2), (0,3),
                                        (0,4), (1,3),
                                        (2,4), (3,4)
                                       ])

    def test_label_def_use_jump_use_def(self):
        ops = """
        [i3]
        i1 = int_add(i3,1)
        guard_value(i1,0) []
        jump(i1)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_no_edge(dep_graph, [(i,i) for i in range(4)])
        self.assert_def_use(dep_graph, 0, 1)
        self.assert_def_use(dep_graph, 1, 2)
        self.assert_def_use(dep_graph, 1, 3)

    def test_vectorize_skip_impossible_1(self):
        """ this trace does not contain a raw load / raw store from an array """
        ops = """
        [p0,i0]
        i1 = int_add(i0,1)
        i2 = int_le(i1, 10)
        guard_true(i2) []
        jump(p0,i1)
        """
        self.assert_vectorize(self.parse_loop(ops), self.parse_loop(ops))

    def test_unroll_empty_stays_empty(self):
        """ has no operations in this trace, thus it stays empty
        after unrolling it 2 times """
        ops = """
        []
        jump()
        """
        self.assert_unroll_loop_equals(self.parse_loop(ops), self.parse_loop(ops), 2)

    def test_unroll_empty_stays_empty_parameter(self):
        """ same as test_unroll_empty_stays_empty but with a parameter """
        ops = """
        [i0]
        jump(i0)
        """
        self.assert_unroll_loop_equals(self.parse_loop(ops), self.parse_loop(ops), 2)

    def test_vect_pointer_fails(self):
        """ it currently rejects pointer arrays """
        ops = """
        [p0,i0]
        raw_load(p0,i0,descr=arraydescr2)
        jump(p0,i0)
        """
        self.assert_vectorize(self.parse_loop(ops), self.parse_loop(ops))

    def test_vect_unroll_char(self):
        """ a 16 byte vector register can hold 16 bytes thus 
        it is unrolled 16 times. (it is the smallest type in the trace) """
        ops = """
        [p0,i0]
        raw_load(p0,i0,descr=chararraydescr)
        jump(p0,i0)
        """
        opt_ops = """
        [p0,i0]
        {}
        jump(p0,i0)
        """.format(('\n' + ' ' *8).join(['raw_load(p0,i0,descr=chararraydescr)'] * 16))
        self.assert_unroll_loop_equals(self.parse_loop(ops), self.parse_loop(opt_ops))

    def test_unroll_vector_addition(self):
        """ a more complex trace doing vector addition (smallest type is float 
        8 byte) """
        ops = """
        [p0,p1,p2,i0]
        i1 = raw_load(p1, i0, descr=floatarraydescr)
        i2 = raw_load(p2, i0, descr=floatarraydescr)
        i3 = int_add(i1,i2)
        raw_store(p0, i0, i3, descr=floatarraydescr)
        i4 = int_add(i0, 1)
        i5 = int_le(i4, 10)
        guard_true(i5) []
        jump(p0,p1,p2,i4)
        """
        opt_ops = """
        [p0,p1,p2,i0]
        i1 = raw_load(p1, i0, descr=floatarraydescr)
        i2 = raw_load(p2, i0, descr=floatarraydescr)
        i3 = int_add(i1,i2)
        raw_store(p0, i0, i3, descr=floatarraydescr)
        i4 = int_add(i0, 1)
        i5 = int_le(i4, 10)
        guard_true(i5) []
        i6 = raw_load(p1, i4, descr=floatarraydescr)
        i7 = raw_load(p2, i4, descr=floatarraydescr)
        i8 = int_add(i6,i7)
        raw_store(p0, i4, i8, descr=floatarraydescr)
        i9 = int_add(i4, 1)
        i10 = int_le(i9, 10)
        guard_true(i10) []
        jump(p0,p1,p2,i9)
        """
        self.assert_unroll_loop_equals(self.parse_loop(ops), self.parse_loop(opt_ops), 2)

    def test_estimate_unroll_factor_smallest_byte_zero(self):
        ops = """
        [p0,i0]
        raw_load(p0,i0,descr=arraydescr2)
        jump(p0,i0)
        """
        vopt = self.vec_optimizer(self.parse_loop(ops))
        assert 0 == vopt.vec_info.smallest_type_bytes
        assert 0 == vopt.get_estimated_unroll_factor()

    def test_array_operation_indices_not_unrolled(self):
        ops = """
        [p0,i0]
        raw_load(p0,i0,descr=arraydescr2)
        jump(p0,i0)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops))
        assert 1 in vopt.vec_info.memory_refs
        assert len(vopt.vec_info.memory_refs) == 1

    def test_array_operation_indices_unrolled_1(self):
        ops = """
        [p0,i0]
        raw_load(p0,i0,descr=chararraydescr)
        jump(p0,i0)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),2)
        assert 1 in vopt.vec_info.memory_refs
        assert 2 in vopt.vec_info.memory_refs
        assert len(vopt.vec_info.memory_refs) == 2

    def test_array_operation_indices_unrolled_2(self):
        ops = """
        [p0,i0,i1]
        i3 = raw_load(p0,i0,descr=chararraydescr)
        i4 = raw_load(p0,i1,descr=chararraydescr)
        jump(p0,i3,i4)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        assert 1 in vopt.vec_info.memory_refs
        assert 2 in vopt.vec_info.memory_refs
        assert len(vopt.vec_info.memory_refs) == 2
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),2)
        for i in [1,2,3,4]:
            assert i in vopt.vec_info.memory_refs
        assert len(vopt.vec_info.memory_refs) == 4
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),4)
        for i in [1,2,3,4,5,6,7,8]:
            assert i in vopt.vec_info.memory_refs
        assert len(vopt.vec_info.memory_refs) == 8

    def test_array_memory_ref_adjacent_1(self):
        ops = """
        [p0,i0]
        i3 = raw_load(p0,i0,descr=chararraydescr)
        i1 = int_add(i0,1)
        jump(p0,i1)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),2)
        vopt.build_dependency_graph()
        self.assert_no_edge(vopt.dependency_graph, [(i,i) for i in range(6)])
        self.assert_def_use(vopt.dependency_graph, [(0,1),(2,3),(4,5)])
        self.assert_no_edge(vopt.dependency_graph, [(0,4),(0,0)])

        vopt.find_adjacent_memory_refs()
        assert 1 in vopt.vec_info.memory_refs
        assert 3 in vopt.vec_info.memory_refs
        assert len(vopt.vec_info.memory_refs) == 2

        mref1 = vopt.vec_info.memory_refs[1]
        mref3 = vopt.vec_info.memory_refs[3]
        assert isinstance(mref1, MemoryRef)
        assert isinstance(mref3, MemoryRef)

        assert mref1.is_adjacent_to(mref3)
        assert mref3.is_adjacent_to(mref1)

    def test_array_memory_ref_1(self):
        ops = """
        [p0,i0]
        i3 = raw_load(p0,i0,descr=chararraydescr)
        jump(p0,i0)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref1 = vopt.vec_info.memory_refs[1]
        assert isinstance(mref1, MemoryRef)
        assert mref1.coefficient_mul == 1
        assert mref1.constant == 0

    def test_array_memory_ref_2(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0,1)
        i3 = raw_load(p0,i1,descr=chararraydescr)
        jump(p0,i1)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref1 = vopt.vec_info.memory_refs[2]
        assert isinstance(mref1, MemoryRef)
        assert mref1.coefficient_mul == 1
        assert mref1.constant == 1

    def test_array_memory_ref_sub_index(self):
        ops = """
        [p0,i0]
        i1 = int_sub(i0,1)
        i3 = raw_load(p0,i1,descr=chararraydescr)
        jump(p0,i1)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref1 = vopt.vec_info.memory_refs[2]
        assert isinstance(mref1, MemoryRef)
        assert mref1.coefficient_mul == 1
        assert mref1.constant == -1

    def test_array_memory_ref_add_mul_index(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0,1)
        i2 = int_mul(i1,3)
        i3 = raw_load(p0,i2,descr=chararraydescr)
        jump(p0,i1)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref1 = vopt.vec_info.memory_refs[3]
        assert isinstance(mref1, MemoryRef)
        assert mref1.coefficient_mul == 3
        assert mref1.constant == 3

    def test_array_memory_ref_add_mul_index_interleaved(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0,1)
        i2 = int_mul(i1,3)
        i3 = int_add(i2,5)
        i4 = int_mul(i3,6)
        i5 = raw_load(p0,i4,descr=chararraydescr)
        jump(p0,i4)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref1 = vopt.vec_info.memory_refs[5]
        assert isinstance(mref1, MemoryRef)
        assert mref1.coefficient_mul == 18
        assert mref1.constant == 48

        ops = """
        [p0,i0]
        i1 = int_add(i0,1)
        i2 = int_mul(i1,3)
        i3 = int_add(i2,5)
        i4 = int_mul(i3,6)
        i5 = int_add(i4,30)
        i6 = int_mul(i5,57)
        i7 = raw_load(p0,i6,descr=chararraydescr)
        jump(p0,i6)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref1 = vopt.vec_info.memory_refs[7]
        assert isinstance(mref1, MemoryRef)
        assert mref1.coefficient_mul == 1026
        assert mref1.coefficient_div == 1
        assert mref1.constant == 57*(30) + 57*6*(5) + 57*6*3*(1)

    def test_array_memory_ref_sub_mul_index_interleaved(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0,1)
        i2 = int_mul(i1,3)
        i3 = int_sub(i2,3)
        i4 = int_mul(i3,2)
        i5 = raw_load(p0,i4,descr=chararraydescr)
        jump(p0,i4)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref1 = vopt.vec_info.memory_refs[5]
        assert isinstance(mref1, MemoryRef)
        assert mref1.coefficient_mul == 6
        assert mref1.coefficient_div == 1
        assert mref1.constant == 0

    def test_array_memory_ref_not_adjacent_1(self):
        ops = """
        [p0,i0,i4]
        i3 = raw_load(p0,i0,descr=chararraydescr)
        i1 = int_add(i0,1)
        i5 = raw_load(p0,i4,descr=chararraydescr)
        i6 = int_add(i4,1)
        jump(p0,i1,i6)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),2)
        vopt.build_dependency_graph()
        self.assert_no_edge(vopt.dependency_graph, [(i,i) for i in range(6)])
        self.assert_def_use(vopt.dependency_graph, [(0,1),(0,2),(0,3),(0,4),(2,5)])
        self.assert_no_edge(vopt.dependency_graph, [(1,3),(2,4)])

        vopt.find_adjacent_memory_refs()

        for i in [1,3,5,7]:
            assert i in vopt.vec_info.memory_refs
        assert len(vopt.vec_info.memory_refs) == 4

        mref1 = vopt.vec_info.memory_refs[1]
        mref3 = vopt.vec_info.memory_refs[3]
        mref5 = vopt.vec_info.memory_refs[5]
        mref7 = vopt.vec_info.memory_refs[7]
        assert isinstance(mref1, MemoryRef)
        assert isinstance(mref3, MemoryRef)
        assert isinstance(mref5, MemoryRef)
        assert isinstance(mref7, MemoryRef)

        self.assert_memory_ref_adjacent(mref1, mref5)
        self.assert_memory_ref_not_adjacent(mref1, mref3)
        self.assert_memory_ref_not_adjacent(mref1, mref7)
        self.assert_memory_ref_adjacent(mref3, mref7)
        assert mref1.is_adjacent_after(mref5)

    def test_array_memory_ref_div(self):
        ops = """
        [p0,i0]
        i1 = int_floordiv(i0,2)
        i2 = int_floordiv(i1,8)
        i3 = raw_load(p0,i2,descr=chararraydescr)
        jump(p0,i2)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref = vopt.vec_info.memory_refs[3]
        assert mref.coefficient_div == 16
        ops = """
        [p0,i0]
        i1 = int_add(i0,8)
        i2 = uint_floordiv(i1,2)
        i3 = raw_load(p0,i2,descr=chararraydescr)
        jump(p0,i2)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref = vopt.vec_info.memory_refs[3]
        assert mref.coefficient_div == 2
        assert mref.constant == 4
        ops = """
        [p0,i0]
        i1 = int_add(i0,8)
        i2 = int_floordiv(i1,2)
        i3 = raw_load(p0,i2,descr=chararraydescr)
        i4 = int_add(i0,4)
        i5 = int_mul(i4,2)
        i6 = raw_load(p0,i5,descr=chararraydescr)
        jump(p0,i2)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref = vopt.vec_info.memory_refs[3]
        mref2 = vopt.vec_info.memory_refs[6]

        self.assert_memory_ref_not_adjacent(mref, mref2)
        assert mref != mref2

    def test_array_memory_ref_diff_calc_but_equal(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0,4)
        i2 = int_mul(i1,2)
        i3 = raw_load(p0,i2,descr=chararraydescr)
        i4 = int_add(i0,2)
        i5 = int_mul(i4,2)
        i6 = int_add(i5,4)
        i7 = raw_load(p0,i6,descr=chararraydescr)
        jump(p0,i2)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref = vopt.vec_info.memory_refs[3]
        mref2 = vopt.vec_info.memory_refs[7]

        self.assert_memory_ref_not_adjacent(mref, mref2)
        assert mref == mref2

    def test_array_memory_ref_diff_calc_but_equal(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0,4)
        i2 = int_floor(i1,2)
        i3 = raw_load(p0,i2,descr=chararraydescr)
        i4 = int_add(i0,2)
        i5 = int_mul(i4,2)
        i6 = int_add(i5,4)
        i7 = raw_load(p0,i6,descr=chararraydescr)
        jump(p0,i2)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref = vopt.vec_info.memory_refs[3]
        mref2 = vopt.vec_info.memory_refs[7]

        self.assert_memory_ref_not_adjacent(mref, mref2)
        assert mref == mref2


class TestLLtype(BaseTestDependencyGraph, LLtypeMixin):
    pass
