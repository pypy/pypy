import py
from rpython.rlib.objectmodel import instantiate
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, BaseTest, FakeMetaInterpStaticData, convert_old_style_to_targets)
from rpython.jit.metainterp.history import TargetToken, JitCellToken
from rpython.jit.metainterp.optimizeopt import optimize_trace
import rpython.jit.metainterp.optimizeopt.optimizer as optimizeopt
import rpython.jit.metainterp.optimizeopt.virtualize as virtualize
from rpython.jit.metainterp.optimizeopt.dependency import DependencyGraph
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.history import ConstInt, BoxInt, get_const_ptr_for_string
from rpython.jit.metainterp import executor, compile, resume
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.rlib.rarithmetic import LONG_BIT

class DepTestHelper(BaseTest):

    enable_opts = "vectorize"

    def build_dependency(self, ops):
        loop = self.parse(ops, postprocess=self.postprocess)
        token = JitCellToken()
        loop.operations = [ResOperation(rop.LABEL, loop.inputargs, None, 
                                   descr=TargetToken(token))] + loop.operations
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        #self._do_optimize_loop(loop, call_pure_results, export_state=False)
        #print '\n'.join([str(o) for o in loop.operations])
        #self.assert_equal(loop, expected)

        return DependencyGraph(None, loop)

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

    def test_label_def(self):
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

class TestLLtype(BaseTestDependencyGraph, LLtypeMixin):
    pass
