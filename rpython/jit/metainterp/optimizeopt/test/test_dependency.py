import py

from rpython.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, BaseTest, FakeMetaInterpStaticData, convert_old_style_to_targets)
from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt.dependency import (DependencyGraph, Dependency,
        IntegralMod)
from rpython.jit.metainterp.resoperation import rop, ResOperation

class DepTestHelper(BaseTest):

    def build_dependency(self, ops, memory_refs = False):
        loop = self.parse_loop(ops)
        refs = {}
        if memory_refs:
            opt = Optimizer(None, None, loop)


        self.last_graph = DependencyGraph(loop.operations, refs)
        for i in range(len(self.last_graph.adjacent_list)):
            self.assert_independent(i,i)
        return self.last_graph

    def parse_loop(self, ops):
        loop = self.parse(ops, postprocess=self.postprocess)
        token = JitCellToken()
        loop.operations = [ResOperation(rop.LABEL, loop.inputargs, None, 
                                   descr=TargetToken(token))] + loop.operations
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        return loop

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
    def assert_graph_equal(self, ga, gb):
        assert len(ga.adjacent_list) == len(gb.adjacent_list)
        for i in range(len(ga.adjacent_list)):
            la = ga.adjacent_list[i]
            lb = gb.adjacent_list[i]
            assert len(la) == len(lb)
            assert sorted([l.idx_to for l in la]) == \
                   sorted([l.idx_to for l in lb])
            assert sorted([l.idx_from for l in la]) == \
                   sorted([l.idx_from for l in lb])

    def assert_independent(self, a, b):
        assert self.last_graph.independent(a,b), "{a} and {b} are dependent!".format(a=a,b=b)

    def assert_dependent(self, a, b):
        assert not self.last_graph.independent(a,b), "{a} and {b} are independent!".format(a=a,b=b)

class BaseTestDependencyGraph(DepTestHelper):
    def test_dependency_empty(self):
        ops = """
        []
        jump()
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph, [ [], [], ])

    def test_dependency_of_constant_not_used(self):
        ops = """
        []
        i1 = int_add(1,1)
        jump()
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph, [ [], [], [] ])

    def test_dependency_simple(self):
        ops = """
        []
        i1 = int_add(1,1)
        i2 = int_add(i1,1)
        guard_value(i2,3) []
        jump()
        """
        graph = self.build_dependency(ops)
        self.assert_edges(graph, 
                [ [], [2], [1,3], [2], [], ])
        for i in range(0,5):
            self.assert_independent(0,i)
        self.assert_dependent(1,2)
        self.assert_dependent(2,3)
        self.assert_dependent(1,3)
        self.assert_independent(2,4)
        self.assert_independent(3,4)

    def test_def_use_jump_use_def(self):
        ops = """
        [i3]
        i1 = int_add(i3,1)
        guard_value(i1,0) []
        jump(i1)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph, 
                [ [1], [0,2,3], [1], [1] ])

    def test_dependency_guard(self):
        ops = """
        [i3]
        i1 = int_add(1,1)
        guard_value(i1,0) [i3]
        jump(i3)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph, 
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
        self.assert_edges(dep_graph, 
                [ [1,2,3], [0,2], [1,0], [0,4], [3] ])

    def test_no_edge_duplication_in_guard_failargs(self):
        ops = """
        [i1]
        i2 = int_lt(i1,10)
        guard_false(i2) [i1,i1,i2,i1,i2,i1]
        jump(i1)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph, 
                [ [1,2,3], [0,2], [1,0], [0] ])
        self.assert_dependent(0,1)
        self.assert_dependent(0,2)
        self.assert_dependent(0,3)

    def test_swap_dependencies(self):
        ops = """
        [i1,i4] # 0
        i2 = int_lt(i1,0) # 1
        i3 = int_lt(i4,0) # 2
        guard_value(i2,0) [] # 3
        jump(i1,i3) # 4
        """
        dep_graph = self.build_dependency(ops)
        dep_graph.swap_instructions(1,2)
        self.assert_edges(dep_graph,
                [ [1,2,4], [4,0], [3,0], [2], [0,1] ])
        dep_graph.swap_instructions(1,2)
        self.assert_graph_equal(dep_graph, self.build_dependency(ops))

        dep_graph.swap_instructions(2,3)
        ops2 = """
        [i1,i4] # 0
        i2 = int_lt(i1,0) # 1
        guard_value(i2,0) [] # 2
        i3 = int_lt(i4,0) # 3
        jump(i1,i3) # 4
        """
        dep_graph_final = self.build_dependency(ops2)
        self.assert_graph_equal(dep_graph, dep_graph_final)

    def test_dependencies_1(self):
        ops="""
        [i0, i1, i2] # 0
        i4 = int_gt(i1, 0) # 1
        guard_true(i4) [] # 2
        i6 = int_sub(i1, 1) # 3
        i8 = int_gt(i6, 0) # 4
        guard_false(i8) [] # 5
        i10 = int_add(i2, 1) # 6
        i12 = int_sub(i0, 1) # 7
        i14 = int_add(i10, 1) # 8
        i16 = int_gt(i12, 0) # 9
        guard_true(i16) [] # 10
        jump(i12, i1, i14) # 11
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph,
                [ [1,3,6,7,11], [0,2], [1], [0,4], [3,5], [4],
                  # next entry is instr 6
                  [0,8], [0,9,11], [6,11], [7,10], [9], [7,0,8] ])
        self.assert_independent(6, 2)
        self.assert_independent(6, 1)
        self.assert_dependent(6, 0)

    def test_prevent_double_arg(self):
        ops="""
        [i0, i1, i2]
        i4 = int_gt(i1, i0)
        guard_true(i4) []
        jump(i0, i1, i2)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph,
                [ [1,3], [0,2], [1], [0] ])

    def test_ovf_dep(self):
        ops="""
        [i0, i1, i2]
        i4 = int_sub_ovf(1, 0)
        guard_overflow() [i2]
        jump(i0, i1, i2)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph,
                [ [1,2,3], [0,2], [0,1], [0] ])

    def test_exception_dep(self):
        ops="""
        [p0, i1, i2]
        i4 = call(p0, 1, descr=nonwritedescr)
        guard_no_exception() []
        jump(p0, i1, i2)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph,
                [ [1,3], [0,2], [1], [0] ])

    def test_call_dependency_on_ptr_but_not_index_value(self):
        ops="""
        [p0, p1, i2]
        i3 = int_add(i2,1)
        i4 = call(p0, i3, descr=nonwritedescr)
        guard_no_exception() [i2]
        p2 = getarrayitem_gc(p1,i3)
        jump(p2, p1, i3)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph,
                [ [1,2,3,4,5], [0,2,4,5], [0,1,3], [0,2], [0,1,5], [4,0,1] ])

    def test_call_dependency(self):
        ops="""
        [p0, p1, i2, i5]
        i3 = int_add(i2,1)
        i4 = call(i5, i3, descr=nonwritedescr)
        guard_no_exception() [i2]
        p2 = getarrayitem_gc(p1,i3)
        jump(p2, p1, i3)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph,
                [ [1,2,3,4,5], [0,2,4,5], [0,1,3], [0,2], [0,1,5], [4,0,1] ])

    def test_setarrayitem_dependency(self):
        ops="""
        [p0, i1]
        setarrayitem_raw(p0, i1, 1, descr=floatarraydescr) # redef p0[i1]
        i2 = getarrayitem_raw(p0, i1, descr=floatarraydescr) # use of redef above
        setarrayitem_raw(p0, i1, 2, descr=floatarraydescr) # redef of p0[i1]
        jump(p0, i2)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph,
                [ [1,2,3], [0,2,3], [0,1,4], [0,1,4], [2,3] ])

    def test_setarrayitem_alias_dependency(self):
        # #1 depends on #2, i1 and i2 might alias, reordering would destroy
        # coorectness
        ops="""
        [p0, i1, i2]
        setarrayitem_raw(p0, i1, 1, descr=floatarraydescr) #1
        setarrayitem_raw(p0, i2, 2, descr=floatarraydescr) #2
        jump(p0, i1, i2)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph,
                [ [1,2,3], [0,2], [0,1,3], [0,2] ])

    def test_setarrayitem_same_modified_var_not_aliased(self):
        # #1 depends on #2, i1 and i2 might alias, reordering would destroy
        # coorectness
        ops="""
        [p0, i1]
        setarrayitem_raw(p0, i1, 1, descr=floatarraydescr) #1
        i2 = int_add(i1,1)
        setarrayitem_raw(p0, i2, 2, descr=floatarraydescr) #2
        jump(p0, i1)
        """
        dep_graph = self.build_dependency(ops)
        self.assert_edges(dep_graph,
                [ [1,2,4], [0,3], [0,3], [0,1,2,4], [0,3] ])
        dep_graph = self.build_dependency(ops, memory_refs=True)
        self.assert_edges(dep_graph,
                [ [1,2,3,4], [0], [0,3], [0,2,4], [0,3] ])

class TestLLtype(BaseTestDependencyGraph, LLtypeMixin):
    pass
