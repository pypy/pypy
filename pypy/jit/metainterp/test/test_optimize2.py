import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.history import ConstAddr, BoxPtr, TreeLoop,\
     ConstInt, BoxInt, BoxObj, ConstObj
from pypy.jit.backend.llgraph import runner

from pypy.jit.metainterp.optimize2 import (optimize_loop,
     ConsecutiveGuardClassRemoval, Specializer, SimpleVirtualizableOpt)
from pypy.jit.metainterp.test.test_optimize import equaloplists, ANY

from pypy.jit.metainterp.test.oparser import parse

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

    XY = lltype.GcStruct('XY', ('field', lltype.Signed),
                         hints= {'virtualizable2': True})
    field_desc = cpu.fielddescrof(XY, 'field')

    namespace = locals()

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

    namespace = locals()

class BaseTestOptimize2(object):

    def optimize(self, lst, optimizations_enabled=[]):
        loop = parse(lst, self.cpu, self.namespace)
        optimize_loop(None, [], loop, self.cpu,
                      spec=Specializer(optimizations_enabled))
        return loop.operations

    def assert_equal(self, optimized, expected):
        equaloplists(optimized,
                     parse(expected, self.cpu, self.namespace).operations)

    def test_basic_constant_folding(self):
        pre_op = """
        []
        i1 = int_add(3, 2)
        """
        expected = "[]"
        self.assert_equal(self.optimize(pre_op), expected)
    
    def test_remove_guard_class(self):
        pre_op = """
        [p0]
        guard_class(p0, ConstAddr(node_vtable))
          fail()
        guard_class(p0, ConstAddr(node_vtable))
          fail()
        """
        expected = """
        [p0]
        guard_class(p0, ConstAddr(node_vtable))
          fail()
        """
        self.assert_equal(self.optimize(pre_op,
                                        [ConsecutiveGuardClassRemoval()]),
                          expected)

    def test_basic_virtualizable(self):
        py.test.skip("xxx")
        pre_op = """
        [p0]
        guard_nonvirtualized(p0)
            fail()
        i1 = getfield_gc(p0, descr=field_desc)
        i2 = getfield_gc(p0, descr=field_desc)
        i3 = int_add(i1, i2)
        """
        expected = """
        [p0]
        i1 = getfield_gc(p0, descr=field_desc)
        i3 = int_add(i1, i1)
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualizableOpt()]),
                          expected)
        

    def test_remove_consecutive_guard_value_constfold(self):
        py.test.skip("not yet")
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
        py.test.skip("not yet")
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
        py.test.skip("not yet")
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


class TestLLtype(LLtypeMixin, BaseTestOptimize2):
    pass

class TestOOtype(OOtypeMixin, BaseTestOptimize2):
    def setup_class(cls):
        py.test.skip("XXX Fix me")
