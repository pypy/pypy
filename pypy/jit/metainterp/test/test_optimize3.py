import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.metainterp.resoperation import rop, ResOperation, opname
from pypy.jit.metainterp.history import ConstAddr, BoxPtr, TreeLoop,\
     ConstInt, BoxInt, BoxObj, ConstObj
from pypy.jit.backend.llgraph import runner

from pypy.jit.metainterp.optimize3 import AbstractOptimization
from pypy.jit.metainterp.optimize3 import optimize_loop, Specializer,\
     OptimizeGuards
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
    nodedescr = cpu.fielddescrof(NODE, 'value')
    namespace = locals()

class OOtypeMixin(object):
    type_system = 'ootype'
    
    cpu = runner.OOtypeCPU(None)

    NODE = ootype.Instance('NODE', ootype.ROOT, {})
    NODE._add_fields({'value': ootype.Signed,
                      'next': NODE})

    node_vtable = ootype.runtimeClass(NODE)

    node = ootype.new(NODE)
    nodebox = BoxObj(ootype.cast_to_object(node))
    nodedescr = cpu.fielddescrof(NODE, 'value')

    namespace = locals()

class BaseTestOptimize3(object):

    @staticmethod
    def newloop(inputargs, operations):
        loop = TreeLoop("test")
        loop.inputargs = inputargs
        loop.operations = operations
        return loop

    def parse(self, s):
        return parse(s, self.cpu, self.namespace,
                     type_system=self.type_system)

    def optimize(self, lst, optlist=None):
        if not isinstance(lst, TreeLoop):
            loop = self.parse(lst)
        else:
            loop = lst
        if optlist is None:
            optlist = []
        optimize_loop(None, [], loop, self.cpu,
                      spec=Specializer(optlist))
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
            """ % op.lower()
            expected = "[]"
            self.assert_equal(self.optimize(ops), expected)

    def test_constfold_guard(self):
        ops = """
        []
        i0 = int_add(0, 0)
        guard_value(i0, 0)
          fail(i0)
        """
        expected = """
        []
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
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable))
          fail()
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
        """
        expected = """
        [i0]
        guard_value(i0, 0)
            fail()
        """
        loop = self.parse(ops)
        # cheat
        loop.operations[1].result.value = 1
        loop.operations[3].result.value = 3
        loop = self.optimize(loop, [OptimizeGuards()])
        self.assert_equal(loop, expected)


class TestLLtype(LLtypeMixin, BaseTestOptimize3):
    pass

class TestOOtype(OOtypeMixin, BaseTestOptimize3):
    pass
