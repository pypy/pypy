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
from rpython.jit.metainterp.optimizeopt.vectorize import OptVectorize
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

    def assert_vectorize(self, loop, unfolded_loop, call_pure_results=None):
        optloop = self._do_optimize_loop(loop, call_pure_results, export_state=True)
        self.assert_equal(optloop, unfolded_loop)

    def assert_unroll_loop_equals(self, loop, expected_loop, \
                     unroll_factor = -1, call_pure_results=None):
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        jitdriver_sd = FakeJitDriverStaticData()
        opt = OptVectorize(metainterp_sd, jitdriver_sd, loop, [])
        if unroll_factor == -1:
            opt._gather_trace_information(loop)
            unroll_factor = opt.get_estimated_unroll_factor()
        opt_loop = opt.unroll_loop_iterations(loop, unroll_factor)
        self.assert_equal(opt_loop, expected_loop)

    def assert_def_use(self, graph, from_instr_index, to_instr_index):
        assert graph.instr_dependency(from_instr_index,
                                      to_instr_index) is not None, \
               " it is expected that instruction at index" + \
               " %d depend on instr on index %d but it is not" \
                    % (from_instr_index, to_instr_index)

class BaseTestDependencyGraph(DepTestHelper):
    def test_simple(self):
        ops = """
        []
        i1 = int_add(1,1)
        i2 = int_add(i1,1)
        guard_value(i2,3) []
        jump()
        """
        dep_graph = self.build_dependency(ops)
        self.assert_def_use(dep_graph, 1, 2)
        self.assert_def_use(dep_graph, 2, 3)

    def test_label_def_use_jump_use_def(self):
        ops = """
        [i3]
        i1 = int_add(i3,1)
        guard_value(i1,0) []
        jump(i1)
        """
        dep_graph = self.build_dependency(ops)
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

class TestLLtype(BaseTestDependencyGraph, LLtypeMixin):
    pass

#class BaseTestVectorize(BaseTest):
#
#    # vector instructions are not produced by the interpreter
#    # the optimization vectorize produces them
#    # load from from aligned memory example:
#    # vec = vec_aligned_raw_load(dst, index, sizeinbytes, descr)
#    # 'VEC_ALIGNED_RAW_LOAD/3d',
#    # store to aligned memory. example:
#    # vec_aligned_raw_store(dst, index, vector, sizeinbytes, descr)
#    # 'VEC_ALIGNED_RAW_STORE/4d',
#    # a list of operations on vectors
#    # add a vector: vec_int_add(v1, v2, 16)
#    # 'VEC_INT_ADD/3',
#
#class TestVectorize(BaseTestVectorize):
#
#    def test_simple(self):
#        ops = """
#        [ia,ib,ic,i0]
#        ibi = raw_load(ib, i0, descr=arraydescr)
#        ici = raw_load(ic, i0, descr=arraydescr)
#        iai = int_add(ibi, ici)
#        raw_store(ia, i0, iai, descr=arraydescr)
#        i1 = int_add(i0,1)
#        ie = int_ge(i1,8)
#        guard_false(ie) [ia,ib,ic,i1]
#        jump(ia,ib,ic,i1)
#        """
#        expected = """
#        [ia,ib,ic,i0]
#        ibv = vec_raw_load(ib, i0, 16, descr=arraydescr)
#        icv = vec_raw_load(ic, i0, 16, descr=arraydescr)
#        iav = vec_int_add(ibi, ici, 16)
#        vec_raw_store(ia, i0, iai, 16, descr=arraydescr)
#        i1 = int_add(i0,4)
#        ie = int_ge(i1,8)
#        guard_false(ie) [ia,ib,ic,i1]
#        jump(ia,ib,ic,i1)
#        """
#        self.optimize_loop(ops, expected)
#
#class TestLLtype(TestVectorize, LLtypeMixin):
#    pass
