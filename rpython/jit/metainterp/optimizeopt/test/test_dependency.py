import py
import pytest

from rpython.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, BaseTest, FakeMetaInterpStaticData, convert_old_style_to_targets)
from rpython.jit.metainterp.history import TargetToken, JitCellToken, TreeLoop
from rpython.jit.metainterp.optimizeopt.dependency import (DependencyGraph, Dependency,
        IndexVar, MemoryRef)
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.conftest import option

class DependencyBaseTest(BaseTest):

    def setup_method(self, method):
        self.test_name = method.__name__

    def build_dependency(self, ops):
        loop = self.parse_loop(ops)
        self.last_graph = DependencyGraph(loop)
        self.show_dot_graph(self.last_graph, self.test_name)
        for node in self.last_graph.nodes:
            assert node.independent(node)
        return self.last_graph

    def parse_loop(self, ops):
        loop = self.parse(ops, postprocess=self.postprocess)
        token = JitCellToken()
        loop.operations = [ResOperation(rop.LABEL, loop.inputargs, None, 
                                   descr=TargetToken(token))] + loop.operations
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        return loop

    def assert_edges(self, graph, edge_list, exceptions):
        """ Check if all dependencies are met. for complex cases
        adding None instead of a list of integers skips the test.
        This checks both if a dependency forward and backward exists.
        """
        assert len(edge_list) == len(graph.nodes)
        for idx,edges in enumerate(edge_list):
            if edges is None:
                continue
            node_a = graph.getnode(idx)
            dependencies = node_a.provides()[:]
            for idx_b in edges:
                node_b = graph.getnode(idx_b)
                dependency = node_a.getedge_to(node_b)
                if dependency is None and idx_b not in exceptions.setdefault(idx,[]):
                    self.show_dot_graph(graph, self.test_name + '_except')
                    assert dependency is not None, \
                       " it is expected that instruction at index" + \
                       " %s depends on instr on index %s but it does not.\n%s" \
                            % (node_a, node_b, graph)
                elif dependency is not None:
                    dependencies.remove(dependency)
            assert dependencies == [], \
                    "dependencies unexpected %s.\n%s" \
                    % (dependencies,graph)

    def assert_dependencies(self, ops, full_check=True):
        graph = self.build_dependency(ops)
        import re
        deps = {}
        exceptions = {}
        for i,line in enumerate(ops.splitlines()):
            dep_pattern = re.compile("#\s*(\d+):")
            dep_match = dep_pattern.search(line)
            if dep_match:
                label = int(dep_match.group(1))
                deps_list = []
                deps[label] = []
                for to in [d for d in line[dep_match.end():].split(',') if len(d) > 0]:
                    exception = to.endswith("?")
                    if exception:
                        to = to[:-1]
                        exceptions.setdefault(label,[]).append(int(to))
                    deps[label].append(int(to))

        if full_check:
            edges = [ None ] * len(deps)
            for k,l in deps.items():
                edges[k] = l
            self.assert_edges(graph, edges, exceptions)
        return graph

    def assert_independent(self, a, b):
        a = self.last_graph.getnode(a)
        b = self.last_graph.getnode(b)
        assert a.independent(b), "{a} and {b} are dependent!".format(a=a,b=b)

    def assert_dependent(self, a, b):
        a = self.last_graph.getnode(a)
        b = self.last_graph.getnode(b)
        assert not a.independent(b), "{a} and {b} are independent!".format(a=a,b=b)

    def show_dot_graph(self, graph, name):
        if option and option.viewdeps:
            from rpython.translator.tool.graphpage import GraphPage
            page = GraphPage()
            page.source = graph.as_dot()
            page.links = []
            page.display()

    def debug_print_operations(self, loop):
        print('--- loop instr numbered ---')
        for i,op in enumerate(loop.operations):
            print "[",i,"]",op,
            if op.is_guard():
                if op.rd_snapshot:
                    print op.rd_snapshot.boxes
                else:
                    print op.getfailargs()
            else:
                print ""

    def assert_memory_ref_adjacent(self, m1, m2):
        assert m1.is_adjacent_to(m2)
        assert m2.is_adjacent_to(m1)

    def assert_memory_ref_not_adjacent(self, m1, m2):
        assert not m1.is_adjacent_to(m2)
        assert not m2.is_adjacent_to(m1)

    def getmemref(self, idx):
        node = self.last_graph.getnode(idx)
        return self.last_graph.memory_refs[node]

class BaseTestDependencyGraph(DependencyBaseTest):
    def test_dependency_empty(self):
        ops = """
        [] # 0: 1
        jump() # 1:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_dependency_of_constant_not_used(self):
        ops = """
        [] # 0: 2
        i1 = int_add(1,1) # 1: 2
        jump() # 2:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_dependency_simple(self):
        ops = """
        [] # 0: 4
        i1 = int_add(1,1) # 1: 2
        i2 = int_add(i1,1) # 2: 3
        guard_value(i2,3) [] # 3: 4
        jump() # 4:
        """
        graph = self.assert_dependencies(ops, full_check=True)
        self.assert_independent(0,1)
        self.assert_independent(0,2)
        self.assert_independent(0,3)
        self.assert_dependent(1,2)
        self.assert_dependent(2,3)
        self.assert_dependent(1,3)
        self.assert_dependent(2,4)
        self.assert_dependent(3,4)

    def test_def_use_jump_use_def(self):
        ops = """
        [i3] # 0: 1
        i1 = int_add(i3,1) # 1: 2, 3
        guard_value(i1,0) [] # 2: 3
        jump(i1) # 3:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_dependency_guard(self):
        ops = """
        [i3] # 0: 2,3
        i1 = int_add(1,1) # 1: 2
        guard_value(i1,0) [i3] # 2: 3
        jump(i3) # 3:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_dependency_guard_2(self):
        ops = """
        [i1] # 0: 1,2?,3?
        i2 = int_le(i1, 10) # 1: 2
        guard_true(i2) [i1] # 2: 3
        i3 = int_add(i1,1) # 3: 4
        jump(i3) # 4:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_no_edge_duplication(self):
        ops = """
        [i1] # 0: 1,2?,3
        i2 = int_lt(i1,10) # 1: 2
        guard_false(i2) [i1] # 2: 3
        i3 = int_add(i1,i1) # 3: 4
        jump(i3) # 4:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_no_edge_duplication_in_guard_failargs(self):
        ops = """
        [i1] # 0: 1,2?,3?
        i2 = int_lt(i1,10) # 1: 2
        guard_false(i2) [i1,i1,i2,i1,i2,i1] # 2: 3
        jump(i1) # 3:
        """
        self.assert_dependencies(ops, full_check=True)
        self.assert_dependent(0,1)
        self.assert_dependent(0,2)
        self.assert_dependent(0,3)

    def test_dependencies_1(self):
        ops="""
        [i0, i1, i2] # 0: 1,3,6,7,11?
        i4 = int_gt(i1, 0) # 1: 2
        guard_true(i4) [] # 2: 3, 5, 11?
        i6 = int_sub(i1, 1) # 3: 4
        i8 = int_gt(i6, 0) # 4: 5
        guard_false(i8) [] # 5: 10
        i10 = int_add(i2, 1) # 6: 8
        i12 = int_sub(i0, 1) # 7: 9, 11
        i14 = int_add(i10, 1) # 8: 11
        i16 = int_gt(i12, 0) # 9: 10
        guard_true(i16) [] # 10: 11
        jump(i12, i1, i14) # 11:
        """
        self.assert_dependencies(ops, full_check=True)
        self.assert_independent(6, 2)
        self.assert_independent(6, 1)
        self.assert_dependent(6, 0)

    def test_prevent_double_arg(self):
        ops="""
        [i0, i1, i2] # 0: 1,3
        i4 = int_gt(i1, i0) # 1: 2
        guard_true(i4) [] # 2: 3
        jump(i0, i1, i2) # 3:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_ovf_dep(self):
        ops="""
        [i0, i1, i2] # 0: 2,3
        i4 = int_sub_ovf(1, 0) # 1: 2
        guard_overflow() [i2] # 2: 3
        jump(i0, i1, i2) # 3:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_exception_dep(self):
        ops="""
        [p0, i1, i2] # 0: 1,3?
        i4 = call(p0, 1, descr=nonwritedescr) # 1: 2,3
        guard_no_exception() [] # 2: 3
        jump(p0, i1, i2) # 3:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_call_dependency_on_ptr_but_not_index_value(self):
        ops="""
        [p0, p1, i2] # 0: 1,2?,3?,4?,5?
        i3 = int_add(i2,1) # 1: 2
        i4 = call(p0, i3, descr=nonwritedescr) # 2: 3,4,5?
        guard_no_exception() [i2] # 3: 4?,5?
        p2 = getarrayitem_gc(p1,i3,descr=intarraydescr) # 4: 5
        jump(p2, p1, i3) # 5:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_call_dependency(self):
        ops="""
        [p0, p1, i2, i5] # 0: 1,2?,3?,4?,5?
        i3 = int_add(i2,1) # 1: 2
        i4 = call(i5, i3, descr=nonwritedescr) # 2: 3,4,5?
        guard_no_exception() [i2] # 3: 5?
        p2 = getarrayitem_gc(p1,i3,descr=chararraydescr) # 4: 5
        jump(p2, p1, i3, i5) # 5:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_not_forced(self):
        ops="""
        [p0, p1, i2, i5] # 0: 1,2,4?,5,6
        i4 = call(i5, i2, descr=nonwritedescr) # 1: 2,4,6
        guard_not_forced() [i2] # 2: 3
        guard_no_exception() [] # 3: 6
        i3 = int_add(i2,1) # 4: 5
        p2 = getarrayitem_gc(p1,i3,descr=chararraydescr) # 5: 6
        jump(p2, p1, i2, i5) # 6:
        """
        self.assert_dependencies(ops, full_check=True)
        assert self.last_graph.nodes[2].priority == 100
        assert self.last_graph.nodes[3].priority == 100

    def test_setarrayitem_dependency(self):
        ops="""
        [p0, i1] # 0: 1,2?,3?,4?
        setarrayitem_raw(p0, i1, 1, descr=floatarraydescr) # 1: 2,3
        i2 = getarrayitem_raw(p0, i1, descr=floatarraydescr) # 2: 4
        setarrayitem_raw(p0, i1, 2, descr=floatarraydescr) # 3: 4
        jump(p0, i2) # 4:
        """
        self.assert_dependencies(ops, full_check=True)

    def test_setarrayitem_alias_dependency(self):
        # #1 depends on #2, i1 and i2 might alias, reordering would destroy
        # coorectness
        ops="""
        [p0, i1, i2] # 0: 1,2?,3?
        setarrayitem_raw(p0, i1, 1, descr=floatarraydescr) # 1: 2
        setarrayitem_raw(p0, i2, 2, descr=floatarraydescr) # 2: 3
        jump(p0, i1, i2) # 3:
        """
        self.assert_dependencies(ops, full_check=True)
        self.assert_dependent(1,2)
        self.assert_dependent(0,3)

    def test_setarrayitem_dont_depend_with_memref_info(self):
        ops="""
        [p0, i1] # 0: 1,2,3?,4?
        setarrayitem_raw(p0, i1, 1, descr=chararraydescr) # 1: 4
        i2 = int_add(i1,1) # 2: 3
        setarrayitem_raw(p0, i2, 2, descr=chararraydescr) # 3: 4
        jump(p0, i1) # 4:
        """
        self.assert_dependencies(ops, full_check=True)
        assert self.last_graph.getnode(1).provides_count() == 1
        self.assert_independent(1,2)
        self.assert_independent(1,3) # they modify 2 different cells

    def test_dependency_complex_trace(self):
        ops = """
        [i0, i1, i2, i3, i4, i5, i6, i7] # 0: 1,2,3,4,6,7,8,9,10,12,14,17,19,20,21
        i9 = int_mul(i0, 8) # 1: 2
        i10 = raw_load(i3, i9, descr=intarraydescr) # 2: 5, 10
        i11 = int_mul(i0, 8) # 3: 4
        i12 = raw_load(i4, i11, descr=intarraydescr) # 4: 5,10
        i13 = int_add(i10, i12) # 5: 7,10
        i14 = int_mul(i0, 8) # 6: 7
        raw_store(i5, i14, i13, descr=intarraydescr) # 7: 21
        i16 = int_add(i0, 1) # 8: 9,10,11,13,16,18
        i17 = int_lt(i16, i7) # 9: 10
        guard_true(i17) [i7, i13, i5, i4, i3, i12, i10, i16] # 10: 11,13,16,18,19,21
        i18 = int_mul(i16, 8) # 11:
        i19 = raw_load(i3, i18, descr=intarraydescr) # 12:
        i20 = int_mul(i16, 8) # 13:
        i21 = raw_load(i4, i20, descr=intarraydescr) # 14:
        i22 = int_add(i19, i21) # 15:
        i23 = int_mul(i16, 8) # 16:
        raw_store(i5, i23, i22, descr=intarraydescr) # 17:
        i24 = int_add(i16, 1) # 18:
        i25 = int_lt(i24, i7) # 19:
        guard_true(i25) [i7, i22, i5, i4, i3, i21, i19, i24] # 20:
        jump(i24, i19, i21, i3, i4, i5, i22, i7) # 21:
        """
        self.assert_dependencies(ops, full_check=False)
        self.assert_dependent(2,12)

    def test_cyclic(self):
        pass 
        trace = """
        [p0, p1, p5, p6, p7, p9, p11, p12] # 0: 1,6
        guard_early_exit() [] # 1: 2,6,7
        p13 = getfield_gc(p9) # 2: 3,4,5,6
        guard_nonnull(p13) [] # 3: 4,5,6
        i14 = getfield_gc(p9) # 4: 5,6,7
        p15 = getfield_gc(p13) # 5: 6
        guard_class(p15, 140737326900656) [p1, p0, p9, i14, p15, p13, p5, p6, p7] # 6: 7
        jump(p0,p1,p5,p6,p7,p9,p11,p12) # 7:
        """
        self.assert_dependencies(trace, full_check=True)

class TestLLtype(BaseTestDependencyGraph, LLtypeMixin):
    pass
