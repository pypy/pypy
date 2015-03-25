import py
import pytest

from rpython.rlib.objectmodel import instantiate
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, BaseTest, FakeMetaInterpStaticData, convert_old_style_to_targets)
from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt import optimize_trace
import rpython.jit.metainterp.optimizeopt.optimizer as optimizeopt
import rpython.jit.metainterp.optimizeopt.virtualize as virtualize
from rpython.jit.metainterp.optimizeopt.dependency import DependencyGraph
from rpython.jit.metainterp.optimizeopt.unroll import Inliner
from rpython.jit.metainterp.optimizeopt.vectorize import VectorizingOptimizer, MemoryRef, isomorphic
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.history import ConstInt, BoxInt, get_const_ptr_for_string
from rpython.jit.metainterp import executor, compile, resume
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.rlib.rarithmetic import LONG_BIT

class FakeJitDriverStaticData(object):
    vectorize=True

class VecTestHelper(BaseTest):

    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unfold"


    jitdriver_sd = FakeJitDriverStaticData()

    def build_dependency(self, ops):
        loop = self.parse_loop(ops)
        return DependencyGraph(loop)

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
        opt = VectorizingOptimizer(metainterp_sd, jitdriver_sd, loop, [])
        return opt

    def vec_optimizer_unrolled(self, loop, unroll_factor = -1):
        opt = self.vec_optimizer(loop)
        opt._gather_trace_information(loop)
        if unroll_factor == -1:
            unroll_factor = opt.get_unroll_count()
        opt.unroll_loop_iterations(loop, unroll_factor)
        opt.loop.operations = opt.get_newoperations()
        return opt

    def init_pack_set(self, loop, unroll_factor = -1):
        opt = self.vec_optimizer_unrolled(loop, unroll_factor)
        opt.build_dependency_graph()
        opt.find_adjacent_memory_refs()
        return opt

    def extend_pack_set(self, loop, unroll_factor = -1):
        opt = self.vec_optimizer_unrolled(loop, unroll_factor)
        opt.build_dependency_graph()
        opt.find_adjacent_memory_refs()
        opt.extend_pack_set()
        return opt

    def assert_unroll_loop_equals(self, loop, expected_loop, \
                     unroll_factor = -1):
        vec_optimizer = self.vec_optimizer_unrolled(loop, unroll_factor)
        self.assert_equal(loop, expected_loop)


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

    def assert_packset_empty(self, packset, instr_count, exceptions):

        for a,b in exceptions:
            self.assert_packset_contains(packset, a, b)
        import itertools
        combintations = set(itertools.product(range(instr_count),
                                              range(instr_count)))
        combintations -= set([(5,10),(4,9)])
        for a,b in combintations:
            self.assert_packset_not_contains(packset, a, b)

    def assert_packset_not_contains(self, packset, x, y):
        for pack in packset.packs:
            if pack.left.opidx == x and \
               pack.right.opidx == y:
                pytest.fail("must not find packset with indices {x},{y}" \
                                .format(x=x,y=y))

    def assert_packset_contains(self, packset, x, y):
        for pack in packset.packs:
            if pack.left.opidx == x and \
               pack.right.opidx == y:
                break
        else:
            pytest.fail("can't find a pack set for indices {x},{y}" \
                            .format(x=x,y=y))

    def assert_edges(self, graph, edge_list):
        """ Check if all dependencies are met. for complex cases
        adding None instead of a list of integers skips the test.
        This checks both if a dependency forward and backward exists.
        """
        assert len(edge_list) == len(graph.adjacent_list)
        for idx,edges in enumerate(edge_list):
            if edges is None:
                continue
            dependencies = graph.adjacent_list[idx][:]
            for edge in edges:
                dependency = graph.instr_dependency(idx,edge)
                if edge < idx:
                    dependency = graph.instr_dependency(edge, idx)
                assert dependency is not None, \
                   " it is expected that instruction at index" + \
                   " %d depends on instr on index %d but it does not.\n%s" \
                        % (idx, edge, graph)
                dependencies.remove(dependency)
            assert dependencies == [], \
                    "dependencies unexpected %s.\n%s" \
                    % (dependencies,graph)

class BaseTestVectorize(VecTestHelper):

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
        self.assert_unroll_loop_equals(self.parse_loop(ops), self.parse_loop(opt_ops), 1)

    def test_estimate_unroll_factor_smallest_byte_zero(self):
        ops = """
        [p0,i0]
        raw_load(p0,i0,descr=arraydescr2)
        jump(p0,i0)
        """
        vopt = self.vec_optimizer(self.parse_loop(ops))
        assert 0 == vopt.vec_info.smallest_type_bytes
        assert 0 == vopt.get_unroll_count()

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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
        assert 1 in vopt.vec_info.memory_refs
        assert 2 in vopt.vec_info.memory_refs
        assert len(vopt.vec_info.memory_refs) == 2
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        for i in [1,2,3,4]:
            assert i in vopt.vec_info.memory_refs
        assert len(vopt.vec_info.memory_refs) == 4
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),3)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        self.assert_edges(vopt.dependency_graph,
                [ [1,2,3,5], [0], [0,3,4], [0,2], [2,5], [0,4] ])

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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
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
        ops2 = """
        [p0,i0,i4]
        i3 = raw_load(p0,i0,descr=chararraydescr)
        i1 = int_add(i0,1)
        i5 = raw_load(p0,i4,descr=chararraydescr)
        i6 = int_add(i4,1)
        i3 = raw_load(p0,i1,descr=chararraydescr)
        i8 = int_add(i1,1)
        i9 = raw_load(p0,i6,descr=chararraydescr)
        i7 = int_add(i6,1)
        jump(p0,i8,i7)
        """

        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),1)
        vopt.build_dependency_graph()
        self.assert_edges(vopt.dependency_graph,
                [ [1,2,3,4,5,7,9], 
                    [0], [0,5,6], [0], [0,7,8],
                    [0,2],  [2,9], [0,4], [4,9], 
                  [0,6,8],
                ])

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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
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
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref = vopt.vec_info.memory_refs[3]
        mref2 = vopt.vec_info.memory_refs[7]

        self.assert_memory_ref_not_adjacent(mref, mref2)
        assert mref == mref2

    def test_array_memory_ref_diff_not_equal(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0,4)
        i2 = int_floordiv(i1,2)
        i3 = raw_load(p0,i2,descr=chararraydescr)
        i4 = int_add(i0,2)
        i5 = int_mul(i4,2)
        i6 = int_add(i5,4)
        i7 = raw_load(p0,i6,descr=chararraydescr)
        jump(p0,i2)
        """
        vopt = self.vec_optimizer_unrolled(self.parse_loop(ops),0)
        vopt.build_dependency_graph()
        vopt.find_adjacent_memory_refs()
        mref = vopt.vec_info.memory_refs[3]
        mref2 = vopt.vec_info.memory_refs[7]

        self.assert_memory_ref_not_adjacent(mref, mref2)
        assert mref != mref2

    def test_do_not_unroll_debug_merge_point(self):
        ops = """
        []
        debug_merge_point(0, 0, 'loc 1')
        debug_merge_point(0, 0, 'loc 1')
        jump()
        """
        loop = self.parse_loop(ops)
        vopt = self.vec_optimizer_unrolled(loop,1)
        self.assert_equal(loop, self.parse_loop(ops))

    def test_packset_init_simple(self):
        ops = """
        [p0,i0]
        i3 = getarrayitem_gc(p0, i0, descr=chararraydescr)
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 16)
        guard_true(i2) [p0, i0]
        jump(p0,i1)
        """
        loop = self.parse_loop(ops)
        vopt = self.init_pack_set(loop,1)
        assert vopt.dependency_graph.independant(1,5)
        assert vopt.pack_set is not None
        assert len(vopt.vec_info.memory_refs) == 2
        assert len(vopt.pack_set.packs) == 1

    def test_packset_init_raw_load_not_adjacent_and_adjacent(self):
        ops = """
        [p0,i0]
        i3 = raw_load(p0, i0, descr=floatarraydescr)
        jump(p0,i0)
        """
        loop = self.parse_loop(ops)
        vopt = self.init_pack_set(loop,3)
        assert len(vopt.vec_info.memory_refs) == 4
        assert len(vopt.pack_set.packs) == 0
        ops = """
        [p0,i0]
        i2 = int_add(i0,1)
        raw_load(p0, i2, descr=floatarraydescr)
        jump(p0,i2)
        """
        loop = self.parse_loop(ops)
        vopt = self.init_pack_set(loop,3)
        assert len(vopt.vec_info.memory_refs) == 4
        assert len(vopt.pack_set.packs) == 3
        for i in range(3):
            x = (i+1)*2
            y = x + 2
            assert vopt.dependency_graph.independant(x,y)
            self.assert_packset_contains(vopt.pack_set, x,y)

    def test_packset_init_2(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 16)
        guard_true(i2) [p0, i0]
        i3 = getarrayitem_gc(p0, i1, descr=chararraydescr)
        jump(p0,i1)
        """
        loop = self.parse_loop(ops)
        vopt = self.init_pack_set(loop,15)
        assert len(vopt.vec_info.memory_refs) == 16
        assert len(vopt.pack_set.packs) == 15
        # assure that memory refs are not adjacent for all
        for i in range(15):
            for j in range(15):
                try:
                    if i-4 == j or i+4 == j:
                        mref1 = vopt.vec_info.memory_refs[i]
                        mref2 = vopt.vec_info.memory_refs[j]
                        assert mref1.is_adjacent_to(mref2)
                    else:
                        mref1 = vopt.vec_info.memory_refs[i]
                        mref2 = vopt.vec_info.memory_refs[j]
                        assert not mref1.is_adjacent_to(mref2)
                except KeyError:
                    pass
        for i in range(15):
            x = (i+1)*4
            y = x + 4
            assert vopt.dependency_graph.independant(x,y)
            self.assert_packset_contains(vopt.pack_set, x, y)

    def test_isomorphic_operations(self):
        ops_src = """
        [p1,p0,i0]
        i3 = getarrayitem_gc(p0, i0, descr=chararraydescr)
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 16)
        i4 = getarrayitem_gc(p0, i1, descr=chararraydescr)
        i5 = getarrayitem_gc(p1, i1, descr=floatarraydescr)
        i6 = getarrayitem_gc(p0, i1, descr=floatarraydescr)
        guard_true(i2) [p0, i0]
        jump(p1,p0,i1)
        """
        loop = self.parse_loop(ops_src)
        ops = loop.operations
        assert isomorphic(ops[1], ops[4])
        assert not isomorphic(ops[0], ops[1])
        assert not isomorphic(ops[0], ops[5])
        # TODO strong assumptions do hold here?
        #assert not isomorphic(ops[4], ops[5])
        #assert not isomorphic(ops[5], ops[6])
        #assert not isomorphic(ops[4], ops[6])
        #assert not isomorphic(ops[1], ops[6])

    def test_packset_extend_simple(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 16)
        guard_true(i2) [p0, i0]
        i3 = getarrayitem_gc(p0, i1, descr=chararraydescr)
        i4 = int_add(i3, 1)
        jump(p0,i1)
        """
        loop = self.parse_loop(ops)
        vopt = self.extend_pack_set(loop,1)
        self.debug_print_operations(loop)
        assert len(vopt.vec_info.memory_refs) == 2
        assert vopt.dependency_graph.independant(5,10) == True
        assert len(vopt.pack_set.packs) == 2
        self.assert_packset_empty(vopt.pack_set, len(loop.operations),
                                  [(5,10), (4,9)])

class TestLLtype(BaseTestVectorize, LLtypeMixin):
    pass
