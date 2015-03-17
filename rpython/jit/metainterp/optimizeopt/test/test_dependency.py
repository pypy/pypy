import py

from rpython.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, BaseTest, FakeMetaInterpStaticData, convert_old_style_to_targets)
from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt.dependency import DependencyGraph, Dependency
from rpython.jit.metainterp.resoperation import rop, ResOperation

class DepTestHelper(BaseTest):

    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unfold"

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

    def assert_dependant(self, graph, edge_list):
        """ Check if all dependencies are met. for complex cases
        adding None instead of a list of integers skips the test.
        This checks both if a dependency forward and backward exists.
        """
        assert len(edge_list) == len(graph.adjacent_list)
        for idx,edges in enumerate(edge_list):
            if edges is None:
                continue
            dependencies = graph.adjacent_list[idx]
            for edge in edges:
                dependency = graph.instr_dependency(idx,edge)
                assert dependency is not None, \
                   " it is expected that instruction at index" + \
                   " %d depends on instr on index %d but it is not" \
                        % (idx, edge)
                dependencies.remove(dependency)
            assert dependencies == [], \
                    "dependencies unexpected %s" \
                    % dependencies

class BaseTestDependencyGraph(DepTestHelper):
    def test_dependency_empty(self):
        ops = """
        []
        jump()
        """
        dep_graph = self.build_dependency(ops)
        self.assert_dependant(dep_graph, [ [], [], ])

    def test_dependency_of_constant_not_used(self):
        ops = """
        []
        i1 = int_add(1,1)
        jump()
        """
        dep_graph = self.build_dependency(ops)
        self.assert_dependant(dep_graph, [ [], [], [] ])

    def test_dependency_simple(self):
        ops = """
        []
        i1 = int_add(1,1)
        i2 = int_add(i1,1)
        guard_value(i2,3) []
        jump()
        """
        dep_graph = self.build_dependency(ops)
        self.assert_dependant(dep_graph, 
                [ [], [2], [1,3], [2], [], ])

    def test_def_use_jump_use_def(self):
        ops = """
        [i3]
        i1 = int_add(i3,1)
        guard_value(i1,0) []
        jump(i1)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_dependant(dep_graph, 
                [ [1], [0,2,3], [1], [1] ])

    def test_dependency_guard(self):
        ops = """
        [i3]
        i1 = int_add(1,1)
        guard_value(i1,0) [i3]
        jump(i3)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_dependant(dep_graph, 
                [ [2,3], [2], [1,0], [0] ])

    def test_no_edge_duplication(self):
        ops = """
        [i1]
        i2 = int_lt(i1,10)
        guard_false(i2) [i1]
        i3 = int_add(i1,i1)
        jump(i3)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_dependant(dep_graph, 
                [ [1,2,3], [0,2], [1,0], [0,4], [3] ])

    def test_no_edge_duplication_in_guard_failargs(self):
        ops = """
        [i1]
        i2 = int_lt(i1,10)
        guard_false(i2) [i1,i1,i2,i1,i2,i1]
        jump(i1)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_dependant(dep_graph, 
                [ [1,2,3], [0,2], [1,0], [0] ])

class TestLLtype(BaseTestDependencyGraph, LLtypeMixin):
    pass
