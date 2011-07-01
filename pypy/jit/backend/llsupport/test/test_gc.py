import random
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.backend.llsupport.descr import *
from pypy.jit.backend.llsupport.gc import *
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.metainterp.gc import get_description
from pypy.jit.metainterp.resoperation import get_deep_immutable_oplist
from pypy.jit.tool.oparser import parse
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE
from pypy.jit.metainterp.optimizeopt.util import equaloplists

def test_boehm():
    gc_ll_descr = GcLLDescr_boehm(None, None, None)
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


class TestGcRootMapAsmGcc:

    def test_make_shapes(self):
        def frame_pos(n):
            return -4*(4+n)
        gcrootmap = GcRootMap_asmgcc()
        num1 = frame_pos(-5)
        num1a = num1|2
        num2 = frame_pos(55)
        num2a = ((-num2|3) >> 7) | 128
        num2b = (-num2|3) & 127
        shape = gcrootmap.get_basic_shape()
        gcrootmap.add_frame_offset(shape, num1)
        gcrootmap.add_frame_offset(shape, num2)
        assert shape == map(chr, [6, 7, 11, 15, 2, 0, num1a, num2b, num2a])
        gcrootmap.add_callee_save_reg(shape, 1)
        assert shape == map(chr, [6, 7, 11, 15, 2, 0, num1a, num2b, num2a,
                                  4])
        gcrootmap.add_callee_save_reg(shape, 2)
        assert shape == map(chr, [6, 7, 11, 15, 2, 0, num1a, num2b, num2a,
                                  4, 8])
        gcrootmap.add_callee_save_reg(shape, 3)
        assert shape == map(chr, [6, 7, 11, 15, 2, 0, num1a, num2b, num2a,
                                  4, 8, 12])
        gcrootmap.add_callee_save_reg(shape, 4)
        assert shape == map(chr, [6, 7, 11, 15, 2, 0, num1a, num2b, num2a,
                                  4, 8, 12, 16])

    def test_compress_callshape(self):
        class FakeDataBlockWrapper:
            def malloc_aligned(self, size, alignment):
                assert alignment == 1    # here
                assert size == 4
                return rffi.cast(lltype.Signed, p)
        datablockwrapper = FakeDataBlockWrapper()
        p = lltype.malloc(rffi.CArray(lltype.Char), 4, immortal=True)
        gcrootmap = GcRootMap_asmgcc()
        shape = ['a', 'b', 'c', 'd']
        gcrootmap.compress_callshape(shape, datablockwrapper)
        assert p[0] == 'd'
        assert p[1] == 'c'
        assert p[2] == 'b'
        assert p[3] == 'a'

    def test_put_basic(self):
        gcrootmap = GcRootMap_asmgcc()
        retaddr = 1234567890
        shapeaddr = 51627384
        gcrootmap.put(retaddr, shapeaddr)
        assert gcrootmap._gcmap[0] == retaddr
        assert gcrootmap._gcmap[1] == shapeaddr
        p = rffi.cast(rffi.LONGP, gcrootmap.gcmapstart())
        assert p[0] == retaddr
        assert (gcrootmap.gcmapend() ==
                gcrootmap.gcmapstart() + rffi.sizeof(lltype.Signed) * 2)

    def test_put_resize(self):
        # the same as before, but enough times to trigger a few resizes
        gcrootmap = GcRootMap_asmgcc()
        for i in range(700):
            shapeaddr = i * 100 + 1
            retaddr = 123456789 + i
            gcrootmap.put(retaddr, shapeaddr)
        for i in range(700):
            assert gcrootmap._gcmap[i*2+0] == 123456789 + i
            assert gcrootmap._gcmap[i*2+1] == i * 100 + 1

    def test_remove_nulls(self):
        expected = []
        def check():
            assert gcrootmap._gcmap_curlength == len(expected) * 2
            for i, (a, b) in enumerate(expected):
                assert gcrootmap._gcmap[i*2] == a
                assert gcrootmap._gcmap[i*2+1] == b
        #
        gcrootmap = GcRootMap_asmgcc()
        for i in range(700):
            shapeaddr = i * 100       # 0 if i == 0
            retaddr = 123456789 + i
            gcrootmap.put(retaddr, shapeaddr)
            if shapeaddr != 0:
                expected.append((retaddr, shapeaddr))
        # at the first resize, the 0 should be removed
        check()
        for repeat in range(10):
            # now clear up half the entries
            assert len(expected) == 699
            for i in range(0, len(expected), 2):
                gcrootmap._gcmap[i*2+1] = 0
                gcrootmap._gcmap_deadentries += 1
            expected = expected[1::2]
            assert gcrootmap._gcmap_deadentries*6 > gcrootmap._gcmap_maxlength
            # check that we can again insert 350 entries without a resize
            oldgcmap = gcrootmap._gcmap
            for i in range(0, 699, 2):
                gcrootmap.put(515151 + i + repeat, 626262 + i)
                expected.append((515151 + i + repeat, 626262 + i))
            assert gcrootmap._gcmap == oldgcmap
            check()

    def test_freeing_block(self):
        from pypy.jit.backend.llsupport import gc
        class Asmgcroot:
            arrayitemsize = 2 * llmemory.sizeof(llmemory.Address)
            sort_count = 0
            def sort_gcmap(self, gcmapstart, gcmapend):
                self.sort_count += 1
            def binary_search(self, gcmapstart, gcmapend, startaddr):
                i = 0
                while (i < gcrootmap._gcmap_curlength//2 and
                       gcrootmap._gcmap[i*2] < startaddr):
                    i += 1
                if i > 0:
                    i -= 1
                assert 0 <= i < gcrootmap._gcmap_curlength//2
                p = rffi.cast(rffi.CArrayPtr(llmemory.Address), gcmapstart)
                p = rffi.ptradd(p, 2*i)
                return llmemory.cast_ptr_to_adr(p)
        saved = gc.asmgcroot
        try:
            gc.asmgcroot = Asmgcroot()
            #
            gcrootmap = GcRootMap_asmgcc()
            gcrootmap._gcmap = lltype.malloc(gcrootmap.GCMAP_ARRAY,
                                             1400, flavor='raw',
                                             immortal=True)
            for i in range(700):
                gcrootmap._gcmap[i*2] = 1200000 + i
                gcrootmap._gcmap[i*2+1] = i * 100 + 1
            assert gcrootmap._gcmap_deadentries == 0
            assert gc.asmgcroot.sort_count == 0
            gcrootmap._gcmap_maxlength = 1400
            gcrootmap._gcmap_curlength = 1400
            gcrootmap._gcmap_sorted = False
            #
            gcrootmap.freeing_block(1200000 - 100, 1200000)
            assert gcrootmap._gcmap_deadentries == 0
            assert gc.asmgcroot.sort_count == 1
            #
            gcrootmap.freeing_block(1200000 + 100, 1200000 + 200)
            assert gcrootmap._gcmap_deadentries == 100
            assert gc.asmgcroot.sort_count == 1
            for i in range(700):
                if 100 <= i < 200:
                    expected = 0
                else:
                    expected = i * 100 + 1
                assert gcrootmap._gcmap[i*2] == 1200000 + i
                assert gcrootmap._gcmap[i*2+1] == expected
            #
            gcrootmap.freeing_block(1200000 + 650, 1200000 + 750)
            assert gcrootmap._gcmap_deadentries == 150
            assert gc.asmgcroot.sort_count == 1
            for i in range(700):
                if 100 <= i < 200 or 650 <= i:
                    expected = 0
                else:
                    expected = i * 100 + 1
                assert gcrootmap._gcmap[i*2] == 1200000 + i
                assert gcrootmap._gcmap[i*2+1] == expected
        #
        finally:
            gc.asmgcroot = saved


class TestGcRootMapShadowStack:
    class FakeGcDescr:
        force_index_ofs = 92

    def test_make_shapes(self):
        gcrootmap = GcRootMap_shadowstack(self.FakeGcDescr())
        shape = gcrootmap.get_basic_shape()
        gcrootmap.add_frame_offset(shape, 16)
        gcrootmap.add_frame_offset(shape, -24)
        assert shape == [16, -24]

    def test_compress_callshape(self):
        class FakeDataBlockWrapper:
            def malloc_aligned(self, size, alignment):
                assert alignment == 4    # even on 64-bits
                assert size == 12        # 4*3, even on 64-bits
                return rffi.cast(lltype.Signed, p)
        datablockwrapper = FakeDataBlockWrapper()
        p = lltype.malloc(rffi.CArray(rffi.INT), 3, immortal=True)
        gcrootmap = GcRootMap_shadowstack(self.FakeGcDescr())
        shape = [16, -24]
        gcrootmap.compress_callshape(shape, datablockwrapper)
        assert rffi.cast(lltype.Signed, p[0]) == 16
        assert rffi.cast(lltype.Signed, p[1]) == -24
        assert rffi.cast(lltype.Signed, p[2]) == 0


class FakeLLOp(object):
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

    _have_wb_from_array = False

    def _write_barrier_from_array_failing_case(self, adr_struct, v_index):
        self.record.append(('barrier_from_array', adr_struct, v_index))

    def get_write_barrier_from_array_failing_case(self, FPTRTYPE):
        if self._have_wb_from_array:
            return llhelper(FPTRTYPE,
                            self._write_barrier_from_array_failing_case)
        else:
            return lltype.nullptr(FPTRTYPE.TO)


class TestFramework(object):
    gc = 'hybrid'

    def setup_method(self, meth):
        class config_(object):
            class translation(object):
                gc = self.gc
                gcrootfinder = 'asmgcc'
                gctransformer = 'framework'
                gcremovetypeptr = False
        class FakeTranslator(object):
            config = config_
        class FakeCPU(object):
            def cast_adr_to_int(self, adr):
                if not adr:
                    return 0
                try:
                    ptr = llmemory.cast_adr_to_ptr(adr, gc_ll_descr.WB_FUNCPTR)
                    assert ptr._obj._callable == \
                           llop1._write_barrier_failing_case
                    return 42
                except lltype.InvalidCast:
                    ptr = llmemory.cast_adr_to_ptr(
                        adr, gc_ll_descr.WB_ARRAY_FUNCPTR)
                    assert ptr._obj._callable == \
                           llop1._write_barrier_from_array_failing_case
                    return 43

        gcdescr = get_description(config_)
        translator = FakeTranslator()
        llop1 = FakeLLOp()
        gc_ll_descr = GcLLDescr_framework(gcdescr, FakeTranslator(), None,
                                          llop1)
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
        assert newops[0].getopnum() == rop.COND_CALL_GC_WB
        assert newops[0].getarg(0) == v_base
        assert newops[0].getarg(1) == v_value
        assert newops[0].result is None
        wbdescr = newops[0].getdescr()
        assert isinstance(wbdescr.jit_wb_if_flag, int)
        assert isinstance(wbdescr.jit_wb_if_flag_byteofs, int)
        assert isinstance(wbdescr.jit_wb_if_flag_singlebyte, int)

    def test_get_rid_of_debug_merge_point(self):
        operations = [
            ResOperation(rop.DEBUG_MERGE_POINT, ['dummy', 2], None),
            ]
        gc_ll_descr = self.gc_ll_descr
        operations = gc_ll_descr.rewrite_assembler(None, operations, [])
        assert len(operations) == 0

    def test_rewrite_assembler_1(self):
        # check recording of ConstPtrs
        class MyFakeCPU(object):
            def cast_adr_to_int(self, adr):
                assert adr == "some fake address"
                return 43
        class MyFakeGCRefList(object):
            def get_address_of_gcref(self, s_gcref1):
                assert s_gcref1 == s_gcref
                return "some fake address"
        S = lltype.GcStruct('S')
        s = lltype.malloc(S)
        s_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
        v_random_box = BoxPtr()
        v_result = BoxInt()
        operations = [
            ResOperation(rop.PTR_EQ, [v_random_box, ConstPtr(s_gcref)],
                         v_result),
            ]
        gc_ll_descr = self.gc_ll_descr
        gc_ll_descr.gcrefs = MyFakeGCRefList()
        gcrefs = []
        operations = get_deep_immutable_oplist(operations)
        operations2 = gc_ll_descr.rewrite_assembler(MyFakeCPU(), operations,
                                                   gcrefs)
        assert operations2 == operations
        assert gcrefs == [s_gcref]

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
        operations = get_deep_immutable_oplist(operations)
        operations = gc_ll_descr.rewrite_assembler(self.fake_cpu, operations,
                                                   [])
        assert len(operations) == 2
        #
        assert operations[0].getopnum() == rop.COND_CALL_GC_WB
        assert operations[0].getarg(0) == v_base
        assert operations[0].getarg(1) == v_value
        assert operations[0].result is None
        #
        assert operations[1].getopnum() == rop.SETFIELD_RAW
        assert operations[1].getarg(0) == v_base
        assert operations[1].getarg(1) == v_value
        assert operations[1].getdescr() == field_descr

    def test_rewrite_assembler_3(self):
        # check write barriers before SETARRAYITEM_GC
        for v_new_length in (None, ConstInt(5), ConstInt(5000), BoxInt()):
            v_base = BoxPtr()
            v_index = BoxInt()
            v_value = BoxPtr()
            array_descr = AbstractDescr()
            operations = [
                ResOperation(rop.SETARRAYITEM_GC, [v_base, v_index, v_value],
                             None, descr=array_descr),
                ]
            if v_new_length is not None:
                operations.insert(0, ResOperation(rop.NEW_ARRAY,
                                                  [v_new_length], v_base,
                                                  descr=array_descr))
                # we need to insert another, unrelated NEW_ARRAY here
                # to prevent the initialization_store optimization
                operations.insert(1, ResOperation(rop.NEW_ARRAY,
                                                  [ConstInt(12)], BoxPtr(),
                                                  descr=array_descr))
            gc_ll_descr = self.gc_ll_descr
            operations = get_deep_immutable_oplist(operations)
            operations = gc_ll_descr.rewrite_assembler(self.fake_cpu,
                                                       operations, [])
            if v_new_length is not None:
                assert operations[0].getopnum() == rop.NEW_ARRAY
                assert operations[1].getopnum() == rop.NEW_ARRAY
                del operations[:2]
            assert len(operations) == 2
            #
            assert operations[0].getopnum() == rop.COND_CALL_GC_WB
            assert operations[0].getarg(0) == v_base
            assert operations[0].getarg(1) == v_value
            assert operations[0].result is None
            #
            assert operations[1].getopnum() == rop.SETARRAYITEM_RAW
            assert operations[1].getarg(0) == v_base
            assert operations[1].getarg(1) == v_index
            assert operations[1].getarg(2) == v_value
            assert operations[1].getdescr() == array_descr

    def test_rewrite_assembler_4(self):
        # check write barriers before SETARRAYITEM_GC,
        # if we have actually a write_barrier_from_array.
        self.llop1._have_wb_from_array = True
        for v_new_length in (None, ConstInt(5), ConstInt(5000), BoxInt()):
            v_base = BoxPtr()
            v_index = BoxInt()
            v_value = BoxPtr()
            array_descr = AbstractDescr()
            operations = [
                ResOperation(rop.SETARRAYITEM_GC, [v_base, v_index, v_value],
                             None, descr=array_descr),
                ]
            if v_new_length is not None:
                operations.insert(0, ResOperation(rop.NEW_ARRAY,
                                                  [v_new_length], v_base,
                                                  descr=array_descr))
                # we need to insert another, unrelated NEW_ARRAY here
                # to prevent the initialization_store optimization
                operations.insert(1, ResOperation(rop.NEW_ARRAY,
                                                  [ConstInt(12)], BoxPtr(),
                                                  descr=array_descr))
            gc_ll_descr = self.gc_ll_descr
            operations = get_deep_immutable_oplist(operations)
            operations = gc_ll_descr.rewrite_assembler(self.fake_cpu,
                                                       operations, [])
            if v_new_length is not None:
                assert operations[0].getopnum() == rop.NEW_ARRAY
                assert operations[1].getopnum() == rop.NEW_ARRAY
                del operations[:2]
            assert len(operations) == 2
            #
            if isinstance(v_new_length, ConstInt) and v_new_length.value < 130:
                assert operations[0].getopnum() == rop.COND_CALL_GC_WB
                assert operations[0].getarg(0) == v_base
                assert operations[0].getarg(1) == v_value
            else:
                assert operations[0].getopnum() == rop.COND_CALL_GC_WB_ARRAY
                assert operations[0].getarg(0) == v_base
                assert operations[0].getarg(1) == v_index
                assert operations[0].getarg(2) == v_value
            assert operations[0].result is None
            #
            assert operations[1].getopnum() == rop.SETARRAYITEM_RAW
            assert operations[1].getarg(0) == v_base
            assert operations[1].getarg(1) == v_index
            assert operations[1].getarg(2) == v_value
            assert operations[1].getdescr() == array_descr

    def test_rewrite_assembler_initialization_store(self):
        S = lltype.GcStruct('S', ('parent', OBJECT),
                            ('x', lltype.Signed))
        s_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
        xdescr = get_field_descr(self.gc_ll_descr, S, 'x')
        ops = parse("""
        [p1]
        p0 = new_with_vtable(ConstClass(s_vtable))
        setfield_gc(p0, p1, descr=xdescr)
        jump()
        """, namespace=locals())
        expected = parse("""
        [p1]
        p0 = new_with_vtable(ConstClass(s_vtable))
        # no write barrier
        setfield_gc(p0, p1, descr=xdescr)
        jump()
        """, namespace=locals())
        operations = get_deep_immutable_oplist(ops.operations)
        operations = self.gc_ll_descr.rewrite_assembler(self.fake_cpu,
                                                        operations, [])
        equaloplists(operations, expected.operations)

    def test_rewrite_assembler_initialization_store_2(self):
        S = lltype.GcStruct('S', ('parent', OBJECT),
                            ('x', lltype.Signed))
        s_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
        wbdescr = self.gc_ll_descr.write_barrier_descr
        xdescr = get_field_descr(self.gc_ll_descr, S, 'x')
        ops = parse("""
        [p1]
        p0 = new_with_vtable(ConstClass(s_vtable))
        p3 = new_with_vtable(ConstClass(s_vtable))
        setfield_gc(p0, p1, descr=xdescr)
        jump()
        """, namespace=locals())
        expected = parse("""
        [p1]
        p0 = new_with_vtable(ConstClass(s_vtable))
        p3 = new_with_vtable(ConstClass(s_vtable))
        cond_call_gc_wb(p0, p1, descr=wbdescr)
        setfield_raw(p0, p1, descr=xdescr)
        jump()
        """, namespace=locals())
        operations = get_deep_immutable_oplist(ops.operations)
        operations = self.gc_ll_descr.rewrite_assembler(self.fake_cpu,
                                                        operations, [])
        equaloplists(operations, expected.operations)

    def test_rewrite_assembler_initialization_store_3(self):
        A = lltype.GcArray(lltype.Ptr(lltype.GcStruct('S')))
        arraydescr = get_array_descr(self.gc_ll_descr, A)
        ops = parse("""
        [p1]
        p0 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p0, 0, p1, descr=arraydescr)
        jump()
        """, namespace=locals())
        expected = parse("""
        [p1]
        p0 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p0, 0, p1, descr=arraydescr)
        jump()
        """, namespace=locals())
        operations = get_deep_immutable_oplist(ops.operations)
        operations = self.gc_ll_descr.rewrite_assembler(self.fake_cpu,
                                                        operations, [])
        equaloplists(operations, expected.operations)

class TestFrameworkMiniMark(TestFramework):
    gc = 'minimark'
