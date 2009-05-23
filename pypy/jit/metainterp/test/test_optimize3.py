import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.history import ConstAddr, BoxPtr, TreeLoop,\
     ConstInt, BoxInt, BoxObj, ConstObj
from pypy.jit.backend.llgraph import runner

from pypy.jit.metainterp.optimize3 import AbstractOptimization
from pypy.jit.metainterp.optimize3 import optimize_loop
from pypy.jit.metainterp.test.test_optimize import equaloplists, ANY

def test_AbstractOptimization():
    
    class MyOpt(AbstractOptimization):
        def int_add(self, spec, op):
            return 'hello world', op

    class MyOpt2(MyOpt):
        def handle_default_op(self, spec, op):
            return 'default op', op

    myopt = MyOpt()
    myopt2 = MyOpt2()
    op = ResOperation(rop.INT_ADD, [], None)
    assert myopt.handle_op(None, op) == ('hello world', op)
    assert myopt2.handle_op(None, op) == ('hello world', op)

    op = ResOperation(rop.INT_SUB, [], None)
    assert myopt.handle_op(None, op) == op
    assert myopt2.handle_op(None, op) == ('default op', op)


class LLtypeMixin(object):

    node_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    node_vtable_adr = llmemory.cast_ptr_to_adr(node_vtable)
    cpu = runner.LLtypeCPU(None)
    vtable_box = ConstAddr(node_vtable_adr, cpu)

    NODE = lltype.GcForwardReference()
    NODE.become(lltype.GcStruct('NODE', ('parent', OBJECT),
                                        ('value', lltype.Signed),
                                        ('next', lltype.Ptr(NODE))))
    node = lltype.malloc(NODE)
    nodebox = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node))
    nodedescr = cpu.fielddescrof(NODE, 'value')

class OOtypeMixin(object):
    cpu = runner.OOtypeCPU(None)

    NODE = ootype.Instance('NODE', ootype.ROOT, {})
    NODE._add_fields({'value': ootype.Signed,
                      'next': NODE})

    node_vtable = ootype.runtimeClass(NODE)
    vtable_box = ConstObj(ootype.cast_to_object(node_vtable))

    node = ootype.new(NODE)
    nodebox = BoxObj(ootype.cast_to_object(node))
    nodedescr = cpu.fielddescrof(NODE, 'value')



class BaseTestOptimize3(object):

    @staticmethod
    def newloop(inputargs, operations):
        loop = TreeLoop("test")
        loop.inputargs = inputargs
        loop.operations = operations
        return loop

    def test_constfold(self):
        ops = [
            ResOperation(rop.INT_ADD, [ConstInt(10), ConstInt(20)], ConstInt(30)),
            ]
        loop = self.newloop([], ops)
        optimize_loop(None, [], loop)
        assert len(loop.operations) == 0

    def test_remove_guard_class(self):
        ops = [
            ResOperation(rop.GUARD_CLASS, [self.nodebox, self.vtable_box], None),
            ResOperation(rop.GUARD_CLASS, [self.nodebox, self.vtable_box], None),
        ]
        ops[0].suboperations = [ResOperation(rop.FAIL, [], None)]
        ops[1].suboperations = [ResOperation(rop.FAIL, [], None)]
        loop = self.newloop([self.nodebox], ops)
        optimize_loop(None, [], loop)
        assert len(loop.operations) == 1

    def test_remove_consecutive_guard_value_constfold(self):
        py.test.skip('in-progress')
        n = BoxInt(0)
        n1 = BoxInt(1)
        n2 = BoxInt(3)
        ops = [
            ResOperation(rop.GUARD_VALUE, [n, ConstInt(0)], None),
            ResOperation(rop.INT_ADD, [n, ConstInt(1)], n1),
            ResOperation(rop.GUARD_VALUE, [n1, ConstInt(1)], None),
            ResOperation(rop.INT_ADD, [n1, ConstInt(2)], n2),
        ]
        ops[0].suboperations = [ResOperation(rop.FAIL, [], None)]
        ops[2].suboperations = [ResOperation(rop.FAIL, [], None)]
        loop = self.newloop([n], ops)
        optimize_loop(None, [], loop)
        equaloplists(loop.operations, [
            ResOperation(rop.GUARD_VALUE, [n, ConstInt(0)], None),
            ])

    def test_remove_consecutive_getfields(self):
        py.test.skip('in-progress')
        n1 = BoxInt()
        n2 = BoxInt()
        n3 = BoxInt()
        ops = [
            ResOperation(rop.GETFIELD_GC, [self.nodebox], n1, self.nodedescr),
            ResOperation(rop.GETFIELD_GC, [self.nodebox], n2, self.nodedescr),
            ResOperation(rop.INT_ADD, [n1, n2], n3),
        ]
        loop = self.newloop([self.nodebox], ops)
        optimize_loop(None, [], loop)
        equaloplists(loop.operations, [
            ResOperation(rop.GETFIELD_GC, [self.nodebox], n1, self.nodedescr),
            ResOperation(rop.INT_ADD, [n1, n1], n3),
            ])

    def test_setfield_getfield_clean_cache(self):
        py.test.skip('in-progress')
        n1 = BoxInt()
        n2 = BoxInt()
        n3 = BoxInt()
        ops = [
            ResOperation(rop.GETFIELD_GC, [self.nodebox], n1, self.nodedescr),
            ResOperation(rop.SETFIELD_GC, [self.nodebox, ConstInt(3)], None, self.nodedescr),
            ResOperation(rop.GETFIELD_GC, [self.nodebox], n2, self.nodedescr),
            ResOperation(rop.CALL, [n2], None),
        ]
        loop = self.newloop([self.nodebox], ops)
        optimize_loop(None, [], loop)
        equaloplists(loop.operations, [
            ResOperation(rop.GETFIELD_GC, [self.nodebox], n1, self.nodedescr),
            ResOperation(rop.SETFIELD_GC, [self.nodebox, ConstInt(3)], None, self.nodedescr),
            ResOperation(rop.CALL, [ConstInt(3)], None),
            ])


class TestLLtype(LLtypeMixin, BaseTestOptimize3):
    pass

class TestOOtype(OOtypeMixin, BaseTestOptimize3):
    pass
