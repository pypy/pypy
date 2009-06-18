import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.metainterp.resoperation import rop, ResOperation, opname
from pypy.jit.metainterp.history import ConstAddr, BoxPtr, TreeLoop,\
     ConstInt, BoxInt, BoxObj, ConstObj
from pypy.jit.backend.llgraph import runner

from pypy.jit.metainterp.optimize3 import AbstractOptimization
from pypy.jit.metainterp.optimize3 import optimize_loop, LoopOptimizer,\
     LoopSpecializer, OptimizeGuards, OptimizeVirtuals
from pypy.jit.metainterp.specnode3 import VirtualInstanceSpecNode, \
     NotSpecNode, FixedClassSpecNode
from pypy.jit.metainterp.test.test_optimize import equaloplists, ANY
from pypy.jit.metainterp.test.oparser import parse


def test_AbstractOptimization():
    
    class MyOpt(AbstractOptimization):
        def int_add(self, spec, op):
            return 'hello world', op

    class MyOpt2(MyOpt):
        def handle_default_op(self, spec, op):
            return 'default op', op

        def find_nodes_int_add(self, spec, op):
            op.found = 42

    myopt = MyOpt()
    myopt2 = MyOpt2()
    op = ResOperation(rop.INT_ADD, [], None)
    assert myopt.handle_op(None, op) == ('hello world', op)
    assert myopt2.handle_op(None, op) == ('hello world', op)
    myopt.find_nodes_for_op(None, op)
    assert not hasattr(op, 'found')
    myopt2.find_nodes_for_op(None, op)
    assert op.found == 42

    op = ResOperation(rop.INT_SUB, [], None)
    assert myopt.handle_op(None, op) == op
    assert myopt2.handle_op(None, op) == ('default op', op)
    myopt2.find_nodes_for_op(None, op)
    assert not hasattr(op, 'found')


class LLtypeMixin(object):
    type_system = 'lltype'

    node_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    node_vtable_adr = llmemory.cast_ptr_to_adr(node_vtable)
    cpu = runner.LLtypeCPU(None)

    NODE = lltype.GcForwardReference()
    NODE.become(lltype.GcStruct('NODE', ('parent', OBJECT),
                                        ('value', lltype.Signed),
                                        ('next', lltype.Ptr(NODE))))
    node = lltype.malloc(NODE)
    nodebox = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node))
    nodebox2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node))
    nodesize = cpu.sizeof(NODE)
    valuedescr = cpu.fielddescrof(NODE, 'value')
    namespace = locals()

class OOtypeMixin(object):
    type_system = 'ootype'
    
    cpu = runner.OOtypeCPU(None)

    NODE = ootype.Instance('NODE', ootype.ROOT, {})
    NODE._add_fields({'value': ootype.Signed,
                      'next': NODE})

    node_vtable = ootype.runtimeClass(NODE)
    node_vtable_adr = ootype.cast_to_object(node_vtable)

    node = ootype.new(NODE)
    nodebox = BoxObj(ootype.cast_to_object(node))
    nodebox2 = BoxObj(ootype.cast_to_object(node))
    valuedescr = cpu.fielddescrof(NODE, 'value')
    nodesize = cpu.typedescrof(NODE)

    namespace = locals()

class BaseTestOptimize3(object):

    @staticmethod
    def newloop(inputargs, operations):
        loop = TreeLoop("test")
        loop.inputargs = inputargs
        loop.operations = operations
        return loop

    def parse(self, s, boxkinds=None):
        return parse(s, self.cpu, self.namespace,
                     type_system=self.type_system,
                     boxkinds=boxkinds)

    def optimize(self, lst, optlist=None):
        if not isinstance(lst, TreeLoop):
            loop = self.parse(lst)
        else:
            loop = lst
        if optlist is None:
            optlist = []
        optimize_loop(None, [], loop, self.cpu,
                      opt=LoopOptimizer(optlist))
        return loop

    def assert_equal(self, optimized, expected):
        equaloplists(optimized.operations,
                     self.parse(expected).operations)


    def test_constfold(self):
        for op in range(rop.INT_ADD, rop._COMPARISON_FIRST):
            try:
                op = opname[op]
            except KeyError:
                continue
            ops = """
            []
            i1 = %s(3, 2)
            jump()
            """ % op.lower()
            expected = """
            []
            jump()
            """
            self.assert_equal(self.optimize(ops), expected)

    def test_constfold_guard(self):
        ops = """
        []
        i0 = int_add(0, 0)
        guard_value(i0, 0)
          fail(i0)
        jump()
        """
        expected = """
        []
        jump()
        """
        loop = self.optimize(ops, [])
        self.assert_equal(loop, expected)

    def test_remove_guard_class(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable))
          fail()
        guard_class(p0, ConstClass(node_vtable))
          fail()
        jump(p0)
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable))
          fail()
        jump(p0)
        """
        loop = self.optimize(ops, [OptimizeGuards()])
        self.assert_equal(loop, expected)


    def test_remove_consecutive_guard_value_constfold(self):
        ops = """
        [i0]
        guard_value(i0, 0)
          fail()
        i1 = int_add(i0, 1)
        guard_value(i1, 1)
          fail()
        i2 = int_add(i1, 2)
        jump(i0)
        """
        expected = """
        [i0]
        guard_value(i0, 0)
            fail()
        jump(0)
        """
        loop = self.parse(ops)
        # cheat
        loop.operations[1].result.value = 1
        loop.operations[3].result.value = 3
        loop = self.optimize(loop, [OptimizeGuards()])
        self.assert_equal(loop, expected)

    def _get_virtual_simple_loop(self):
        ops = """
        [i0, p0]
        guard_class(p0, ConstClass(node_vtable))
          fail()
        i1 = getfield_gc(p0, descr=valuedescr)
        i2 = int_sub(i1, 1)
        i3 = int_add(i0, i1)
        p1 = new_with_vtable(ConstClass(node_vtable), descr=nodesize)
        setfield_gc(p1, i2, descr=valuedescr)
        jump(i3, p1)
        """
        loop = self.parse(ops)
        loop.setvalues(i0 = 0,
                       p0 = self.nodebox.value,
                       i1 = 20,
                       i2 = 19,
                       i3 = 20,
                       p1 = self.nodebox2.value)
        return loop

    def test_virtual_simple_find_nodes(self):
        loop = self._get_virtual_simple_loop()
        spec = LoopSpecializer([OptimizeVirtuals()])
        spec._init(loop)
        spec.find_nodes()

        b = loop.getboxes()
        assert spec.nodes[b.i0] is not spec.nodes[b.i3]
        assert spec.nodes[b.p0] is not spec.nodes[b.p1]
        assert spec.nodes[b.p0].known_class.source.value == self.node_vtable_adr
        assert not spec.nodes[b.p0].escaped
        assert spec.nodes[b.p1].known_class.source.value == self.node_vtable_adr
        assert not spec.nodes[b.p1].escaped

        assert len(spec.nodes[b.p0].curfields) == 0
        assert spec.nodes[b.p0].origfields[self.valuedescr] is spec.nodes[b.i1]
        assert len(spec.nodes[b.p1].origfields) == 0
        assert spec.nodes[b.p1].curfields[self.valuedescr] is spec.nodes[b.i2]

    def test_virtual_simple_intersect_input_and_output(self):
        loop = self._get_virtual_simple_loop()
        spec = LoopSpecializer([OptimizeVirtuals()])
        spec._init(loop)
        spec.find_nodes()
        spec.intersect_input_and_output()
        
        assert len(spec.specnodes) == 2
        spec_sum, spec_n = spec.specnodes
        assert isinstance(spec_sum, NotSpecNode)
        assert isinstance(spec_n, VirtualInstanceSpecNode)
        assert spec_n.known_class.value == self.node_vtable_adr
        assert spec_n.fields[0][0] == self.valuedescr
        assert isinstance(spec_n.fields[0][1], NotSpecNode)

    def test_virtual_simple_optimize_loop(self):
        loop = self._get_virtual_simple_loop()
        opt = LoopOptimizer([OptimizeVirtuals()])
        opt.optimize_loop(loop)
        expected = """
        [i0, i1]
        i2 = int_sub(i1, 1)
        i3 = int_add(i0, i1)
        jump(i3, i2)
        """
        self.assert_equal(loop, expected)

    def _get_virtual_escape_loop(self):
        ops = """
        [sum, n1]
        guard_class(n1, ConstClass(node_vtable))
            fail()
        escape(n1)
        v = getfield_gc(n1, descr=valuedescr)
        v2 = int_sub(v, 1)
        sum2 = int_add(sum, v)
        n2 = new_with_vtable(ConstClass(node_vtable), descr=nodesize)
        setfield_gc(n2, v2, descr=valuedescr)
        escape(n2)
        jump(sum2, n2)
        """
        loop = self.parse(ops, boxkinds={'sum': BoxInt,
                                         'v': BoxInt,
                                         'n': BoxPtr})
        loop.setvalues(sum  = 0,
                       n1   = self.nodebox.value,
                       v    = 20,
                       v2   = 19,
                       sum2 = 20,
                       n2   = self.nodebox2.value)
        return loop

    def test_virtual_escape_find_nodes(self):
        loop = self._get_virtual_escape_loop()
        spec = LoopSpecializer([OptimizeVirtuals()])
        spec._init(loop)
        spec.find_nodes()

        b = loop.getboxes()
        assert spec.nodes[b.n1].known_class.source.value == self.node_vtable_adr
        assert spec.nodes[b.n1].escaped
        assert spec.nodes[b.n2].known_class.source.value == self.node_vtable_adr
        assert spec.nodes[b.n2].escaped

    def test_virtual_escape_intersect_input_and_output(self):
        loop = self._get_virtual_escape_loop()
        spec = LoopSpecializer([OptimizeVirtuals()])
        spec._init(loop)
        spec.find_nodes()
        spec.intersect_input_and_output()

        assert len(spec.specnodes) == 2
        spec_sum, spec_n = spec.specnodes
        assert isinstance(spec_sum, NotSpecNode)
        assert type(spec_n) is FixedClassSpecNode
        assert spec_n.known_class.value == self.node_vtable_adr

    def test_virtual_escape_optimize_loop(self):
        loop = self._get_virtual_escape_loop()
        opt = LoopOptimizer([OptimizeVirtuals()])
        opt.optimize_loop(loop)
        expected = """
        [sum, n1]
        escape(n1)
        v = getfield_gc(n1, descr=valuedescr)
        v2 = int_sub(v, 1)
        sum2 = int_add(sum, v)
        n2 = new_with_vtable(ConstClass(node_vtable), descr=nodesize)
        setfield_gc(n2, v2, descr=valuedescr)
        escape(n2)
        jump(sum2, n2)
        """
        self.assert_equal(loop, expected)


class TestLLtype(LLtypeMixin, BaseTestOptimize3):
    pass

class TestOOtype(OOtypeMixin, BaseTestOptimize3):
    pass
