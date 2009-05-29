import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.metainterp.resoperation import rop, ResOperation, opname
from pypy.jit.metainterp.history import ConstAddr, BoxPtr, TreeLoop,\
     ConstInt, BoxInt, BoxObj, ConstObj
from pypy.jit.backend.llgraph import runner

from pypy.jit.metainterp.optimize2 import (optimize_loop,
     ConsecutiveGuardClassRemoval, Specializer, SimpleVirtualizableOpt,
     SimpleVirtualOpt)
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
    nodesize = cpu.sizeof(NODE)

    TP = lltype.GcArray(lltype.Signed)
    NODE_ARRAY = lltype.GcArray(lltype.Ptr(NODE))

    XY = lltype.GcStruct('XY', ('parent', OBJECT),
                         ('inst_field', lltype.Signed),
                         ('inst_other_field', lltype.Signed),
                         ('inst_list', lltype.Ptr(TP)),
                         ('inst_item_list', lltype.Ptr(NODE_ARRAY)),
                         hints= {'virtualizable2': True,
                                 'virtuals': ('field','list', 'item_list')})
    field_desc = cpu.fielddescrof(XY, 'inst_field')
    array_descr = cpu.arraydescrof(TP)
    list_desc = cpu.fielddescrof(XY, 'inst_list')
    list_node_desc = cpu.fielddescrof(XY, 'inst_item_list')
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
    nodesize = cpu.sizeof(node)

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
        for op in range(rop.INT_ADD, rop._COMPARISON_FIRST):
            try:
                op = opname[op]
            except KeyError:
                continue
            pre_op = """
            []
            i1 = %s(3, 2)
            """ % op.lower()
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
        pre_op = self.parse(pre_op)
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
        pre_op = self.parse(pre_op)
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

    def test_newly_allocated_virtualizable_is_not_virtualized(self):
        pre_op = """
        []
        p0 = new_with_vtable(ConstClass(xy_vtable))
        guard_nonvirtualized(p0, vdesc=vdesc)
            fail()
        setfield_gc(p0, 3, descr=field_desc)
        """
        expected = """
        []
        p0 = new_with_vtable(ConstClass(xy_vtable))
        setfield_gc(p0, 3, descr=field_desc)
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualizableOpt()]),
                          expected)

    def test_escape_analysis(self):
        ops = """
        [i0]
        i1 = int_add(i0, i0)
        """
        spec = Specializer([])
        loop = self.parse(ops)
        optimize_loop(None, [], loop, self.cpu, spec=spec)
        assert spec.nodes[loop.operations[0].args[0]].escaped
        ops = """
        [p0]
        i1 = getfield_gc(p0, descr=field_desc)
        i2 = int_add(i1, i1)
        """
        spec = Specializer([])
        loop = self.parse(ops)
        optimize_loop(None, [], loop, self.cpu, spec=spec)
        assert not spec.nodes[loop.operations[0].result].escaped
        ops = """
        [p0]
        i1 = getfield_gc(p0, descr=field_desc)
        fail(i1)
        """
        spec = Specializer([])
        loop = self.parse(ops)
        optimize_loop(None, [], loop, self.cpu, spec=spec)
        assert spec.nodes[loop.operations[0].result].escaped
        ops = """
        [p0]
        i1 = getfield_gc(p0, descr=field_desc)
        guard_true(i1)
            fail()
        """
        spec = Specializer([])
        loop = self.parse(ops)
        optimize_loop(None, [], loop, self.cpu, spec=spec)
        assert not spec.nodes[loop.operations[0].result].escaped

    def test_escape_analysis_on_virtualizable(self):
        ops = """
        [p0]
        guard_nonvirtualized(p0, vdesc=vdesc)
            fail()
        i1 = getfield_gc(p0, descr=field_desc)
        setfield_gc(p0, i1, descr=field_desc)
        i2 = int_add(i1, i1)
        """
        spec = Specializer([SimpleVirtualizableOpt()])
        loop = self.parse(ops)
        optimize_loop(None, [], loop, self.cpu, spec=spec)
        assert not spec.nodes[loop.operations[0].result].escaped

    def test_simple_virtual(self):
        pre_op = """
        []
        p0 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p0, 1, descr=field_desc)
        i2 = getfield_gc(p0, descr=field_desc)
        fail(i2)
        """
        expected = """
        []
        fail(1)
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualOpt()]),
                          expected)

    def test_virtual_with_virtualizable(self):
        pre_op = """
        [p0]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, 1, descr=nodedescr)
        guard_nonvirtualized(p0, vdesc=vdesc)
            fail()
        p2 = getfield_gc(p0, descr=list_node_desc)
        setarrayitem_gc(p2, 0, p1)
        p3 = getarrayitem_gc(p2, 0)
        i3 = getfield_gc(p3, descr=nodedescr)
        fail(i3)
        """
        expected = """
        [p0]
        p2 = getfield_gc(p0, descr=list_node_desc)
        fail(1)
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualizableOpt(),
                                                 SimpleVirtualOpt()]),
                          expected)

    def test_rebuild_ops(self):
        pre_op = """
        [i1]
        p1 = new_with_vtable(ConstClass(node_vtable), descr=nodesize)
        setfield_gc(p1, 1, descr=field_desc)
        guard_true(i1)
            fail(p1)
        """
        expected = """
        [i1]
        guard_true(i1)
            p1 = new_with_vtable(ConstClass(node_vtable), descr=nodesize)
            setfield_gc(p1, 1, descr=field_desc)
            fail(p1)
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualOpt()]),
                          expected)


    def test_virtual_with_virtualizable_escapes(self):
        pre_op = """
        [p0]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, 1, descr=nodedescr)
        guard_nonvirtualized(p0, vdesc=vdesc)
            fail()
        p2 = getfield_gc(p0, descr=list_node_desc)
        setarrayitem_gc(p2, 0, p1)
        p3 = getarrayitem_gc(p2, 0)
        fail(p3)
        """
        expected = """
        [p0]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, 1, descr=nodedescr)
        p2 = getfield_gc(p0, descr=list_node_desc)
        fail(p1)
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualizableOpt(),
                                                 SimpleVirtualOpt()]),
                          expected)

    def test_virtualizable_double_read(self):
        pre_op = """
        [p0]
        p3 = new_with_vtable(ConstClass(node_vtable))
        guard_nonvirtualized(p0, vdesc=vdesc)
            fail()
        p1 = getfield_gc(p0, descr=list_node_desc)
        setarrayitem_gc(p1, 0, p3)
        p2 = getfield_gc(p0, descr=list_node_desc)
        p4 = getarrayitem_gc(p2, 0)
        fail(p4)
        """
        expected = """
        [p0]
        p3 = new_with_vtable(ConstClass(node_vtable))
        p1 = getfield_gc(p0, descr=list_node_desc)
        fail(p3)
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualizableOpt(),
                                                 SimpleVirtualOpt()]),
                          expected)

    def test_virtual_without_vtable(self):
        pre_op = """
        [i1]
        p0 = new()
        guard_true(i1)
            fail(p0)
        """
        expected = """
        [i1]
        guard_true(i1)
            p0 = new()
            fail(p0)
        """
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualOpt()]),
                          expected)

    def test_oononnull_on_virtual(self):
        pre_op = """
        []
        p0 = new()
        i1 = oononnull(p0)
        guard_true(i1)
            fail()
        i2 = ooisnull(p0)
        guard_false(i2)
            fail()
        """
        expected = "[]"
        self.assert_equal(self.optimize(pre_op, [SimpleVirtualOpt()]),
                          expected)

class TestLLtype(LLtypeMixin, BaseTestOptimize2):
    pass

class TestOOtype(OOtypeMixin, BaseTestOptimize2):
    def test_virtual_with_virtualizable(self):
        py.test.skip("XXX")

    test_virtual_with_virtualizable_escapes = test_virtual_with_virtualizable
    test_virtualizable_double_read = test_virtual_with_virtualizable
