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
from pypy.jit.metainterp.test.test_optimize import ANY

from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.metainterp.virtualizable import VirtualizableDesc

def equaloplists(oplist1, oplist2):
    #saved = Box._extended_display
    #try:
    #    Box._extended_display = False
    print '-'*20, 'Comparing lists', '-'*20
    for op1, op2 in zip(oplist1, oplist2):
        txt1 = str(op1)
        txt2 = str(op2)
        while txt1 or txt2:
            print '%-39s| %s' % (txt1[:39], txt2[:39])
            txt1 = txt1[39:]
            txt2 = txt2[39:]
        assert op1.opnum == op2.opnum
        assert len(op1.args) == len(op2.args)
        for x, y in zip(op1.args, op2.args):
            assert x == y or y == x     # for ANY object :-(
        assert op1.result == op2.result
        assert op1.descr == op2.descr
        if op1.suboperations or op2.suboperations:
            equaloplists(op1.suboperations, op2.suboperations)
    assert len(oplist1) == len(oplist2)
    print '-'*57
    #finally:
    #    Box._extended_display = saved
    return True

class LLtypeMixin(object):
    type_system = 'lltype'

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

    TP = lltype.GcArray(lltype.Signed)

    XY = lltype.GcStruct('XY', ('parent', OBJECT),
                         ('inst_field', lltype.Signed),
                         ('inst_other_field', lltype.Signed),
                         ('inst_list', lltype.Ptr(TP)),
                         hints= {'virtualizable2': True,
                                 'virtuals': ('field','list')})
    field_desc = cpu.fielddescrof(XY, 'inst_field')
    array_descr = cpu.arraydescrof(TP)
    list_desc = cpu.fielddescrof(XY, 'inst_list')
    other_field_desc = cpu.fielddescrof(XY, 'inst_other_field')
    vdesc = VirtualizableDesc(cpu, XY, XY)
    xy_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)

    namespace = locals()

class OOtypeMixin(object):
    type_system = 'ootype'
    
    cpu = runner.OOtypeCPU(None)

    NODE = ootype.Instance('NODE', ootype.ROOT, {})
    NODE._add_fields({'value': ootype.Signed,
                      'next': NODE})

    node_vtable = ootype.runtimeClass(NODE)
    vtable_box = ConstObj(ootype.cast_to_object(node_vtable))

    node = ootype.new(NODE)
    nodebox = BoxObj(ootype.cast_to_object(node))
    nodedescr = cpu.fielddescrof(NODE, 'value')

    TP = ootype.Array(ootype.Signed)

    XY = ootype.Instance('XY', ootype.ROOT,
                         {'ofield': ootype.Signed,
                          'oother_field': ootype.Signed,
                          'olist': TP},
                         _hints = {'virtualizable2': True,
                                 'virtuals': ('field','list')})
    
    field_desc = cpu.fielddescrof(XY, 'ofield')
    array_descr = cpu.arraydescrof(TP)
    list_desc = cpu.fielddescrof(XY, 'olist')
    other_field_desc = cpu.fielddescrof(XY, 'oother_field')
    vdesc = VirtualizableDesc(cpu, XY, XY)
    xy_vtable = ootype.runtimeClass(XY)

    namespace = locals()

class BaseTestOptimize2(object):

    def parse(self, s):
        return parse(s, self.cpu, self.namespace,
                     type_system=self.type_system)

    def optimize(self, lst, optimizations_enabled=[]):
        if not isinstance(lst, TreeLoop):
            loop = self.parse(lst)
        else:
            loop = lst
        optimize_loop(None, [], loop, self.cpu,
                      spec=Specializer(optimizations_enabled))
        return loop.operations

    def assert_equal(self, optimized, expected):
        equaloplists(optimized, self.parse(expected).operations)

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
        self.assert_equal(self.optimize(pre_op,
                                        [ConsecutiveGuardClassRemoval()]),
                          expected)

    def test_basic_virtualizable(self):
        pre_op = """
        [p0]
        guard_nonvirtualized(p0, ConstClass(xy_vtable), vdesc=vdesc)
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

    def test_virtualizable_setfield_rebuild_ops(self):
        pre_op = """
        [p0]
        guard_nonvirtualized(p0, ConstClass(xy_vtable), vdesc=vdesc)
            fail()
        i1 = getfield_gc(p0, descr=field_desc)
        i2 = getfield_gc(p0, descr=other_field_desc)
        setfield_gc(p0, i2, descr=field_desc)
        # ^^^ this should be gone
        i3 = getfield_gc(p0, descr=field_desc)
        # ^^^ this one as well
        guard_true(i3)
            fail()
        """
        expected = """
        [p0]
        i1 = getfield_gc(p0, descr=field_desc)
        i2 = getfield_gc(p0, descr=other_field_desc)
        guard_true(i2)
            guard_nonvirtualized(p0)
                fail()
            setfield_gc(p0, i2, descr=field_desc)
            fail()
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualizableOpt()]),
                          expected)

    def test_const_guard_value(self):
        pre_op = """
        []
        guard_value(0, 0)
            fail()
        """
        expected = "[]"
        self.assert_equal(self.optimize(pre_op, []), expected)

    def test_don_t_fold_guard_no_exception(self):
        pre_op = """
        []
        guard_no_exception()
            fail()
        """
        self.assert_equal(self.optimize(pre_op, []), pre_op)

    def test_virtualized_list_on_virtualizable(self):
        pre_op = """
        [p0]
        guard_nonvirtualized(p0, ConstClass(xy_vtable), vdesc=vdesc)
            fail()
        p1 = getfield_gc(p0, descr=list_desc)
        setarrayitem_gc(p1, 0, 1, descr=array_descr)
        i1 = getarrayitem_gc(p1, 0)
        i2 = int_add(i1, i1)
        i3 = int_is_true(i2)
        guard_true(i3)
            fail()
        """
        pre_op = parse(pre_op, self.cpu, self.namespace)
        # cheat
        pre_op.operations[-2].result.value = 1
        expected = """
        [p0]
        p1 = getfield_gc(p0, descr=list_desc)
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualizableOpt()]),
                          expected)        


    def test_virtualized_list_on_virtualizable_2(self):
        pre_op = """
        [p0, i0]
        guard_nonvirtualized(p0, ConstClass(xy_vtable), vdesc=vdesc)
            fail()
        p1 = getfield_gc(p0, descr=list_desc)
        setarrayitem_gc(p1, 0, i0, descr=array_descr)
        i1 = getarrayitem_gc(p1, 0)
        i2 = int_add(i1, i1)
        i3 = int_is_true(i2)
        guard_true(i3)
            fail()
        """
        pre_op = parse(pre_op, self.cpu, self.namespace)
        expected = """
        [p0, i0]
        p1 = getfield_gc(p0, descr=list_desc)
        i2 = int_add(i0, i0)
        i3 = int_is_true(i2)
        guard_true(i3)
            guard_nonvirtualized(p1)
                fail()
            setarrayitem_gc(p1, 0, i0, descr=array_descr)
            fail()
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualizableOpt()]),
                          expected)        

    def test_virtualized_list_on_virtualizable_3(self):
        pre_op = """
        [p0, i0, i1]
        guard_nonvirtualized(p0, ConstClass(xy_vtable), vdesc=vdesc)
            fail()
        p1 = getfield_gc(p0, descr=list_desc)
        setarrayitem_gc(p1, 0, i0, descr=array_descr)
        i2 = getarrayitem_gc(p1, 0)
        setarrayitem_gc(p1, 0, i1, descr=array_descr)
        i3 = getarrayitem_gc(p1, 0)
        i4 = int_add(i2, i3)
        i5 = int_is_true(i4)
        guard_true(i5)
            fail()
        """
        pre_op = parse(pre_op, self.cpu, self.namespace)
        expected = """
        [p0, i0, i1]
        p1 = getfield_gc(p0, descr=list_desc)
        i4 = int_add(i0, i1)
        i5 = int_is_true(i4)
        guard_true(i5)
            guard_nonvirtualized(p1)
                fail()
            setarrayitem_gc(p1, 0, i1, descr=array_descr)
            fail()
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
        py.test.skip("XXX")
