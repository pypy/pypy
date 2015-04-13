import py
import pytest

from rpython.rlib.objectmodel import instantiate
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, FakeMetaInterpStaticData, convert_old_style_to_targets)
from rpython.jit.metainterp.optimizeopt.test.test_dependency import DependencyBaseTest
from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt import optimize_trace
import rpython.jit.metainterp.optimizeopt.optimizer as optimizeopt
import rpython.jit.metainterp.optimizeopt.virtualize as virtualize
from rpython.jit.metainterp.optimizeopt.dependency import DependencyGraph
from rpython.jit.metainterp.optimizeopt.unroll import Inliner
from rpython.jit.metainterp.optimizeopt.vectorize import (VectorizingOptimizer, MemoryRef,
        isomorphic, Pair, NotAVectorizeableLoop)
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.history import ConstInt, BoxInt, get_const_ptr_for_string
from rpython.jit.metainterp import executor, compile, resume
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.rlib.rarithmetic import LONG_BIT

class FakeJitDriverStaticData(object):
    vectorize=True

class VecTestHelper(DependencyBaseTest):

    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unfold"

    jitdriver_sd = FakeJitDriverStaticData()

    def parse_loop(self, ops):
        loop = self.parse(ops, postprocess=self.postprocess)
        token = JitCellToken()
        loop.operations = \
            [ResOperation(rop.LABEL, loop.inputargs, None, descr=TargetToken(token))] + \
            loop.operations
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        return loop

    def assert_vectorize(self, loop, expected_loop, call_pure_results=None):
        self._do_optimize_loop(loop, call_pure_results, export_state=True)
        self.assert_equal(loop, expected_loop)

    def vectoroptimizer(self, loop):
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        jitdriver_sd = FakeJitDriverStaticData()
        opt = VectorizingOptimizer(metainterp_sd, jitdriver_sd, loop, [])
        return opt

    def vectoroptimizer_unrolled(self, loop, unroll_factor = -1):
        opt = self.vectoroptimizer(loop)
        opt.linear_find_smallest_type(loop)
        if unroll_factor == -1 and opt.smallest_type_bytes == 0:
            raise NotAVectorizeableLoop()
        if unroll_factor == -1:
            unroll_factor = opt.get_unroll_count()
        opt.unroll_loop_iterations(loop, unroll_factor)
        opt.loop.operations = opt.get_newoperations()
        opt.clear_newoperations()
        opt.build_dependency_graph()
        self.last_graph = opt.dependency_graph
        self._write_dot_and_convert_to_svg(self.last_graph, self.test_name)
        return opt

    def init_packset(self, loop, unroll_factor = -1):
        opt = self.vectoroptimizer_unrolled(loop, unroll_factor)
        opt.find_adjacent_memory_refs()
        return opt

    def extend_packset(self, loop, unroll_factor = -1):
        opt = self.vectoroptimizer_unrolled(loop, unroll_factor)
        opt.find_adjacent_memory_refs()
        opt.extend_packset()
        return opt

    def combine_packset(self, loop, unroll_factor = -1):
        opt = self.vectoroptimizer_unrolled(loop, unroll_factor)
        opt.find_adjacent_memory_refs()
        opt.extend_packset()
        opt.combine_packset()
        return opt

    def schedule(self, loop, unroll_factor = -1):
        opt = self.vectoroptimizer_unrolled(loop, unroll_factor)
        opt.find_adjacent_memory_refs()
        opt.extend_packset()
        opt.combine_packset()
        opt.schedule()
        return opt

    def assert_unroll_loop_equals(self, loop, expected_loop, \
                     unroll_factor = -1):
        vectoroptimizer = self.vectoroptimizer_unrolled(loop, unroll_factor)
        self.assert_equal(loop, expected_loop)

    def assert_pack(self, pack, indices):
        assert len(pack.operations) == len(indices)
        for op,i in zip(pack.operations, indices):
            assert op.opidx == i

    def assert_has_pack_with(self, packset, opindices):
        for pack in packset.packs:
            for op,i in zip(pack.operations, opindices):
                if op.opidx != i:
                    break
            else:
                # found a pack that points to the specified operations
                break
        else:
            pytest.fail("could not find a packset that points to %s" % str(opindices))

    def assert_packset_empty(self, packset, instr_count, exceptions):
        for a,b in exceptions:
            self.assert_packset_contains_pair(packset, a, b)
        import itertools
        combintations = set(itertools.product(range(instr_count),
                                              range(instr_count)))
        combintations -= set(exceptions)
        for a,b in combintations:
            self.assert_packset_not_contains_pair(packset, a, b)

    def assert_packset_not_contains_pair(self, packset, x, y):
        for pack in packset.packs:
            if pack.left.opidx == x and \
               pack.right.opidx == y:
                pytest.fail("must not find packset with indices {x},{y}" \
                                .format(x=x,y=y))

    def assert_packset_contains_pair(self, packset, x, y):
        for pack in packset.packs:
            if isinstance(pack, Pair):
                if pack.left.opidx == x and \
                   pack.right.opidx == y:
                    break
        else:
            pytest.fail("can't find a pack set for indices {x},{y}" \
                            .format(x=x,y=y))
    def assert_has_memory_ref_at(self, idx):
        node = self.last_graph.nodes[idx]
        assert node in self.last_graph.memory_refs, \
            "operation %s at pos %d has no memory ref!" % \
                (node.getoperation(), node.getindex())

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
        guard_no_early_exit() []
        raw_load(p0,i0,descr=chararraydescr)
        jump(p0,i0)
        """
        opt_ops = """
        [p0,i0]
        guard_no_early_exit() []
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
        vopt = self.vectoroptimizer(self.parse_loop(ops))
        assert 0 == vopt.smallest_type_bytes
        assert 0 == vopt.get_unroll_count()

    def test_array_operation_indices_not_unrolled(self):
        ops = """
        [p0,i0]
        raw_load(p0,i0,descr=arraydescr2)
        jump(p0,i0)
        """
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        assert len(vopt.dependency_graph.memory_refs) == 1
        self.assert_has_memory_ref_at(1)

    def test_array_operation_indices_unrolled_1(self):
        ops = """
        [p0,i0]
        raw_load(p0,i0,descr=chararraydescr)
        jump(p0,i0)
        """
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),1)
        assert len(vopt.dependency_graph.memory_refs) == 2
        self.assert_has_memory_ref_at(1)
        self.assert_has_memory_ref_at(2)

    def test_array_operation_indices_unrolled_2(self):
        ops = """
        [p0,i0,i1]
        i3 = raw_load(p0,i0,descr=chararraydescr)
        i4 = raw_load(p0,i1,descr=chararraydescr)
        jump(p0,i3,i4)
        """
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.build_dependency_graph()
        assert len(vopt.dependency_graph.memory_refs) == 2
        self.assert_has_memory_ref_at(1)
        self.assert_has_memory_ref_at(2)
        #
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),1)
        assert len(vopt.dependency_graph.memory_refs) == 4
        for i in [1,2,3,4]:
            self.assert_has_memory_ref_at(i)
        #
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),3)
        assert len(vopt.dependency_graph.memory_refs) == 8
        for i in [1,2,3,4,5,6,7,8]:
            self.assert_has_memory_ref_at(i)

    def test_array_memory_ref_adjacent_1(self):
        ops = """
        [p0,i0]
        i3 = raw_load(p0,i0,descr=chararraydescr)
        i1 = int_add(i0,1)
        jump(p0,i1)
        """
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),1)
        self.assert_edges(vopt.dependency_graph,
                [ [1,2,3,5], [5], [3,4], [5], [5], [] ], {})

        vopt.find_adjacent_memory_refs()
        self.assert_has_memory_ref_at(1)
        self.assert_has_memory_ref_at(3)
        assert len(vopt.dependency_graph.memory_refs) == 2

        mref1 = self.getmemref(1)
        mref3 = self.getmemref(3)
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
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref1 = self.getmemref(1)
        assert isinstance(mref1, MemoryRef)
        assert mref1.index_var.coefficient_mul == 1
        assert mref1.index_var.constant == 0

    def test_array_memory_ref_2(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0,1)
        i3 = raw_load(p0,i1,descr=chararraydescr)
        jump(p0,i1)
        """
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref1 = self.getmemref(2)
        assert isinstance(mref1, MemoryRef)
        assert mref1.index_var.coefficient_mul == 1
        assert mref1.index_var.constant == 1

    def test_array_memory_ref_sub_index(self):
        ops = """
        [p0,i0]
        i1 = int_sub(i0,1)
        i3 = raw_load(p0,i1,descr=chararraydescr)
        jump(p0,i1)
        """
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref1 = self.getmemref(2)
        assert isinstance(mref1, MemoryRef)
        assert mref1.index_var.coefficient_mul == 1
        assert mref1.index_var.constant == -1

    def test_array_memory_ref_add_mul_index(self):
        ops = """
        [p0,i0]
        i1 = int_add(i0,1)
        i2 = int_mul(i1,3)
        i3 = raw_load(p0,i2,descr=chararraydescr)
        jump(p0,i1)
        """
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref1 = self.getmemref(3)
        assert isinstance(mref1, MemoryRef)
        assert mref1.index_var.coefficient_mul == 3
        assert mref1.index_var.constant == 3

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
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref1 = self.getmemref(5)
        assert isinstance(mref1, MemoryRef)
        assert mref1.index_var.coefficient_mul == 18
        assert mref1.index_var.constant == 48

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
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref1 = self.getmemref(7)
        assert isinstance(mref1, MemoryRef)
        assert mref1.index_var.coefficient_mul == 1026
        assert mref1.index_var.coefficient_div == 1
        assert mref1.index_var.constant == 57*(30) + 57*6*(5) + 57*6*3*(1)

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
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref1 = self.getmemref(5)
        assert isinstance(mref1, MemoryRef)
        assert mref1.index_var.coefficient_mul == 6
        assert mref1.index_var.coefficient_div == 1
        assert mref1.index_var.constant == 0

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

        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),1)
        self.assert_edges(vopt.dependency_graph,
                [ [1,2,3,4,5,7,9], 
                    [9], [5,6], [9], [7,8],
                    [9],  [9], [9], [9], 
                  [],
                ], {})

        vopt.find_adjacent_memory_refs()

        for i in [1,3,5,7]:
            self.assert_has_memory_ref_at(i)
        assert len(vopt.dependency_graph.memory_refs) == 4

        mref1 = self.getmemref(1)
        mref3 = self.getmemref(3)
        mref5 = self.getmemref(5)
        mref7 = self.getmemref(7)
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
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref = self.getmemref(3)
        assert mref.index_var.coefficient_div == 16
        ops = """
        [p0,i0]
        i1 = int_add(i0,8)
        i2 = uint_floordiv(i1,2)
        i3 = raw_load(p0,i2,descr=chararraydescr)
        jump(p0,i2)
        """
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref = self.getmemref(3)
        assert mref.index_var.coefficient_div == 2
        assert mref.index_var.constant == 4
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
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref = self.getmemref(3)
        mref2 = self.getmemref(6)

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
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref = self.getmemref(3)
        mref2 = self.getmemref(7)

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
        vopt = self.vectoroptimizer_unrolled(self.parse_loop(ops),0)
        vopt.find_adjacent_memory_refs()
        mref = self.getmemref(3)
        mref2 = self.getmemref(7)

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
        vopt = self.vectoroptimizer_unrolled(loop,1)
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
        vopt = self.init_packset(loop,1)
        self.assert_independent(1,5)
        assert vopt.packset is not None
        assert len(vopt.dependency_graph.memory_refs) == 2
        assert len(vopt.packset.packs) == 1

    def test_packset_init_raw_load_not_adjacent_and_adjacent(self):
        ops = """
        [p0,i0]
        i3 = raw_load(p0, i0, descr=chararraydescr)
        jump(p0,i0)
        """
        loop = self.parse_loop(ops)
        vopt = self.init_packset(loop,3)
        assert len(vopt.dependency_graph.memory_refs) == 4
        assert len(vopt.packset.packs) == 0
        ops = """
        [p0,i0]
        i2 = int_add(i0,1)
        raw_load(p0, i2, descr=chararraydescr)
        jump(p0,i2)
        """
        loop = self.parse_loop(ops)
        vopt = self.init_packset(loop,3)
        assert len(vopt.dependency_graph.memory_refs) == 4
        assert len(vopt.packset.packs) == 3
        for i in range(3):
            x = (i+1)*2
            y = x + 2
            self.assert_independent(x,y)
            self.assert_packset_contains_pair(vopt.packset, x,y)

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
        vopt = self.init_packset(loop,15)
        assert len(vopt.dependency_graph.memory_refs) == 16
        assert len(vopt.packset.packs) == 15
        # assure that memory refs are not adjacent for all
        for i in range(15):
            for j in range(15):
                try:
                    if i-4 == j or i+4 == j:
                        mref1 = self.getmemref(i)
                        mref2 = self.getmemref(j)
                        assert mref1.is_adjacent_to(mref2)
                    else:
                        mref1 = self.getmemref(i)
                        mref2 = self.getmemref(j)
                        assert not mref1.is_adjacent_to(mref2)
                except KeyError:
                    pass
        for i in range(15):
            x = (i+1)*4
            y = x + 4
            self.assert_independent(x,y)
            self.assert_packset_contains_pair(vopt.packset, x, y)

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
        vopt = self.extend_packset(loop,1)
        assert len(vopt.dependency_graph.memory_refs) == 2
        self.assert_independent(5,10)
        assert len(vopt.packset.packs) == 2
        self.assert_packset_empty(vopt.packset, len(loop.operations),
                                  [(5,10), (4,9)])

    def test_packset_extend_load_modify_store(self):
        ops = """
        [p0,i0]
        guard_no_early_exit() []
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 16)
        guard_true(i2) [p0, i0]
        i3 = getarrayitem_gc(p0, i1, descr=chararraydescr)
        i4 = int_mul(i3, 2)
        setarrayitem_gc(p0, i1, i4, descr=chararraydescr)
        jump(p0,i1)
        """
        loop = self.parse_loop(ops)
        vopt = self.extend_packset(loop,1)
        assert len(vopt.dependency_graph.memory_refs) == 4
        self.assert_independent(5,11)
        self.assert_independent(6,12)
        self.assert_independent(7,13)
        assert len(vopt.packset.packs) == 3
        self.assert_packset_empty(vopt.packset, len(loop.operations),
                                  [(6,12), (5,11), (7,13)])

    @pytest.mark.parametrize("descr", ['char','float','int','singlefloat'])
    def test_packset_combine_simple(self,descr):
        ops = """
        [p0,i0]
        i3 = getarrayitem_gc(p0, i0, descr={descr}arraydescr)
        i1 = int_add(i0,1)
        jump(p0,i1)
        """.format(descr=descr)
        loop = self.parse_loop(ops)
        vopt = self.combine_packset(loop,3)
        assert len(vopt.dependency_graph.memory_refs) == 4
        assert len(vopt.packset.packs) == 1
        self.assert_pack(vopt.packset.packs[0], (1,3,5,7))
        ops = """
        [p0,i0]
        i3 = getarrayitem_raw(p0, i0, descr={descr}arraydescr)
        i1 = int_add(i0,1)
        jump(p0,i1)
        """.format(descr=descr)
        loop = self.parse_loop(ops)
        vopt = self.combine_packset(loop,3)
        assert len(vopt.dependency_graph.memory_refs) == 4
        assert len(vopt.packset.packs) == 1
        self.assert_pack(vopt.packset.packs[0], (1,3,5,7))

    @pytest.mark.parametrize("descr,stride",
            [('char',1),('float',8),('int',8),('singlefloat',4)])
    def test_packset_combine_2_loads_in_trace(self, descr, stride):
        ops = """
        [p0,i0]
        i3 = raw_load(p0, i0, descr={type}arraydescr)
        i1 = int_add(i0,{stride})
        i4 = raw_load(p0, i1, descr={type}arraydescr)
        i2 = int_add(i1,{stride})
        jump(p0,i2)
        """.format(type=descr,stride=stride)
        loop = self.parse_loop(ops)
        vopt = self.combine_packset(loop,3)
        assert len(vopt.dependency_graph.memory_refs) == 8
        assert len(vopt.packset.packs) == 1
        self.assert_pack(vopt.packset.packs[0], (1,3,5,7,9,11,13,15))

    def test_packset_combine_2_loads_one_redundant(self):
        ops = """
        [p0,i0]
        i3 = getarrayitem_gc(p0, i0, descr=floatarraydescr)
        i1 = int_add(i0,1)
        i4 = getarrayitem_gc(p0, i1, descr=floatarraydescr)
        jump(p0,i1)
        """
        pytest.skip("loop unrolling must apply redundant loop unrolling")
        loop = self.parse_loop(ops)
        vopt = self.combine_packset(loop,3)
        assert len(vopt.dependency_graph.memory_refs) == 4
        assert len(vopt.packset.packs) == 1
        self.assert_pack(vopt.packset.packs[0], (1,3,5,7))

    def test_packset_combine_no_candidates_packset_empty(self):
        ops = """
        []
        jump()
        """
        try:
            self.combine_packset(self.parse_loop(ops),15)
            pytest.fail("combine should raise an exception if no pack "
                        "statements are present")
        except NotAVectorizeableLoop:
            pass

        ops = """
        [p0,i0]
        i3 = getarrayitem_gc(p0, i0, descr=floatarraydescr)
        jump(p0,i3)
        """
        try:
            loop = self.parse_loop(ops)
            self.combine_packset(loop,15)
        except NotAVectorizeableLoop:
            pass

    @pytest.mark.parametrize("op,descr,stride",
            [('int_add','char',1),
             ('int_sub','char',1),
             ('int_mul','char',1),
             ('float_add','float',8),
             ('float_sub','float',8),
             ('float_mul','float',8),
             ('float_add','singlefloat',4),
             ('float_sub','singlefloat',4),
             ('float_mul','singlefloat',4),
             ('int_add','int',8),
             ('int_sub','int',8),
             ('int_mul','int',8),
            ])
    def test_packset_vector_operation(self, op, descr, stride):
        ops = """
        [p0,p1,p2,i0]
        i1 = int_add(i0, {stride})
        i10 = int_le(i1, 128)
        guard_true(i10) []
        i2 = raw_load(p0, i0, descr={descr}arraydescr)
        i3 = raw_load(p1, i0, descr={descr}arraydescr)
        i4 = {op}(i2,i3)
        raw_store(p2, i0, i4, descr={descr}arraydescr)
        jump(p0,p1,p2,i1)
        """.format(op=op,descr=descr,stride=stride)
        loop = self.parse_loop(ops)
        vopt = self.combine_packset(loop,3)
        assert len(vopt.dependency_graph.memory_refs) == 12
        assert len(vopt.packset.packs) == 4

        for opindices in [(4,11,18,25),(5,12,19,26),
                          (6,13,20,27),(7,14,21,28)]:
            self.assert_has_pack_with(vopt.packset, opindices)

    @pytest.mark.parametrize('op,descr,stride',
            [('int_add','char',1),
             ('int_sub','char',1),
             ('int_mul','char',1),
             ('float_add','float',8),
             ('float_sub','float',8),
             ('float_mul','float',8),
             ('float_add','singlefloat',4),
             ('float_sub','singlefloat',4),
             ('float_mul','singlefloat',4),
             ('int_add','int',8),
             ('int_sub','int',8),
             ('int_mul','int',8),
            ])
    def test_schedule_vector_operation(self, op, descr, stride):
        ops = """
        [p0,p1,p2,i0] # 0
        guard_no_early_exit() []
        i10 = int_le(i0, 128)  # 1, 8, 15, 22
        guard_true(i10) [p0,p1,p2,i0] # 2, 9, 16, 23
        i2 = getarrayitem_gc(p0, i0, descr={descr}arraydescr) # 3, 10, 17, 24
        i3 = getarrayitem_gc(p1, i0, descr={descr}arraydescr) # 4, 11, 18, 25
        i4 = {op}(i2,i3) # 5, 12, 19, 26
        setarrayitem_gc(p2, i0, i4, descr={descr}arraydescr) # 6, 13, 20, 27
        i1 = int_add(i0, {stride}) # 7, 14, 21, 28
        jump(p0,p1,p2,i1) # 29
        """.format(op=op,descr=descr,stride=1) # stride getarray is always 1
        vops = """
        [p0,p1,p2,i0]
        i10 = int_le(i0, 128)
        guard_true(i10) []
        i1 = int_add(i0, {stride})
        i11 = int_le(i1, 128)
        guard_true(i11) []
        i12 = int_add(i1, {stride})
        guard_no_early_exit() []
        v1 = vec_raw_load(p0, i0, 2, descr={descr}arraydescr)
        v2 = vec_raw_load(p1, i0, 2, descr={descr}arraydescr)
        v3 = {op}(v1,v2)
        vec_raw_store(p2, i0, v3, 2, descr={descr}arraydescr)
        jump(p0,p1,p2,i12)
        """.format(op='vec_'+op,descr=descr,stride=1)
        loop = self.parse_loop(ops)
        vopt = self.schedule(loop,1)
        self.assert_equal(loop, self.parse_loop(vops))

    @pytest.mark.parametrize('unroll', range(1,16,2))
    def test_vectorize_index_variable_combination(self, unroll):
        pytest.skip("implement index variable combination")
        ops = """
        [p0,i0]
        i1 = raw_load(p0, i0, descr=floatarraydescr)
        i2 = int_add(i0,1)
        jump(p0,i2)
        """
        vops = """
        [p0,i0]
        v1 = vec_raw_load(p0, i0, {count}, descr=floatarraydescr)
        i1 = int_add(i0,{count})
        jump(p0,i1)
        """.format(count=unroll+1)
        loop = self.parse_loop(ops)
        vopt = self.schedule(loop,unroll)
        self.assert_equal(loop, self.parse_loop(vops))


    def test_vectorize_raw_load_mul_index(self):
        pytest.skip("")
        ops = """
        [i0, i1, i2, i3, i4, i5, i6, i7]
        guard_no_early_exit() []
        i9 = int_mul(i0, 8)
        i10 = raw_load(i3, i9, descr=intarraydescr)
        i11 = int_mul(i0, 8)
        i12 = raw_load(i3, i11, descr=intarraydescr)
        i13 = int_add(i10, i12)
        i14 = int_mul(i0, 8)
        raw_store(i5, i14, i13, descr=intarraydescr)
        i16 = int_add(i0, 1)
        i17 = int_lt(i16, i7)
        guard_true(i17) [i7, i13, i5, i4, i3, i12, i10, i16]
        guard_future_condition() []
        jump(i16, i10, i12, i3, i4, i5, i13, i7)
        """
        vopt = self.schedule(self.parse_loop(ops),1)

    def test_vschedule_trace_1(self):
        ops = """
        [i0, i1, i2, i3, i4]
        guard_no_early_exit() []
        i6 = int_mul(i0, 8)
        i7 = raw_load(i2, i6, descr=intarraydescr)
        i8 = raw_load(i3, i6, descr=intarraydescr)
        i9 = int_add(i7, i8)
        raw_store(i4, i6, i9, descr=intarraydescr)
        i11 = int_add(i0, 1)
        i12 = int_lt(i11, i1)
        guard_true(i12) [i4, i3, i2, i1, i11]
        jump(i11, i1, i2, i3, i4)
        """
        opt="""
        [i0, i1, i2, i3, i4]
        i11 = int_add(i0, 1) 
        i12 = int_lt(i11, i1) 
        guard_true(i12) []
        i14 = int_mul(i11, 8) 
        i13 = int_add(i11, 1) 
        i18 = int_lt(i13, i1) 
        guard_true(i18) []
        guard_no_early_exit() []
        i6 = int_mul(i0, 8) 
        v19 = vec_raw_load(i2, i6, 2, descr=intarraydescr) 
        v20 = vec_raw_load(i3, i6, 2, descr=intarraydescr) 
        v21 = vec_int_add(v19, v20) 
        vec_raw_store(i4, i6, v21, 2, descr=intarraydescr) 
        jump(i13, i1, i2, i3, i4)
        """
        vopt = self.schedule(self.parse_loop(ops),1)
        self.assert_equal(vopt.loop, self.parse_loop(opt))

    def test_vschedule_trace_2(self):
        pytest.skip()
        ops = """
        [i0, i1, i2, i3, i4, i5, i6, i7]
        guard_no_early_exit() []
        i8 = raw_load(i3, i0, descr=intarraydescr)
        i9 = raw_load(i4, i0, descr=intarraydescr)
        i10 = int_add(i8, i9)
        raw_store(i5, i0, i10, descr=intarraydescr)
        i12 = int_add(i0, 8)
        i14 = int_mul(i7, 8)
        i15 = int_lt(i12, i14)
        guard_true(i15) [i7, i10, i5, i4, i3, i9, i8, i12]
        guard_future_condition() []
        jump(i12, i8, i9, i3, i4, i5, i10, i7)
        """
        opt = """
        [i0, i1, i2, i3, i4, i5, i6, i7]
        i12 = int_add(i0, 8) 
        i14 = int_mul(i7, 8) 
        i20 = int_mul(i7, 8) 
        i15 = int_lt(i12, i14) 
        guard_true(i15) []
        i16 = int_add(i12, 8) 
        i21 = int_lt(i16, i20) 
        guard_true(i21) []
        guard_no_early_exit() []
        v22 = vec_raw_load(i3, i0, 2, descr=intarraydescr) 
        v23 = vec_raw_load(i4, i0, 2, descr=intarraydescr) 
        v24 = vec_int_add(v22, v23) 
        vec_raw_store(i5, i0, v24, 2, descr=intarraydescr) 
        i17 = vec_unpack(v22, 0)
        i18 = vec_unpack(v22, 1)
        jump(i16, i17, i18, i3, i4, i5, i19, i7)
        """
        vopt = self.schedule(self.parse_loop(ops),1)
        self.assert_equal(vopt.loop, self.parse_loop(opt))

class TestLLtype(BaseTestVectorize, LLtypeMixin):
    pass
