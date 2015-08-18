import py
import pytest

from rpython.rlib.objectmodel import instantiate
from rpython.jit.metainterp.optimizeopt.test.test_util import (LLtypeMixin,
        FakeMetaInterpStaticData, convert_old_style_to_targets,
        FakeWarmState)
from rpython.jit.metainterp.optimizeopt.test.test_dependency import DependencyBaseTest
from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt import optimize_trace
import rpython.jit.metainterp.optimizeopt.optimizer as optimizeopt
import rpython.jit.metainterp.optimizeopt.virtualize as virtualize
from rpython.jit.metainterp.optimizeopt.dependency import DependencyGraph
from rpython.jit.metainterp.optimizeopt.unroll import Inliner
from rpython.jit.metainterp.optimizeopt.vectorize import (VectorizingOptimizer, MemoryRef,
        isomorphic, Pair, NotAVectorizeableLoop, NotAProfitableLoop, GuardStrengthenOpt,
        CostModel)
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.history import ConstInt, BoxInt, get_const_ptr_for_string
from rpython.jit.metainterp import executor, compile, resume
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.rlib.rarithmetic import LONG_BIT

class FakeJitDriverStaticData(object):
    vec=True

class FakeCostModel(CostModel):
    def __init__(self):
        CostModel.__init__(self, 0, 16)
    def record_cast_int(self): pass
    def record_pack_savings(self, pack, times): pass
    def record_vector_pack(self, box, index, count): pass
    def record_vector_unpack(self, box, index, count): pass
    def unpack_cost(self, op, index, count): pass
    def savings_for_pack(self, pack, times): pass
    def profitable(self):
        return True

ARCH_VEC_REG_SIZE = 16

class VecTestHelper(DependencyBaseTest):

    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap"

    jitdriver_sd = FakeJitDriverStaticData()

    def parse_loop(self, ops, add_label=True):
        loop = self.parse(ops, postprocess=self.postprocess)
        token = JitCellToken()
        pre = []
        tt = TargetToken(token)
        if add_label:
            pre = [ResOperation(rop.LABEL, loop.inputargs, None, descr=tt)]
        else:
            for i,op in enumerate(loop.operations):
                if op.getopnum() == rop.LABEL:
                    op.setdescr(tt)
        loop.operations = pre + loop.operations
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        for op in loop.operations:
            if op.getopnum() == rop.GUARD_EARLY_EXIT and op.getdescr() is None:
                op.setdescr(compile.ResumeAtLoopHeaderDescr())
        return loop

    def assert_vectorize(self, loop, expected_loop, call_pure_results=None):
        self._do_optimize_loop(loop, call_pure_results, export_state=True)
        self.assert_equal(loop, expected_loop)

    def vectoroptimizer(self, loop):
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        jitdriver_sd = FakeJitDriverStaticData()
        opt = VectorizingOptimizer(metainterp_sd, jitdriver_sd, loop, 0)
        label_index = loop.find_first_index(rop.LABEL)
        opt.orig_label_args = loop.operations[label_index].getarglist()[:]
        return opt

    def vectoroptimizer_unrolled(self, loop, unroll_factor = -1):
        opt = self.vectoroptimizer(loop)
        opt.linear_find_smallest_type(loop)
        if unroll_factor == -1 and opt.smallest_type_bytes == 0:
            raise NotAVectorizeableLoop()
        if unroll_factor == -1:
            unroll_factor = opt.get_unroll_count(ARCH_VEC_REG_SIZE)
            print ""
            print "unroll factor: ", unroll_factor, opt.smallest_type_bytes
        if opt.loop.find_first_index(rop.GUARD_EARLY_EXIT) == -1:
            idx = loop.find_first_index(rop.LABEL)
            guard = ResOperation(rop.GUARD_EARLY_EXIT, [], None)
            guard.setfailargs([])
            guard.setdescr(compile.ResumeAtLoopHeaderDescr())
            loop.operations.insert(idx+1, guard)
        self.show_dot_graph(DependencyGraph(opt.loop), "original_" + self.test_name)
        opt.analyse_index_calculations()
        if opt.dependency_graph is not None:
            self.show_dot_graph(opt.dependency_graph, "early_exit_" + self.test_name)
            opt.schedule(False)
        opt.unroll_loop_iterations(loop, unroll_factor)
        opt.loop.operations = opt.get_newoperations()
        self.debug_print_operations(opt.loop)
        opt.clear_newoperations()
        opt.dependency_graph = DependencyGraph(loop)
        self.last_graph = opt.dependency_graph
        self.show_dot_graph(self.last_graph, self.test_name)
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

    def schedule(self, loop, unroll_factor = -1, with_guard_opt=False):
        opt = self.vectoroptimizer_unrolled(loop, unroll_factor)
        opt.costmodel = FakeCostModel()
        opt.find_adjacent_memory_refs()
        opt.extend_packset()
        opt.combine_packset()
        opt.schedule(True)
        if with_guard_opt:
            gso = GuardStrengthenOpt(opt.dependency_graph.index_vars)
            gso.propagate_all_forward(opt.loop)
        return opt

    def vectorize(self, loop, unroll_factor = -1):
        opt = self.vectoroptimizer_unrolled(loop, unroll_factor)
        opt.find_adjacent_memory_refs()
        opt.extend_packset()
        opt.combine_packset()
        opt.costmodel.reset_savings()
        opt.schedule(True)
        if not opt.costmodel.profitable():
            raise NotAProfitableLoop()
        gso = GuardStrengthenOpt(opt.dependency_graph.index_vars)
        gso.propagate_all_forward(opt.loop)
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

    def test_vectorize_empty_with_early_exit(self):
        ops = """
        []
        jump()
        """
        try:
            self.schedule(self.parse_loop(ops),1)
            py.test.fail("empty loop with no memory references is not vectorizable")
        except NotAVectorizeableLoop:
            pass

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

    def test_load_primitive_python_list(self):
        """ it currently rejects pointer arrays """
        ops = """
        [p0,i0]
        i2 = getarrayitem_gc(p0,i0,descr=floatarraydescr)
        i1 = int_add(i0,1)
        i3 = getarrayitem_gc(p0,i1,descr=floatarraydescr)
        i4 = int_add(i1,1)
        jump(p0,i4)
        """
        opt = """
        [p0,i0]
        i1 = int_add(i0,1)
        i2 = int_add(i0,2)
        i3 = vec_getarrayitem_gc(p0,i0,2,descr=floatarraydescr)
        jump(p0,i2)
        """
        vopt = self.vectorize(self.parse_loop(ops),0)
        self.assert_equal(vopt.loop, self.parse_loop(opt))

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
        i4 = int_add(i0, 1)
        i5 = int_le(i4, 10)
        guard_true(i5) []
        i1 = raw_load(p1, i0, descr=floatarraydescr)
        i2 = raw_load(p2, i0, descr=floatarraydescr)
        i3 = int_add(i1,i2)
        raw_store(p0, i0, i3, descr=floatarraydescr)
        i9 = int_add(i4, 1)
        i10 = int_le(i9, 10)
        guard_true(i10) []
        i6 = raw_load(p1, i4, descr=floatarraydescr)
        i7 = raw_load(p2, i4, descr=floatarraydescr)
        i8 = int_add(i6,i7)
        raw_store(p0, i4, i8, descr=floatarraydescr)
        jump(p0,p1,p2,i9)
        """
        self.assert_unroll_loop_equals(self.parse_loop(ops), self.parse_loop(opt_ops), 1)

    def test_estimate_unroll_factor_smallest_byte_zero(self):
        ops = """
        [p0,i0]
        raw_load(p0,i0,descr=arraydescr)
        jump(p0,i0)
        """
        vopt = self.vectoroptimizer(self.parse_loop(ops))
        assert 0 == vopt.smallest_type_bytes
        assert 0 == vopt.get_unroll_count(ARCH_VEC_REG_SIZE)

    def test_array_operation_indices_not_unrolled(self):
        ops = """
        [p0,i0]
        raw_load(p0,i0,descr=arraydescr)
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
        loop = self.parse_loop(ops)
        vopt = self.vectoroptimizer_unrolled(loop,0)
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
        loop = self.parse_loop(ops)
        vopt = self.vectoroptimizer_unrolled(loop,1)
        vopt.find_adjacent_memory_refs()
        assert len(vopt.dependency_graph.memory_refs) == 2

        mref1 = self.getmemref(loop.find_first_index(rop.RAW_LOAD))
        mref3 = self.getmemref(loop.find_first_index(rop.RAW_LOAD,1))
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
        loop = self.parse_loop(ops)
        vopt = self.vectoroptimizer_unrolled(loop,1)
        vopt.find_adjacent_memory_refs()

        f = lambda x: loop.find_first_index(rop.RAW_LOAD, x)
        indices = [f(0),f(1),f(2),f(3)]
        for i in indices:
            self.assert_has_memory_ref_at(i)
        assert len(vopt.dependency_graph.memory_refs) == 4

        mref1, mref3, mref5, mref7 = [self.getmemref(i) for i in indices]
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
        mref = self.getmemref(5)
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
        mref = self.getmemref(6)
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
        mref = self.getmemref(6)
        mref2 = self.getmemref(7)

        self.assert_memory_ref_not_adjacent(mref, mref2)
        assert mref != mref2

    def test_packset_init_simple(self):
        ops = """
        [p0,i0]
        i3 = getarrayitem_raw(p0, i0, descr=chararraydescr)
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 16)
        guard_true(i2) [p0, i0]
        jump(p0,i1)
        """
        loop = self.parse_loop(ops)
        vopt = self.init_packset(loop,1)
        self.assert_independent(4,8)
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
        i3 = getarrayitem_raw(p0, i1, descr=chararraydescr)
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
        i3 = getarrayitem_raw(p0, i0, descr=chararraydescr)
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 16)
        i4 = getarrayitem_raw(p0, i1, descr=chararraydescr)
        i5 = getarrayitem_raw(p1, i1, descr=floatarraydescr)
        i6 = getarrayitem_raw(p0, i1, descr=floatarraydescr)
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
        i3 = getarrayitem_raw(p0, i1, descr=chararraydescr)
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
        guard_early_exit() []
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 16)
        guard_true(i2) [p0, i0]
        i3 = getarrayitem_raw(p0, i1, descr=chararraydescr)
        i4 = int_mul(i3, 2)
        setarrayitem_raw(p0, i1, i4, descr=chararraydescr)
        jump(p0,i1)
        """
        loop = self.parse_loop(ops)
        vopt = self.extend_packset(loop,1)
        assert len(vopt.dependency_graph.memory_refs) == 4
        self.assert_independent(4,10)
        self.assert_independent(5,11)
        self.assert_independent(6,12)
        assert len(vopt.packset.packs) == 3
        self.assert_packset_empty(vopt.packset, len(loop.operations),
                                  [(6,12), (5,11), (4,10)])

    @pytest.mark.parametrize("descr,packs,packidx", 
                             [('char',1,  [(0,(2,4,6,8))]),
                              ('float',2, [(0,(2,4)),(1,(6,8))]),
                              ('int',2,   [(0,(2,4)),(1,(6,8))]),
                              ('singlefloat',1,[(0,(2,4,6,8))])])
    def test_packset_combine_simple(self,descr,packs,packidx):
        ops = """
        [p0,i0]
        i3 = getarrayitem_raw(p0, i0, descr={descr}arraydescr)
        i1 = int_add(i0,1)
        jump(p0,i1)
        """.format(descr=descr)
        loop = self.parse_loop(ops)
        vopt = self.combine_packset(loop,3)
        assert len(vopt.dependency_graph.memory_refs) == 4
        assert len(vopt.packset.packs) == packs
        for i,t in packidx:
            self.assert_pack(vopt.packset.packs[i], t)

    @pytest.mark.parametrize("descr,stride,packs",
            [('char',1,1),('float',8,4),('int',8,4),('singlefloat',4,2)])
    def test_packset_combine_2_loads_in_trace(self, descr, stride,packs):
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
        assert len(vopt.packset.packs) == packs

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
        i3 = getarrayitem_raw(p0, i0, descr=floatarraydescr)
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
        guard_early_exit() []
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
        if stride == 8:
            assert len(vopt.packset.packs) == 8
        else:
            assert len(vopt.packset.packs) == 4

        for opindices in [(5,12,19,26),(6,13,20,27),
                          (7,14,21,28),(4,11,18,25)]:
            self.assert_has_pack_with(vopt.packset, opindices)

    @pytest.mark.parametrize('op,descr,stride',
            [('float_add','float',8),
             ('float_sub','float',8),
             ('float_mul','float',8),
             ('int_add','int',8),
             ('int_sub','int',8),
            ])
    def test_schedule_vector_operation(self, op, descr, stride):
        ops = """
        [p0,p1,p2,i0] # 0
        guard_early_exit() []
        i10 = int_le(i0, 128)  # 1, 8, 15, 22
        guard_true(i10) [p0,p1,p2,i0] # 2, 9, 16, 23
        i2 = getarrayitem_raw(p0, i0, descr={descr}arraydescr) # 3, 10, 17, 24
        i3 = getarrayitem_raw(p1, i0, descr={descr}arraydescr) # 4, 11, 18, 25
        i4 = {op}(i2,i3) # 5, 12, 19, 26
        setarrayitem_raw(p2, i0, i4, descr={descr}arraydescr) # 6, 13, 20, 27
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
        v1 = vec_getarrayitem_raw(p0, i0, 2, descr={descr}arraydescr)
        v2 = vec_getarrayitem_raw(p1, i0, 2, descr={descr}arraydescr)
        v3 = {op}(v1,v2)
        vec_setarrayitem_raw(p2, i0, v3, descr={descr}arraydescr)
        jump(p0,p1,p2,i12)
        """.format(op='vec_'+op,descr=descr,stride=1)
        loop = self.parse_loop(ops)
        vopt = self.schedule(loop, 1)
        self.assert_equal(loop, self.parse_loop(vops))

    def test_vschedule_trace_1(self):
        ops = """
        [i0, i1, i2, i3, i4]
        guard_early_exit() []
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
        i6 = int_mul(i0, 8) 
        i12 = int_lt(i11, i1) 
        guard_true(i12) []
        i13 = int_add(i11, 1) 
        i14 = int_mul(i11, 8) 
        i18 = int_lt(i13, i1) 
        guard_true(i18) []
        v19 = vec_raw_load(i2, i6, 2, descr=intarraydescr) 
        v20 = vec_raw_load(i3, i6, 2, descr=intarraydescr) 
        v21 = vec_int_add(v19, v20) 
        vec_raw_store(i4, i6, v21, descr=intarraydescr) 
        jump(i13, i1, i2, i3, i4)
        """
        vopt = self.schedule(self.parse_loop(ops),1)
        self.assert_equal(vopt.loop, self.parse_loop(opt))

    def test_collapse_index_guard_1(self):
        ops = """
        [p0,i0]
        guard_early_exit() [p0,i0]
        i1 = getarrayitem_raw(p0, i0, descr=chararraydescr)
        i2 = int_add(i0, 1)
        i3 = int_lt(i2, 102)
        guard_true(i3) [p0,i0]
        jump(p0,i2)
        """
        dead_code =  '\n        '.join([
          "i{t1} = int_add(i0,{i})\n        i{s} = int_lt(i{t1}, 102)".format(
              i=i+2, t1=i+201, t=i+200, s=i+20)
          for i in range(0,14)])
        opt="""
        [p0,i0]
        i200 = int_add(i0, 1)
        i400 = int_lt(i200, 102)
        i2 = int_add(i0, 16)
        i3 = int_lt(i2, 102)
        guard_true(i3) [p0,i0]
        {dead_code}
        i500 = int_add(i0, 16)
        i501 = int_lt(i2, 102)
        i1 = vec_getarrayitem_raw(p0, i0, 16, descr=chararraydescr)
        jump(p0,i2)
        """.format(dead_code=dead_code)
        vopt = self.schedule(self.parse_loop(ops),15,with_guard_opt=True)
        self.assert_equal(vopt.loop, self.parse_loop(opt))

    def test_too_small_vector(self):
        ops = """
        [p0,i0]
        guard_early_exit() [p0,i0]
        i1 = getarrayitem_raw(p0, 0, descr=chararraydescr) # constant index
        i2 = getarrayitem_raw(p0, 1, descr=chararraydescr) # constant index
        i4 = int_add(i1, i2)
        i3 = int_add(i0,1)
        i5 = int_lt(i3, 10)
        guard_true(i5) [p0, i0]
        jump(p0,i1)
        """
        try:
            self.vectorize(self.parse_loop(ops))
            py.test.fail("loop is not vectorizable")
        except NotAVectorizeableLoop:
            pass

    def test_constant_expansion(self):
        ops = """
        [p0,i0]
        guard_early_exit() [p0,i0]
        i1 = getarrayitem_raw(p0, i0, descr=floatarraydescr)
        i4 = int_sub(i1, 42)
        i3 = int_add(i0,1)
        i5 = int_lt(i3, 10)
        guard_true(i5) [p0, i0]
        jump(p0,i3)
        """
        opt="""
        [p0,i0]
        label(p0,i0)
        v3 = vec_int_expand(42)
        label(p0,i0,v3)
        i20 = int_add(i0, 1)
        i30 = int_lt(i20, 10)
        i2 = int_add(i0, 2)
        i3 = int_lt(i2, 10)
        guard_true(i3) [p0,i0]
        i4 = int_add(i0, 2)
        i5 = int_lt(i2, 10)
        v1 = vec_getarrayitem_raw(p0, i0, 2, descr=floatarraydescr)
        v2 = vec_int_sub(v1, v3)
        jump(p0,i2,v3)
        """
        vopt = self.vectorize(self.parse_loop(ops),1)
        self.assert_equal(vopt.loop, self.parse_loop(opt,add_label=False))

    def test_variable_expansion(self):
        ops = """
        [p0,i0,f3]
        guard_early_exit() [p0,i0]
        f1 = getarrayitem_raw(p0, i0, descr=floatarraydescr)
        f4 = int_add(f1, f3)
        i3 = int_add(i0,1)
        i5 = int_lt(i3, 10)
        guard_true(i5) [p0, i0]
        jump(p0,i3,f3)
        """
        opt="""
        [p0,i0,f3]
        label(p0,i0,f3)
        v3 = vec_float_expand(f3)
        label(p0,i0,f3,v3)
        i20 = int_add(i0, 1)
        i30 = int_lt(i20, 10)
        i2 = int_add(i0, 2)
        i3 = int_lt(i2, 10)
        guard_true(i3) [p0,i0]
        i4 = int_add(i0, 2)
        i5 = int_lt(i2, 10)
        v1 = vec_getarrayitem_raw(p0, i0, 2, descr=floatarraydescr)
        v2 = vec_int_add(v1, v3)
        jump(p0,i2,f3,v3)
        """
        vopt = self.vectorize(self.parse_loop(ops),1)
        self.assert_equal(vopt.loop, self.parse_loop(opt, add_label=False))

    def test_accumulate_basic(self):
        trace = """
        [p0, i0, f0]
        guard_early_exit() [p0, i0, f0]
        f1 = raw_load(p0, i0, descr=floatarraydescr)
        f2 = float_add(f0, f1)
        i1 = int_add(i0, 8)
        i2 = int_lt(i1, 100)
        guard_false(i2) [p0, i0, f2]
        jump(p0, i1, f2)
        """
        trace_opt = """
        [p0, i0, v2[f64|2]]
        i1 = int_add(i0, 16)
        i2 = int_lt(i1, 100)
        guard_false(i2) [p0, i0, v[f64|2]]
        i10 = int_add(i0, 16)
        i20 = int_lt(i10, 100)
        v1[f64|2] = vec_raw_load(p0, i0, 2, descr=floatarraydescr)
        v3[f64|2] = vec_float_add(v2[f64|2], v1[f64|2])
        jump(p0, i1, v3[f64|2])
        """
        opt = self.vectorize(self.parse_loop(trace))
        assert len(opt.packset.accum_vars) == 1
        assert opt.loop.inputargs[2] in opt.packset.accum_vars
        self.debug_print_operations(opt.loop)

    def test_element_f45_in_guard_failargs(self):
        ops = """
        [p36, i28, p9, i37, p14, f34, p12, p38, f35, p39, i40, i41, p42, i43, i44, i21, i4, i0, i18]
        guard_early_exit() [p38, p12, p9, p14, p39, i37, i44, f35, i40, p42, i43, f34, i28, p36, i41]
        f45 = raw_load(i21, i44, descr=floatarraydescr) 
        guard_not_invalidated() [p38, p12, p9, p14, f45, p39, i37, i44, f35, i40, p42, i43, None, i28, p36, i41]
        i46 = int_add(i44, 8) 
        f47 = raw_load(i4, i41, descr=floatarraydescr) 
        i48 = int_add(i41, 8) 
        f49 = float_add(f45, f47)
        raw_store(i0, i37, f49, descr=floatarraydescr)
        i50 = int_add(i28, 1)
        i51 = int_add(i37, 8)
        i52 = int_ge(i50, i18) 
        guard_false(i52) [p38, p12, p9, p14, i48, i46, f47, i51, i50, f45, p39, None, None, None, i40, p42, i43, None, None, p36, None]
        jump(p36, i50, p9, i51, p14, f45, p12, p38, f47, p39, i40, i48, p42, i43, i46, i21, i4, i0, i18)
        """
        opt = """
        [p36, i28, p9, i37, p14, f34, p12, p38, f35, p39, i40, i41, p42, i43, i44, i21, i4, i0, i18]
        guard_not_invalidated() [p38, p12, p9, p14, p39, i37, i44, f35, i40, p42, i43, f34, i28, p36, i41]
        i50 = int_add(i28, 1) 
        i48 = int_add(i41, 8) 
        i51 = int_add(i37, 8) 
        i54 = int_add(i41, 16) 
        i46 = int_add(i44, 8) 
        i56 = int_add(i37, 16) 
        i52 = int_ge(i50, i18) 
        i637 = int_add(i28, 2)
        i638 = int_ge(i637, i18)
        guard_false(i638) [p38, p12, p9, p14, p39, i37, i44, f35, i40, p42, i43, f34, i28, p36, i41]
        i55 = int_add(i44, 16) 
        i629 = int_add(i28, 2)
        i57 = int_ge(i637, i18) 
        v61 = vec_raw_load(i21, i44, 2, descr=floatarraydescr) 
        v62 = vec_raw_load(i4, i41, 2, descr=floatarraydescr) 
        v63 = vec_float_add(v61, v62) 
        vec_raw_store(i0, i37, v63, descr=floatarraydescr) 
        f100 = vec_float_unpack(v61, 1, 1)
        f101 = vec_float_unpack(v62, 1, 1)
        jump(p36, i637, p9, i56, p14, f100, p12, p38, f101, p39, i40, i54, p42, i43, i55, i21, i4, i0, i18)
        """
        vopt = self.vectorize(self.parse_loop(ops))
        self.assert_equal(vopt.loop, self.parse_loop(opt))

    def test_shrink_vector_size(self):
        ops = """
        [p0,p1,i1]
        guard_early_exit() []
        f1 = getarrayitem_raw(p0, i1, descr=floatarraydescr)
        i2 = cast_float_to_singlefloat(f1)
        setarrayitem_raw(p1, i1, i2, descr=singlefloatarraydescr)
        i3 = int_add(i1, 1)
        i4 = int_ge(i3, 36)
        guard_false(i4) []
        jump(p0, p1, i3)
        """
        opt = """
        [p0, p1, i1]
        i3 = int_add(i1, 1)
        i4 = int_ge(i3, 36)
        i50 = int_add(i1, 4)
        i51 = int_ge(i50, 36)
        guard_false(i51) []
        i5 = int_add(i1, 2)
        i8 = int_ge(i5, 36)
        i6 = int_add(i1, 3)
        i11 = int_ge(i6, 36)
        i7 = int_add(i1, 4)
        i14 = int_ge(i50, 36)
        v17 = vec_getarrayitem_raw(p0, i1, 2, descr=floatarraydescr)
        v19 = vec_cast_float_to_singlefloat(v17)
        v18 = vec_getarrayitem_raw(p0, i5, 2, descr=floatarraydescr)
        v20 = vec_cast_float_to_singlefloat(v18)
        v21 = vec_float_pack(v19, v20, 2, 2)
        vec_setarrayitem_raw(p1, i1, v21, descr=singlefloatarraydescr)
        jump(p0, p1, i50)
        """
        vopt = self.vectorize(self.parse_loop(ops))
        self.assert_equal(vopt.loop, self.parse_loop(opt))

    def test_castup_arith_castdown(self):
        ops = """
        [p0,p1,p2,i0,i4]
        guard_early_exit() []
        i10 = raw_load(p0, i0, descr=singlefloatarraydescr)
        i1 = int_add(i0, 4)
        i11 = raw_load(p1, i1, descr=singlefloatarraydescr)
        f1 = cast_singlefloat_to_float(i10)
        f2 = cast_singlefloat_to_float(i11)
        f3 = float_add(f1, f2)
        i12  = cast_float_to_singlefloat(f3)
        raw_store(p2, i4, i12, descr=singlefloatarraydescr)
        i5  = int_add(i4, 4) 
        i186 = int_lt(i5, 100) 
        guard_true(i186) []
        jump(p0,p1,p2,i1,i5)
        """
        opt = """
        [p0, p1, p2, i0, i4]
        i5 = int_add(i4, 4)
        i1 = int_add(i0, 4)
        i186 = int_lt(i5, 100)
        i500 = int_add(i4, 16)
        i501 = int_lt(i500, 100)
        guard_true(i501) []
        i189 = int_add(i0, 8)
        i187 = int_add(i4, 8)
        i198 = int_add(i0, 12)
        i188 = int_lt(i187, 100)
        i207 = int_add(i0, 16)
        i196 = int_add(i4, 12)
        i197 = int_lt(i196, 100)
        i205 = int_add(i4, 16)
        i206 = int_lt(i500, 100)
        v228 = vec_raw_load(p0, i0, 4, descr=singlefloatarraydescr)
        v229 = vec_cast_singlefloat_to_float(v228)
        v230 = vec_int_unpack(v228, 2, 2)
        v231 = vec_cast_singlefloat_to_float(v230)
        v232 = vec_raw_load(p1, i1, 4, descr=singlefloatarraydescr)
        v233 = vec_cast_singlefloat_to_float(v232)
        v234 = vec_int_unpack(v232, 2, 2)
        v235 = vec_cast_singlefloat_to_float(v234)
        v237 = vec_float_add(v231, v235)
        v239 = vec_cast_float_to_singlefloat(v237)
        v236 = vec_float_add(v229, v233)
        v238 = vec_cast_float_to_singlefloat(v236)
        v240 = vec_float_pack(v238, v239, 2, 2)
        vec_raw_store(p2, i4, v240, descr=singlefloatarraydescr)
        jump(p0, p1, p2, i207, i500)
        """
        vopt = self.vectorize(self.parse_loop(ops))
        self.assert_equal(vopt.loop, self.parse_loop(opt))

    def test_truediv_abs_neg_float(self):
        ops = """
        [f9,p10,i11,p4,i12,p2,p5,p13,i14,p7,i15,p8,i16,f17,i18,i19]
        guard_early_exit() [p8, p7, p5, p4, p2, f9, i12, i11, p10, i15, i14, p13]
        f20 = raw_load(i16, i12, descr=floatarraydescr)
        guard_not_invalidated() [p8, p7, p5, p4, p2, f20, None, i12, i11, p10, i15, i14, p13]
        i23 = int_add(i12, 8)
        f24 = float_truediv(f20, f17)
        f25 = float_abs(f20)
        f26 = float_neg(f20)
        raw_store(i18, i15, f24, descr=floatarraydescr)
        i26 = int_add(i14, 1)
        i28 = int_add(i15, 8)
        i29 = int_ge(i26, i19)
        guard_false(i29) [p8, p7, p5, p4, p2, f20, i23, i28, None, p13]
        jump(f20, p10, i11, p4, i23, p2, p5, p13, i26, p7, i28, p8, i16, f17, i18, i19)
        """
        opt = self.vectorize(self.parse_loop(ops))
        self.debug_print_operations(opt.loop)

    def test_axis_sum(self):
        trace = """
        [i1, p10, i11, p8, i12, p3, p4, p13, i14, i15, p6, p9, i16, i17, i18, i19, i20, i21, i22, i23]
        guard_early_exit() [i1, p9, p8, p6, p4, p3, i11, i15, p13, i12, i14, p10]
        f24 = raw_load(i16, i12, descr=floatarraydescr)
        guard_not_invalidated() [i1, p9, p8, p6, p4, p3, f24, i11, i15, p13, i12, i14, p10]
        i26 = int_add(i12, 8)
        i27 = getarrayitem_gc(p13, i1, descr=floatarraydescr)
        i28 = int_is_zero(i27)
        guard_false(i28) [i1, p9, p8, p6, p4, p3, f24, i26, i11, i15, p13, None, i14, p10]
        f30 = raw_load(i17, i15, descr=floatarraydescr)
        f31 = float_add(f30, f24)
        raw_store(i18, i15, f31, descr=floatarraydescr)
        i33 = int_add(i14, 1)
        i34 = getarrayitem_gc(p13, i19, descr=floatarraydescr)
        i35 = int_lt(i34, i20)
        guard_true(i35) [i1, p9, p8, p6, p4, p3, i21, i34, i15, i33, i19, p13, f31, None, i26, i11, None, None, None, i14, p10]
        i37 = int_add(i34, 1)
        setarrayitem_gc(p13, i19, i37, descr=floatarraydescr)
        i38 = int_add(i15, i22)
        i39 = int_ge(i33, i23)
        guard_false(i39) [i1, p9, p8, p6, p4, p3, i33, i38, None, None, i26, i11, None, p13, None, None, p10]
        jump(i1, p10, i11, p8, i26, p3, p4, p13, i33, i38, p6, p9, i16, i17, i18, i19, i20, i21, i22, i23)
        """
        try:
            self.vectorize(self.parse_loop(trace))
            py.test.fail("axis sum is not profitable")
        except NotAProfitableLoop:
            pass

    def test_cast_1(self):
        trace = """
        [i9, i10, p2, p11, i12, i13, p4, p5, p14, i15, p8, i16, p17, i18, i19, i20, i21, i22, i23]
        guard_early_exit() [p8, p5, p4, p2, p17, i13, i12, i10, i19, p14, p11, i18, i15, i16, i9]
        i24 = raw_load(i20, i16, descr=singlefloatarraydescr)
        guard_not_invalidated() [p8, p5, p4, p2, i24, p17, i13, i12, i10, i19, p14, p11, i18, i15, i16, None]
        i27 = int_add(i16, 4)
        i28 = raw_load(i21, i19, descr=singlefloatarraydescr)
        i30 = int_add(i19, 4)
        f31 = cast_singlefloat_to_float(i24)
        f32 = cast_singlefloat_to_float(i28)
        f33 = float_add(f31, f32)
        i34 = cast_float_to_singlefloat(f33)
        raw_store(i22, i13, i34, descr=singlefloatarraydescr)
        i36 = int_add(i12, 1)
        i38 = int_add(i13, 4)
        i39 = int_ge(i36, i23)
        guard_false(i39) [p8, p5, p4, p2, i27, i28, i30, i24, i38, i36, p17, None, None, None, None, p14, p11, i18, i15, None, None]
        jump(i24, i28, p2, p11, i36, i38, p4, p5, p14, i15, p8, i27, p17, i18, i30, i20, i21, i22, i23)
        """
        opt = self.vectorize(self.parse_loop(trace))
        self.debug_print_operations(opt.loop)

    def test_all_guard(self):
        trace = """
        [p0, p3, i4, i5, i6, i7]
        guard_early_exit() [p0, p3, i5, i4]
        f8 = raw_load(i6, i5, descr=floatarraydescr)
        guard_not_invalidated() [p0, f8, p3, i5, i4]
        i9 = cast_float_to_int(f8)
        i11 = int_and(i9, 255)
        guard_false(i11) [p0, p3, i5, i4]
        i13 = int_add(i4, 1)
        i15 = int_add(i5, 8)
        i16 = int_ge(i13, i7)
        guard_false(i16) [p0, i13, i15, p3, None, None]
        jump(p0, p3, i13, i15, i6, i7)
        """
        opt = self.vectorize(self.parse_loop(trace))
        self.debug_print_operations(opt.loop)

    def test_max(self):
        trace = """
        [p3, i4, p2, i5, f6, i7, i8]
        guard_early_exit() [p2, f6, i4, i5, p3]
        f9 = raw_load(i7, i5, descr=floatarraydescr)
        guard_not_invalidated() [p2, f9, f6, i4, i5, p3]
        i10 = float_ge(f6, f9)
        guard_false(i10) [p2, f9, f6, None, i4, i5, p3]
        i12 = float_ne(f6, f6)
        guard_false(i12) [p2, f9, f6, None, i4, i5, p3]
        i14 = int_add(i4, 1)
        i16 = int_add(i5, 8)
        i17 = int_ge(i14, i8)
        guard_false(i17) [p2, i16, f9, i14, None, None, None, p3]
        jump(p3, i14, p2, i16, f9, i7, i8)
        """
        opt = self.schedule(self.parse_loop(trace), with_guard_opt=True)
        self.debug_print_operations(opt.loop)


    def test_abc(self):
        trace="""
        [p0, p1, p5, p6, p7, p12, p13, i14, i15, i16, i17, i18, i19, i20]
        guard_early_exit() []
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #117 LOAD_NAME')
        guard_not_invalidated(descr=<ResumeGuardNotInvalidated object at 0x7fc657d7be20>) [p1, p0, p5, p6, p7, p12, p13]
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #120 LOAD_CONST')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #123 COMPARE_OP')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #126 POP_JUMP_IF_FALSE')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #129 LOAD_NAME')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #132 LOAD_NAME')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #135 BINARY_SUBSCR')
        i23 = int_lt(i14, i15)
        guard_true(i23, descr=<ResumeGuardTrueDescr object at 0x7fc657d7bd60>) [p1, p0, i14, p5, p6, p7, p12, p13, None]
        f25 = getarrayitem_raw(i16, i14, descr=floatarraydescr)
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #136 LOAD_NAME')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #139 LOAD_NAME')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #142 BINARY_SUBSCR')
        i26 = int_lt(i14, i17)
        guard_true(i26, descr=<ResumeGuardTrueDescr object at 0x7fc657d7bca0>) [p1, p0, i14, p5, p6, p7, p12, p13, f25, None]
        f27 = getarrayitem_raw(i18, i14, descr=floatarraydescr)
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #143 BINARY_ADD')
        f28 = float_add(f25, f27)
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #144 LOAD_NAME')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #147 LOAD_NAME')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #150 STORE_SUBSCR')
        i29 = int_lt(i14, i19)
        guard_true(i29, descr=<ResumeGuardTrueDescr object at 0x7fc657d7bc40>) [p1, p0, i14, p5, p6, p7, p12, p13, f28, None, None]
        setarrayitem_raw(i20, i14, f28, descr=floatarraydescr)
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #151 LOAD_NAME')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #154 LOAD_CONST')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #157 INPLACE_ADD')
        i31 = int_add(i14, 1)
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #158 STORE_NAME')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #161 JUMP_ABSOLUTE')
        i33 = getfield_raw(140489852409120, descr=<FieldS pypysig_long_struct.c_value 0>)
        setfield_gc(1234, i31, descr=<FieldS pypy.objspace.std.typeobject.IntMutableCell.inst_intvalue 8>)
        i36 = int_lt(i33, 0)
        guard_false(i36, descr=<ResumeGuardFalseDescr object at 0x7fc657d7be80>) [p1, p0, p5, p6, p7, p12, p13, None, None, None]
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/proj/da/thesis/bench/user1.py'. line 2> #117 LOAD_NAME')
        i22 = int_lt(i14, 2024)
        guard_true(i22, descr=<ResumeGuardTrueDescr object at 0x7fc657d7bdc0>) [p1, p0, p5, p6, p7, p12, p13, i14]
        jump(p0, p1, p5, p6, p7, p12, p13, i31, i15, i16, i17, i18, i19, i20)
        """
        # schedule 885 -> ptype is non for raw_load?
        opt = self.vectorize(self.parse_loop(trace))
        self.debug_print_operations(opt.loop)

    def test_bug1(self):
        trace="""
        [p0, p1, p6, p7, p11, i83, f57, f61, f65, f70, f78, f81, i48, i56, p46]
        guard_early_exit(descr=<Guard0x7fa392d5c1a0>) [p1, p0, p6, p7, p11, f81, f78, f70, f65, f61, f57, i83]
        guard_not_invalidated(descr=<Guard0x7fa392d5c200>) [p1, p0, p6, p7, p11, f81, f78, f70, f65, f61, f57, i83]
        i91 = int_lt(i83, i48)
        guard_true(i91, descr=<Guard0x7fa392d5c260>) [p1, p0, p6, p7, p11, i48, f81, f78, f70, f65, f61, f57, i83]
        f92 = getarrayitem_raw(i56, i83, descr=floatarraydescr)
        i93 = int_add(i83, 1)
        i94 = int_lt(i93, i48)
        guard_true(i94, descr=<Guard0x7fa392d5c2c0>) [p1, p0, p46, i93, p6, p7, p11, f92, None, f81, f78, f70, f65, f61, None, i83]
        f95 = getarrayitem_raw(i56, i93, descr=floatarraydescr)
        i96 = int_add(i83, 2)
        i97 = int_lt(i96, i48)
        guard_true(i97, descr=<Guard0x7fa392d5c320>) [p1, p0, p46, i96, p6, p7, p11, f95, f92, None, f81, f78, f70, f65, None, None, i83]
        f98 = getarrayitem_raw(i56, i96, descr=floatarraydescr)
        f99 = float_sub(f98, 128.000000)
        f100 = float_mul(1.370705, f99)
        f101 = float_add(f92, f100)
        f102 = float_mul(0.698001, f99)
        f103 = float_sub(f92, f102)
        f104 = float_sub(f95, 128.000000)
        f105 = float_mul(0.337633, f104)
        f106 = float_sub(f103, f105)
        f107 = float_mul(1.732446, f104)
        f108 = float_add(f92, f107)
        i109 = int_add(i83, 3)
        i110 = getfield_raw(140340519358368, descr=<FieldS pypysig_long_struct.c_value 0>)
        i111 = int_lt(i110, 0)
        guard_false(i111, descr=<Guard0x7fa392d5c380>) [p1, p0, p6, p7, p11, f108, f106, f101, f98, i109, f95, f92, None, None, None, None, None, None, None, None]
        jump(p0, p1, p6, p7, p11, i109, f92, f95, f98, f101, f106, f108, i48, i56, p46)
        """
        opt = self.schedule(self.parse_loop(trace))
        self.debug_print_operations(opt.loop)

    def test_1(self):
        trace = """
        [p0, p1, p5, p6, p7, p9, p11, p12]
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/fijal.py'. line 2> #34 FOR_ITER')
        guard_early_exit(descr=<ResumeAtLoopHeaderDescr object at 0x7ffff7e3cc80>) [p1, p0, p5, p6, p7, p9]
        p13 = getfield_gc(p9, descr=<FieldP pypy.objspace.std.iterobject.W_AbstractSeqIterObject.inst_w_seq 16>)
        guard_nonnull(p13, descr=<ResumeGuardNonnullDescr object at 0x7ffff7e3cce0>) [p1, p0, p9, p13, p5, p6, p7]
        i14 = getfield_gc(p9, descr=<FieldS pypy.objspace.std.iterobject.W_AbstractSeqIterObject.inst_index 8>)
        p15 = getfield_gc(p13, descr=<FieldP pypy.objspace.std.listobject.W_ListObject.inst_strategy 16>)
        guard_class(p15, 140737326900656, descr=<ResumeGuardClassDescr object at 0x7ffff7e3cd40>) [p1, p0, p9, i14, p15, p13, p5, p6, p7]
        p17 = getfield_gc(p13, descr=<FieldP pypy.objspace.std.listobject.W_ListObject.inst_lstorage 8>)
        i18 = getfield_gc_pure(p17, descr=<FieldS tuple1.item0 8>)
        i20 = int_lt(i14, 0)
        guard_false(i20, descr=<ResumeGuardFalseDescr object at 0x7ffff7e3cda0>) [p1, p0, p9, i14, i18, p5, p6, p7]
        i21 = int_ge(i14, i18)
        guard_false(i21, descr=<ResumeGuardFalseDescr object at 0x7ffff7e3ce00>) [p1, p0, p9, i14, p5, p6, p7]
        i23 = int_add(i14, 1)
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/fijal.py'. line 2> #37 STORE_NAME')
        p24 = getfield_gc(p5, descr=<FieldP pypy.interpreter.pyframe.FrameDebugData.inst_w_locals 48>)
        setfield_gc(p9, i23, descr=<FieldS pypy.objspace.std.iterobject.W_AbstractSeqIterObject.inst_index 8>)
        guard_value(p24, 25, descr=<ResumeGuardValueDescr object at 0x7ffff7e3ce60>) [p1, p0, p24, p5, p6, p7, p9, i14]
        p26 = getfield_gc(p24, descr=<FieldP pypy.objspace.std.dictmultiobject.W_DictMultiObject.inst_strategy 16>)
        guard_value(p26, 27, descr=<ResumeGuardValueDescr object at 0x7ffff7e3cec0>) [p1, p0, p26, p24, p5, p6, p7, p9, i14]
        guard_not_invalidated(descr=<ResumeGuardNotInvalidated object at 0x7ffff7e3cf20>) [p1, p0, p24, p5, p6, p7, p9, i14]
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/fijal.py'. line 2> #40 LOAD_NAME')
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/fijal.py'. line 2> #43 CALL_FUNCTION')
        p28 = force_token()
        enter_portal_frame(15, 8070450532247933488)
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #0 LOAD_CONST')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #3 STORE_FAST')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #6 SETUP_LOOP')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #9 LOAD_FAST')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #12 LOAD_CONST')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #15 COMPARE_OP')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #18 POP_JUMP_IF_FALSE')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #21 LOAD_GLOBAL')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #24 LOAD_FAST')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #27 BINARY_SUBSCR')
        p32 = getfield_gc(31, descr=<FieldP pypy.objspace.std.listobject.W_ListObject.inst_strategy 16>)
        setfield_gc(33, i14, descr=<FieldS pypy.objspace.std.typeobject.IntMutableCell.inst_intvalue 8>)
        guard_class(p32, 140737326657856, descr=<ResumeGuardClassDescr object at 0x7ffff7e3cf80>) [p1, p0, p11, p32, p5, p6, p7, p9, p28, p12, None]
        p36 = getfield_gc(31, descr=<FieldP pypy.objspace.std.listobject.W_ListObject.inst_lstorage 8>)
        i37 = getfield_gc(p36, descr=<FieldS list.length 8>)
        i39 = uint_ge(0, i37)
        guard_false(i39, descr=<ResumeGuardFalseDescr object at 0x7ffff7e3cfe0>) [p1, p0, p11, i37, p36, p5, p6, p7, p9, p28, p12, None]
        p40 = getfield_gc(p36, descr=<FieldP list.items 16>)
        i41 = getarrayitem_gc(p40, 0, descr=intarraydescr)
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #28 LOAD_CONST')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #31 BINARY_ADD')
        i43 = int_add_ovf(i41, 1)
        guard_no_overflow(descr=<ResumeGuardNoOverflowDescr object at 0x7ffff7e3d040>) [p1, p0, p11, i43, p5, p6, p7, p9, i41, p28, p12, None]
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #32 LOAD_GLOBAL')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #35 LOAD_FAST')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #38 STORE_SUBSCR')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #39 LOAD_FAST')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #42 LOAD_CONST')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #45 INPLACE_ADD')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #46 STORE_FAST')
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #49 JUMP_ABSOLUTE')
        i45 = getfield_raw(140737351875840, descr=<FieldS pypysig_long_struct.c_value 0>)
        setarrayitem_gc(p40, 0, i43, descr=intarraydescr)
        i48 = int_lt(i45, 0)
        guard_false(i48, descr=<ResumeGuardFalseDescr object at 0x7ffff7e3d0a0>) [p1, p0, p11, p5, p6, p7, p9, None, p28, p12, None]
        debug_merge_point(1, 1, '<code object f. file '/home/rich/fijal.py'. line 4> #9 LOAD_FAST')
        p49 = force_token()
        p51 = new_with_vtable(140737326477112)
        p53 = new_array_clear(4, descr=<ArrayP 8>)
        p55 = new_with_vtable(100000)
        p57 = new_with_vtable(140737326516800)
        setfield_gc(p57, p28, descr=<FieldP JitVirtualRef.virtual_token 8>)
        setfield_gc(p57, 0, descr=<FieldP JitVirtualRef.forced 16>)
        setfield_gc(p11, p57, descr=<FieldP pypy.interpreter.executioncontext.ExecutionContext.inst_topframeref 72>)
        setfield_gc(p0, p49, descr=<FieldP pypy.interpreter.pyframe.PyFrame.vable_token 8>)
        setfield_gc(p51, 0, descr=<FieldU pypy.interpreter.pyframe.PyFrame.inst_escaped 88>)
        setfield_gc(p51, 0, descr=<FieldU pypy.interpreter.pyframe.PyFrame.inst_frame_finished_execution 89>)
        setfield_gc(p51, 9, descr=<FieldS pypy.interpreter.pyframe.PyFrame.inst_last_instr 40>)
        setfield_gc(p51, 1, descr=<FieldS pypy.interpreter.pyframe.PyFrame.inst_valuestackdepth 72>)
        setfield_gc(p51, 25, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_w_globals 80>)
        setfield_gc(p51, 63, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_pycode 64>)
        setfield_gc(p55, 1, descr=<FieldS pypy.objspace.std.intobject.W_IntObject.inst_intval 8>)
        setarrayitem_gc(p53, 0, p55, descr=<ArrayP 8>)
        setfield_gc(p51, p53, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_locals_cells_stack_w 56>)
        setfield_gc(p51, p12, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_f_backref 24>)
        setfield_gc(p51, 66, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_lastblock 48>)
        p67 = call_assembler(p51, p11, descr=<Loop2>)
        guard_not_forced(descr=<ResumeGuardForcedDescr object at 0x7ffff7e4b4d8>) [p1, p0, p11, p51, p67, p57, p5, p6, p7, p9]
        keepalive(p51)
        guard_no_exception(descr=<ResumeGuardNoExceptionDescr object at 0x7ffff7e3d100>) [p1, p0, p11, p51, p67, p57, p5, p6, p7, p9]
        leave_portal_frame(15)
        p69 = getfield_gc(p11, descr=<FieldP pypy.interpreter.executioncontext.ExecutionContext.inst_topframeref 72>)
        p70 = getfield_gc(p51, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_f_backref 24>)
        i71 = getfield_gc(p51, descr=<FieldU pypy.interpreter.pyframe.PyFrame.inst_escaped 88>)
        setfield_gc(p11, p70, descr=<FieldP pypy.interpreter.executioncontext.ExecutionContext.inst_topframeref 72>)
        guard_false(i71, descr=<ResumeGuardFalseDescr object at 0x7ffff7e3d160>) [p1, p0, p67, p69, p51, p57, p5, p6, p7, p9]
        i72 = getfield_gc(p5, descr=<FieldU pypy.interpreter.pyframe.FrameDebugData.inst_is_being_profiled 56>)
        setfield_gc(p57, 0, descr=<FieldP JitVirtualRef.virtual_token 8>)
        guard_value(i72, 0, descr=<ResumeGuardValueDescr object at 0x7ffff7e3d1c0>) [i72, p1, p0, p5, p6, p7, p9, p67]
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/fijal.py'. line 2> #46 POP_TOP')
        p75 = getfield_gc(p5, descr=<FieldP pypy.interpreter.pyframe.FrameDebugData.inst_w_f_trace 40>)
        guard_isnull(p75, descr=<ResumeGuardIsnullDescr object at 0x7ffff7e3d220>) [p1, p0, p75, p5, p6, p7, p9, p67]
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/fijal.py'. line 2> #47 JUMP_ABSOLUTE')
        guard_not_invalidated(descr=<ResumeGuardNotInvalidated object at 0x7ffff7e3d280>) [p1, p0, p5, p6, p7, p9]
        i77 = getfield_raw(140737351875840, descr=<FieldS pypysig_long_struct.c_value 0>)
        i79 = int_lt(i77, 0)
        guard_false(i79, descr=<ResumeGuardFalseDescr object at 0x7ffff7e3d2e0>) [p1, p0, p5, p6, p7, p9]
        debug_merge_point(0, 0, '<code object <module>. file '/home/rich/fijal.py'. line 2> #34 FOR_ITER')
        jump(p0, p1, p5, p6, p7, p9, p11, p70)
        """        
        opt = self.schedule(self.parse_loop(trace))
        self.debug_print_operations(opt.loop)

class TestLLtype(BaseTestVectorize, LLtypeMixin):
    pass
