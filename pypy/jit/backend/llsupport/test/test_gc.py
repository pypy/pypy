import random
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.backend.llsupport.descr import *
from pypy.jit.backend.llsupport.gc import *
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.metainterp.gc import get_description


def test_boehm():
    gc_ll_descr = GcLLDescr_boehm(None, None)
    #
    record = []
    prev_funcptr_for_new = gc_ll_descr.funcptr_for_new
    def my_funcptr_for_new(size):
        p = prev_funcptr_for_new(size)
        record.append((size, p))
        return p
    gc_ll_descr.funcptr_for_new = my_funcptr_for_new
    #
    # ---------- gc_malloc ----------
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    sizedescr = get_size_descr(gc_ll_descr, S)
    p = gc_ll_descr.gc_malloc(sizedescr)
    assert record == [(sizedescr.size, p)]
    del record[:]
    # ---------- gc_malloc_array ----------
    A = lltype.GcArray(lltype.Signed)
    arraydescr = get_array_descr(gc_ll_descr, A)
    p = gc_ll_descr.gc_malloc_array(arraydescr, 10)
    assert record == [(arraydescr.get_base_size(False) +
                       10 * arraydescr.get_item_size(False), p)]
    del record[:]
    # ---------- gc_malloc_str ----------
    p = gc_ll_descr.gc_malloc_str(10)
    basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR, False)
    assert record == [(basesize + 10 * itemsize, p)]
    del record[:]
    # ---------- gc_malloc_unicode ----------
    p = gc_ll_descr.gc_malloc_unicode(10)
    basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                              False)
    assert record == [(basesize + 10 * itemsize, p)]
    del record[:]

# ____________________________________________________________

def test_GcRefList():
    S = lltype.GcStruct('S')
    order = range(50) * 4
    random.shuffle(order)
    allocs = [lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S))
              for i in range(50)]
    allocs = [allocs[i] for i in order]
    #
    gcrefs = GcRefList()
    gcrefs.initialize()
    addrs = [gcrefs.get_address_of_gcref(ptr) for ptr in allocs]
    for i in range(len(allocs)):
        assert addrs[i].address[0] == llmemory.cast_ptr_to_adr(allocs[i])

def test_GcRootMap_asmgcc():
    def frame_pos(n):
        return -4*(4+n)
    gcrootmap = GcRootMap_asmgcc()
    num1 = frame_pos(1)
    num2 = frame_pos(55)
    shape = gcrootmap.get_basic_shape()
    gcrootmap.add_ebp_offset(shape, num1)
    gcrootmap.add_ebp_offset(shape, num2)
    assert shape == [6, -2, -6, -10, 2, 0, num1|2, num2|2]
    gcrootmap.add_ebx(shape)
    assert shape == [6, -2, -6, -10, 2, 0, num1|2, num2|2, 0|1]
    gcrootmap.add_esi(shape)
    assert shape == [6, -2, -6, -10, 2, 0, num1|2, num2|2, 0|1, 4|1]
    gcrootmap.add_edi(shape)
    assert shape == [6, -2, -6, -10, 2, 0, num1|2, num2|2, 0|1, 4|1, 8|1]
    gcrootmap.add_ebp(shape)
    assert shape == [6, -2, -6, -10, 2, 0, num1|2, num2|2, 0|1, 4|1, 8|1, 12|1]
    #
    shapeaddr = gcrootmap.compress_callshape(shape)
    PCALLSHAPE = lltype.Ptr(GcRootMap_asmgcc.CALLSHAPE_ARRAY)
    p = llmemory.cast_adr_to_ptr(shapeaddr, PCALLSHAPE)
    num1a = -2*(num1|2)-1
    num2a = ((-2*(num2|2)-1) >> 7) | 128
    num2b = (-2*(num2|2)-1) & 127
    for i, expected in enumerate([26, 18, 10, 2,
                                  num2a, num2b, num1a, 0, 4, 19, 11, 3, 12]):
        assert p[i] == expected
    #
    retaddr = rffi.cast(llmemory.Address, 1234567890)
    gcrootmap.put(retaddr, shapeaddr)
    assert gcrootmap._gcmap[0] == retaddr
    assert gcrootmap._gcmap[1] == shapeaddr
    assert gcrootmap.gcmapstart().address[0] == retaddr
    #
    # the same as before, but enough times to trigger a few resizes
    expected_shapeaddr = {}
    for i in range(1, 600):
        shape = gcrootmap.get_basic_shape()
        gcrootmap.add_ebp_offset(shape, frame_pos(i))
        shapeaddr = gcrootmap.compress_callshape(shape)
        expected_shapeaddr[i] = shapeaddr
        retaddr = rffi.cast(llmemory.Address, 123456789 + i)
        gcrootmap.put(retaddr, shapeaddr)
    for i in range(1, 600):
        expected_retaddr = rffi.cast(llmemory.Address, 123456789 + i)
        assert gcrootmap._gcmap[i*2+0] == expected_retaddr
        assert gcrootmap._gcmap[i*2+1] == expected_shapeaddr[i]


class FakeLLOp:
    def __init__(self):
        self.record = []

    def do_malloc_fixedsize_clear(self, RESTYPE, type_id, size, can_collect,
                                  has_finalizer, contains_weakptr):
        assert can_collect
        assert not contains_weakptr
        p = llmemory.raw_malloc(size)
        p = llmemory.cast_adr_to_ptr(p, RESTYPE)
        flags = int(has_finalizer) << 16
        tid = llop.combine_ushort(lltype.Signed, type_id, flags)
        self.record.append(("fixedsize", repr(size), tid, p))
        return p

    def do_malloc_varsize_clear(self, RESTYPE, type_id, length, size,
                                itemsize, offset_to_length, can_collect):
        assert can_collect
        p = llmemory.raw_malloc(size + itemsize * length)
        (p + offset_to_length).signed[0] = length
        p = llmemory.cast_adr_to_ptr(p, RESTYPE)
        tid = llop.combine_ushort(lltype.Signed, type_id, 0)
        self.record.append(("varsize", tid, length,
                            repr(size), repr(itemsize),
                            repr(offset_to_length), p))
        return p

    def _write_barrier_failing_case(self, adr_struct, adr_newptr):
        self.record.append(('barrier', adr_struct, adr_newptr))

    def get_write_barrier_failing_case(self, FPTRTYPE):
        return llhelper(FPTRTYPE, self._write_barrier_failing_case)


class TestFramework:

    def setup_method(self, meth):
        class config_:
            class translation:
                gc = 'hybrid'
                gcrootfinder = 'asmgcc'
                gctransformer = 'framework'
                gcremovetypeptr = False
        class FakeTranslator:
            config = config_
        class FakeCPU:
            def cast_adr_to_int(self, adr):
                ptr = llmemory.cast_adr_to_ptr(adr, gc_ll_descr.WB_FUNCPTR)
                assert ptr._obj._callable == llop1._write_barrier_failing_case
                return 42
        gcdescr = get_description(config_)
        translator = FakeTranslator()
        llop1 = FakeLLOp()
        gc_ll_descr = GcLLDescr_framework(gcdescr, FakeTranslator(), llop1)
        gc_ll_descr.initialize()
        self.llop1 = llop1
        self.gc_ll_descr = gc_ll_descr
        self.fake_cpu = FakeCPU()

    def test_args_for_new(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        sizedescr = get_size_descr(self.gc_ll_descr, S)
        args = self.gc_ll_descr.args_for_new(sizedescr)
        for x in args:
            assert lltype.typeOf(x) == lltype.Signed
        A = lltype.GcArray(lltype.Signed)
        arraydescr = get_array_descr(self.gc_ll_descr, A)
        args = self.gc_ll_descr.args_for_new(sizedescr)
        for x in args:
            assert lltype.typeOf(x) == lltype.Signed

    def test_gc_malloc(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        sizedescr = get_size_descr(self.gc_ll_descr, S)
        p = self.gc_ll_descr.gc_malloc(sizedescr)
        assert self.llop1.record == [("fixedsize",
                                      repr(sizedescr.size),
                                      sizedescr.tid, p)]
        assert repr(self.gc_ll_descr.args_for_new(sizedescr)) == repr(
            [sizedescr.size, sizedescr.tid])

    def test_gc_malloc_array(self):
        A = lltype.GcArray(lltype.Signed)
        arraydescr = get_array_descr(self.gc_ll_descr, A)
        p = self.gc_ll_descr.gc_malloc_array(arraydescr, 10)
        assert self.llop1.record == [("varsize", arraydescr.tid, 10,
                                      repr(arraydescr.get_base_size(True)),
                                      repr(arraydescr.get_item_size(True)),
                                      repr(arraydescr.get_ofs_length(True)),
                                      p)]
        assert repr(self.gc_ll_descr.args_for_new_array(arraydescr)) == repr(
            [arraydescr.get_item_size(True), arraydescr.tid])

    def test_gc_malloc_str(self):
        p = self.gc_ll_descr.gc_malloc_str(10)
        type_id = self.gc_ll_descr.layoutbuilder.get_type_id(rstr.STR)
        tid = llop.combine_ushort(lltype.Signed, type_id, 0)
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                                  True)
        assert self.llop1.record == [("varsize", tid, 10,
                                      repr(basesize), repr(itemsize),
                                      repr(ofs_length), p)]

    def test_gc_malloc_unicode(self):
        p = self.gc_ll_descr.gc_malloc_unicode(10)
        type_id = self.gc_ll_descr.layoutbuilder.get_type_id(rstr.UNICODE)
        tid = llop.combine_ushort(lltype.Signed, type_id, 0)
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                                  True)
        assert self.llop1.record == [("varsize", tid, 10,
                                      repr(basesize), repr(itemsize),
                                      repr(ofs_length), p)]

    def test_do_write_barrier(self):
        gc_ll_descr = self.gc_ll_descr
        R = lltype.GcStruct('R')
        S = lltype.GcStruct('S', ('r', lltype.Ptr(R)))
        s = lltype.malloc(S)
        r = lltype.malloc(R)
        s_hdr = gc_ll_descr.gcheaderbuilder.new_header(s)
        s_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
        r_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, r)
        s_adr = llmemory.cast_ptr_to_adr(s)
        r_adr = llmemory.cast_ptr_to_adr(r)
        #
        s_hdr.tid &= ~gc_ll_descr.GCClass.JIT_WB_IF_FLAG
        gc_ll_descr.do_write_barrier(s_gcref, r_gcref)
        assert self.llop1.record == []    # not called
        #
        s_hdr.tid |= gc_ll_descr.GCClass.JIT_WB_IF_FLAG
        gc_ll_descr.do_write_barrier(s_gcref, r_gcref)
        assert self.llop1.record == [('barrier', s_adr, r_adr)]

    def test_gen_write_barrier(self):
        gc_ll_descr = self.gc_ll_descr
        llop1 = self.llop1
        #
        newops = []
        v_base = BoxPtr()
        v_value = BoxPtr()
        gc_ll_descr._gen_write_barrier(newops, v_base, v_value)
        assert llop1.record == []
        assert len(newops) == 1
        assert newops[0].opnum == rop.COND_CALL_GC_WB
        assert newops[0].args[0] == v_base
        assert newops[0].args[1] == v_value
        assert newops[0].result is None
        wbdescr = newops[0].descr
        assert isinstance(wbdescr.jit_wb_if_flag, int)
        assert isinstance(wbdescr.jit_wb_if_flag_byteofs, int)
        assert isinstance(wbdescr.jit_wb_if_flag_singlebyte, int)

    def test_get_rid_of_debug_merge_point(self):
        operations = [
            ResOperation(rop.DEBUG_MERGE_POINT, [], None),
            ]
        gc_ll_descr = self.gc_ll_descr
        gc_ll_descr.rewrite_assembler(None, operations)
        assert len(operations) == 0

    def test_rewrite_assembler_1(self):
        # check rewriting of ConstPtrs
        class MyFakeCPU:
            def cast_adr_to_int(self, adr):
                assert adr == "some fake address"
                return 43
        class MyFakeGCRefList:
            def get_address_of_gcref(self, s_gcref1):
                assert s_gcref1 == s_gcref
                return "some fake address"
        S = lltype.GcStruct('S')
        s = lltype.malloc(S)
        s_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
        v_random_box = BoxPtr()
        v_result = BoxInt()
        operations = [
            ResOperation(rop.OOIS, [v_random_box, ConstPtr(s_gcref)],
                         v_result),
            ]
        gc_ll_descr = self.gc_ll_descr
        gc_ll_descr.gcrefs = MyFakeGCRefList()
        gc_ll_descr.rewrite_assembler(MyFakeCPU(), operations)
        assert len(operations) == 2
        assert operations[0].opnum == rop.GETFIELD_RAW
        assert operations[0].args == [ConstInt(43)]
        assert operations[0].descr == gc_ll_descr.single_gcref_descr
        v_box = operations[0].result
        assert isinstance(v_box, BoxPtr)
        assert operations[1].opnum == rop.OOIS
        assert operations[1].args == [v_random_box, v_box]
        assert operations[1].result == v_result

    def test_rewrite_assembler_1_cannot_move(self):
        # check rewriting of ConstPtrs
        class MyFakeCPU:
            def cast_adr_to_int(self, adr):
                xxx    # should not be called
        class MyFakeGCRefList:
            def get_address_of_gcref(self, s_gcref1):
                seen.append(s_gcref1)
                assert s_gcref1 == s_gcref
                return "some fake address"
        seen = []
        S = lltype.GcStruct('S')
        s = lltype.malloc(S)
        s_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
        v_random_box = BoxPtr()
        v_result = BoxInt()
        operations = [
            ResOperation(rop.OOIS, [v_random_box, ConstPtr(s_gcref)],
                         v_result),
            ]
        gc_ll_descr = self.gc_ll_descr
        gc_ll_descr.gcrefs = MyFakeGCRefList()
        old_can_move = rgc.can_move
        try:
            rgc.can_move = lambda s: False
            gc_ll_descr.rewrite_assembler(MyFakeCPU(), operations)
        finally:
            rgc.can_move = old_can_move
        assert len(operations) == 1
        assert operations[0].opnum == rop.OOIS
        assert operations[0].args == [v_random_box, ConstPtr(s_gcref)]
        assert operations[0].result == v_result
        # check that s_gcref gets added to the list anyway, to make sure
        # that the GC sees it
        assert seen == [s_gcref]

    def test_rewrite_assembler_2(self):
        # check write barriers before SETFIELD_GC
        v_base = BoxPtr()
        v_value = BoxPtr()
        field_descr = AbstractDescr()
        operations = [
            ResOperation(rop.SETFIELD_GC, [v_base, v_value], None,
                         descr=field_descr),
            ]
        gc_ll_descr = self.gc_ll_descr
        gc_ll_descr.rewrite_assembler(self.fake_cpu, operations)
        assert len(operations) == 2
        #
        assert operations[0].opnum == rop.COND_CALL_GC_WB
        assert operations[0].args[0] == v_base
        assert operations[0].args[1] == v_value
        assert operations[0].result is None
        #
        assert operations[1].opnum == rop.SETFIELD_RAW
        assert operations[1].args == [v_base, v_value]
        assert operations[1].descr == field_descr

    def test_rewrite_assembler_3(self):
        # check write barriers before SETARRAYITEM_GC
        v_base = BoxPtr()
        v_index = BoxInt()
        v_value = BoxPtr()
        array_descr = AbstractDescr()
        operations = [
            ResOperation(rop.SETARRAYITEM_GC, [v_base, v_index, v_value], None,
                         descr=array_descr),
            ]
        gc_ll_descr = self.gc_ll_descr
        gc_ll_descr.rewrite_assembler(self.fake_cpu, operations)
        assert len(operations) == 2
        #
        assert operations[0].opnum == rop.COND_CALL_GC_WB
        assert operations[0].args[0] == v_base
        assert operations[0].args[1] == v_value
        assert operations[0].result is None
        #
        assert operations[1].opnum == rop.SETARRAYITEM_RAW
        assert operations[1].args == [v_base, v_index, v_value]
        assert operations[1].descr == array_descr
