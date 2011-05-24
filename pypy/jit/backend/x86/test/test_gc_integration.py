
""" Tests for register allocation for common constructs
"""

import py
from pypy.jit.metainterp.history import BoxInt, ConstInt,\
     BoxPtr, ConstPtr, TreeLoop
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.codewriter import heaptracker
from pypy.jit.backend.llsupport.descr import GcCache
from pypy.jit.backend.llsupport.gc import GcLLDescription
from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.backend.x86.regalloc import RegAlloc
from pypy.jit.backend.x86.arch import WORD, FRAME_FIXED_SIZE
from pypy.jit.tool.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import rclass, rstr
from pypy.jit.backend.llsupport.gc import GcLLDescr_framework, GcRefList, GcPtrFieldDescr

from pypy.jit.backend.x86.test.test_regalloc import MockAssembler
from pypy.jit.backend.x86.test.test_regalloc import BaseTestRegalloc
from pypy.jit.backend.x86.regalloc import X86RegisterManager, X86FrameManager,\
     X86XMMRegisterManager

CPU = getcpuclass()

class MockGcRootMap(object):
    is_shadow_stack = False
    def get_basic_shape(self, is_64_bit):
        return ['shape']
    def add_frame_offset(self, shape, offset):
        shape.append(offset)
    def add_callee_save_reg(self, shape, reg_index):
        index_to_name = { 1: 'ebx', 2: 'esi', 3: 'edi' }
        shape.append(index_to_name[reg_index])
    def compress_callshape(self, shape, datablockwrapper):
        assert datablockwrapper == 'fakedatablockwrapper'
        assert shape[0] == 'shape'
        return ['compressed'] + shape[1:]

class MockGcDescr(GcCache):
    def get_funcptr_for_new(self):
        return 123
    get_funcptr_for_newarray = get_funcptr_for_new
    get_funcptr_for_newstr = get_funcptr_for_new
    get_funcptr_for_newunicode = get_funcptr_for_new
    get_malloc_slowpath_addr = None

    moving_gc = True
    gcrootmap = MockGcRootMap()

    def initialize(self):
        self.gcrefs = GcRefList()
        self.gcrefs.initialize()
        self.single_gcref_descr = GcPtrFieldDescr('', 0)

    replace_constptrs_with_getfield_raw = GcLLDescr_framework.replace_constptrs_with_getfield_raw.im_func
    rewrite_assembler = GcLLDescr_framework.rewrite_assembler.im_func

class TestRegallocDirectGcIntegration(object):

    def test_mark_gc_roots(self):
        cpu = CPU(None, None)
        cpu.setup_once()
        regalloc = RegAlloc(MockAssembler(cpu, MockGcDescr(False)))
        regalloc.assembler.datablockwrapper = 'fakedatablockwrapper'
        boxes = [BoxPtr() for i in range(len(X86RegisterManager.all_regs))]
        longevity = {}
        for box in boxes:
            longevity[box] = (0, 1)
        regalloc.fm = X86FrameManager()
        regalloc.rm = X86RegisterManager(longevity, regalloc.fm,
                                         assembler=regalloc.assembler)
        regalloc.xrm = X86XMMRegisterManager(longevity, regalloc.fm,
                                             assembler=regalloc.assembler)
        cpu = regalloc.assembler.cpu
        for box in boxes:
            regalloc.rm.try_allocate_reg(box)
        TP = lltype.FuncType([], lltype.Signed)
        calldescr = cpu.calldescrof(TP, TP.ARGS, TP.RESULT)
        regalloc.rm._check_invariants()
        box = boxes[0]
        regalloc.position = 0
        regalloc.consider_call(ResOperation(rop.CALL, [box], BoxInt(),
                                            calldescr))
        assert len(regalloc.assembler.movs) == 3
        #
        mark = regalloc.get_mark_gc_roots(cpu.gc_ll_descr.gcrootmap)
        assert mark[0] == 'compressed'
        base = -WORD * FRAME_FIXED_SIZE
        expected = ['ebx', 'esi', 'edi', base, base-WORD, base-WORD*2]
        assert dict.fromkeys(mark[1:]) == dict.fromkeys(expected)

class TestRegallocGcIntegration(BaseTestRegalloc):
    
    cpu = CPU(None, None)
    cpu.gc_ll_descr = MockGcDescr(False)
    cpu.setup_once()
    
    S = lltype.GcForwardReference()
    S.become(lltype.GcStruct('S', ('field', lltype.Ptr(S)),
                             ('int', lltype.Signed)))

    fielddescr = cpu.fielddescrof(S, 'field')

    struct_ptr = lltype.malloc(S)
    struct_ref = lltype.cast_opaque_ptr(llmemory.GCREF, struct_ptr)
    child_ptr = lltype.nullptr(S)
    struct_ptr.field = child_ptr


    descr0 = cpu.fielddescrof(S, 'int')
    ptr0 = struct_ref

    namespace = locals().copy()

    def test_basic(self):
        ops = '''
        [p0]
        p1 = getfield_gc(p0, descr=fielddescr)
        finish(p1)
        '''
        self.interpret(ops, [self.struct_ptr])
        assert not self.getptr(0, lltype.Ptr(self.S))

    def test_rewrite_constptr(self):
        ops = '''
        []
        p1 = getfield_gc(ConstPtr(struct_ref), descr=fielddescr)
        finish(p1)
        '''
        self.interpret(ops, [])
        assert not self.getptr(0, lltype.Ptr(self.S))

    def test_bug_0(self):
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7, i8]
        guard_value(i2, 1) [i2, i3, i4, i5, i6, i7, i0, i1, i8]
        guard_class(i4, 138998336) [i4, i5, i6, i7, i0, i1, i8]
        i11 = getfield_gc(i4, descr=descr0)
        guard_nonnull(i11) [i4, i5, i6, i7, i0, i1, i11, i8]
        i13 = getfield_gc(i11, descr=descr0)
        guard_isnull(i13) [i4, i5, i6, i7, i0, i1, i11, i8]
        i15 = getfield_gc(i4, descr=descr0)
        i17 = int_lt(i15, 0)
        guard_false(i17) [i4, i5, i6, i7, i0, i1, i11, i15, i8]
        i18 = getfield_gc(i11, descr=descr0)
        i19 = int_ge(i15, i18)
        guard_false(i19) [i4, i5, i6, i7, i0, i1, i11, i15, i8]
        i20 = int_lt(i15, 0)
        guard_false(i20) [i4, i5, i6, i7, i0, i1, i11, i15, i8]
        i21 = getfield_gc(i11, descr=descr0)
        i22 = getfield_gc(i11, descr=descr0)
        i23 = int_mul(i15, i22)
        i24 = int_add(i21, i23)
        i25 = getfield_gc(i4, descr=descr0)
        i27 = int_add(i25, 1)
        setfield_gc(i4, i27, descr=descr0)
        i29 = getfield_raw(144839744, descr=descr0)
        i31 = int_and(i29, -2141192192)
        i32 = int_is_true(i31)
        guard_false(i32) [i4, i6, i7, i0, i1, i24]
        i33 = getfield_gc(i0, descr=descr0)
        guard_value(i33, ConstPtr(ptr0)) [i4, i6, i7, i0, i1, i33, i24]
        jump(i0, i1, 1, 17, i4, ConstPtr(ptr0), i6, i7, i24)
        '''
        self.interpret(ops, [0, 0, 0, 0, 0, 0, 0, 0, 0], run=False)

class GCDescrFastpathMalloc(GcLLDescription):
    gcrootmap = None
    expected_malloc_slowpath_size = WORD*2

    def __init__(self):
        GcCache.__init__(self, False)
        # create a nursery
        NTP = rffi.CArray(lltype.Signed)
        self.nursery = lltype.malloc(NTP, 16, flavor='raw')
        self.addrs = lltype.malloc(rffi.CArray(lltype.Signed), 3,
                                   flavor='raw')
        self.addrs[0] = rffi.cast(lltype.Signed, self.nursery)
        self.addrs[1] = self.addrs[0] + 16*WORD
        self.addrs[2] = 0
        # 16 WORDs
        def malloc_slowpath(size):
            assert size == self.expected_malloc_slowpath_size
            nadr = rffi.cast(lltype.Signed, self.nursery)
            self.addrs[0] = nadr + size
            self.addrs[2] += 1
            return nadr
        self.malloc_slowpath = malloc_slowpath
        self.MALLOC_SLOWPATH = lltype.FuncType([lltype.Signed],
                                               lltype.Signed)
        self._counter = 123000

    def can_inline_malloc(self, descr):
        return True

    def get_funcptr_for_new(self):
        return 42
#        return llhelper(lltype.Ptr(self.NEW_TP), self.new)

    def init_size_descr(self, S, descr):
        descr.tid = self._counter
        self._counter += 1

    def get_nursery_free_addr(self):
        return rffi.cast(lltype.Signed, self.addrs)

    def get_nursery_top_addr(self):
        return rffi.cast(lltype.Signed, self.addrs) + WORD

    def get_malloc_slowpath_addr(self):
        fptr = llhelper(lltype.Ptr(self.MALLOC_SLOWPATH), self.malloc_slowpath)
        return rffi.cast(lltype.Signed, fptr)

    get_funcptr_for_newarray = None
    get_funcptr_for_newstr = None
    get_funcptr_for_newunicode = None

class TestMallocFastpath(BaseTestRegalloc):

    def setup_method(self, method):
        cpu = CPU(None, None)
        cpu.vtable_offset = WORD
        cpu.gc_ll_descr = GCDescrFastpathMalloc()
        cpu.setup_once()

        # hack: specify 'tid' explicitly, because this test is not running
        # with the gc transformer
        NODE = lltype.GcStruct('node', ('tid', lltype.Signed),
                                       ('value', lltype.Signed))
        nodedescr = cpu.sizeof(NODE)
        valuedescr = cpu.fielddescrof(NODE, 'value')

        self.cpu = cpu
        self.nodedescr = nodedescr
        vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        vtable_int = cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(vtable))
        NODE2 = lltype.GcStruct('node2',
                                  ('parent', rclass.OBJECT),
                                  ('tid', lltype.Signed),
                                  ('vtable', lltype.Ptr(rclass.OBJECT_VTABLE)))
        descrsize = cpu.sizeof(NODE2)
        heaptracker.register_known_gctype(cpu, vtable, NODE2)
        self.descrsize = descrsize
        self.vtable_int = vtable_int

        self.namespace = locals().copy()
        
    def test_malloc_fastpath(self):
        ops = '''
        [i0]
        p0 = new(descr=nodedescr)
        setfield_gc(p0, i0, descr=valuedescr)
        finish(p0)
        '''
        self.interpret(ops, [42])
        # check the nursery
        gc_ll_descr = self.cpu.gc_ll_descr
        assert gc_ll_descr.nursery[0] == self.nodedescr.tid
        assert gc_ll_descr.nursery[1] == 42
        nurs_adr = rffi.cast(lltype.Signed, gc_ll_descr.nursery)
        assert gc_ll_descr.addrs[0] == nurs_adr + (WORD*2)
        assert gc_ll_descr.addrs[2] == 0   # slowpath never called

    def test_malloc_slowpath(self):
        ops = '''
        []
        p0 = new(descr=nodedescr)
        p1 = new(descr=nodedescr)
        p2 = new(descr=nodedescr)
        p3 = new(descr=nodedescr)
        p4 = new(descr=nodedescr)
        p5 = new(descr=nodedescr)
        p6 = new(descr=nodedescr)
        p7 = new(descr=nodedescr)
        p8 = new(descr=nodedescr)
        finish(p0, p1, p2, p3, p4, p5, p6, p7, p8)
        '''
        self.interpret(ops, [])
        # this should call slow path once
        gc_ll_descr = self.cpu.gc_ll_descr
        nadr = rffi.cast(lltype.Signed, gc_ll_descr.nursery)
        assert gc_ll_descr.addrs[0] == nadr + (WORD*2)
        assert gc_ll_descr.addrs[2] == 1   # slowpath called once

    def test_new_with_vtable(self):
        ops = '''
        [i0, i1]
        p0 = new_with_vtable(ConstClass(vtable))
        guard_class(p0, ConstClass(vtable)) [i0]
        finish(i1)
        '''
        self.interpret(ops, [0, 1])
        assert self.getint(0) == 1
        gc_ll_descr = self.cpu.gc_ll_descr
        assert gc_ll_descr.nursery[0] == self.descrsize.tid
        assert gc_ll_descr.nursery[1] == self.vtable_int
        nurs_adr = rffi.cast(lltype.Signed, gc_ll_descr.nursery)
        assert gc_ll_descr.addrs[0] == nurs_adr + (WORD*3)
        assert gc_ll_descr.addrs[2] == 0   # slowpath never called


class Seen(Exception):
    pass

class GCDescrFastpathMallocVarsize(GCDescrFastpathMalloc):
    def can_inline_malloc_varsize(self, arraydescr, num_elem):
        return num_elem < 5
    def get_funcptr_for_newarray(self):
        return 52
    def init_array_descr(self, A, descr):
        descr.tid = self._counter
        self._counter += 1
    def args_for_new_array(self, descr):
        raise Seen("args_for_new_array")

class TestMallocVarsizeFastpath(BaseTestRegalloc):
    def setup_method(self, method):
        cpu = CPU(None, None)
        cpu.vtable_offset = WORD
        cpu.gc_ll_descr = GCDescrFastpathMallocVarsize()
        cpu.setup_once()
        self.cpu = cpu

        ARRAY = lltype.GcArray(lltype.Signed)
        arraydescr = cpu.arraydescrof(ARRAY)
        self.arraydescr = arraydescr
        ARRAYCHAR = lltype.GcArray(lltype.Char)
        arraychardescr = cpu.arraydescrof(ARRAYCHAR)

        self.namespace = locals().copy()

    def test_malloc_varsize_fastpath(self):
        # Hack.  Running the GcLLDescr_framework without really having
        # a complete GC means that we end up with both the tid and the
        # length being at offset 0.  In this case, so the length overwrites
        # the tid.  This is of course only the case in this test class.
        ops = '''
        []
        p0 = new_array(4, descr=arraydescr)
        setarrayitem_gc(p0, 0, 142, descr=arraydescr)
        setarrayitem_gc(p0, 3, 143, descr=arraydescr)
        finish(p0)
        '''
        self.interpret(ops, [])
        # check the nursery
        gc_ll_descr = self.cpu.gc_ll_descr
        assert gc_ll_descr.nursery[0] == 4
        assert gc_ll_descr.nursery[1] == 142
        assert gc_ll_descr.nursery[4] == 143
        nurs_adr = rffi.cast(lltype.Signed, gc_ll_descr.nursery)
        assert gc_ll_descr.addrs[0] == nurs_adr + (WORD*5)
        assert gc_ll_descr.addrs[2] == 0   # slowpath never called

    def test_malloc_varsize_slowpath(self):
        ops = '''
        []
        p0 = new_array(4, descr=arraydescr)
        setarrayitem_gc(p0, 0, 420, descr=arraydescr)
        setarrayitem_gc(p0, 3, 430, descr=arraydescr)
        p1 = new_array(4, descr=arraydescr)
        setarrayitem_gc(p1, 0, 421, descr=arraydescr)
        setarrayitem_gc(p1, 3, 431, descr=arraydescr)
        p2 = new_array(4, descr=arraydescr)
        setarrayitem_gc(p2, 0, 422, descr=arraydescr)
        setarrayitem_gc(p2, 3, 432, descr=arraydescr)
        p3 = new_array(4, descr=arraydescr)
        setarrayitem_gc(p3, 0, 423, descr=arraydescr)
        setarrayitem_gc(p3, 3, 433, descr=arraydescr)
        finish(p0, p1, p2, p3)
        '''
        gc_ll_descr = self.cpu.gc_ll_descr
        gc_ll_descr.expected_malloc_slowpath_size = 5*WORD
        self.interpret(ops, [])
        assert gc_ll_descr.addrs[2] == 1   # slowpath called once

    def test_malloc_varsize_too_big(self):
        ops = '''
        []
        p0 = new_array(5, descr=arraydescr)
        finish(p0)
        '''
        py.test.raises(Seen, self.interpret, ops, [])

    def test_malloc_varsize_variable(self):
        ops = '''
        [i0]
        p0 = new_array(i0, descr=arraydescr)
        finish(p0)
        '''
        py.test.raises(Seen, self.interpret, ops, [])

    def test_malloc_array_of_char(self):
        # check that fastpath_malloc_varsize() respects the alignment
        # of the pointer in the nursery
        ops = '''
        []
        p1 = new_array(1, descr=arraychardescr)
        p2 = new_array(2, descr=arraychardescr)
        p3 = new_array(3, descr=arraychardescr)
        p4 = new_array(4, descr=arraychardescr)
        finish(p1, p2, p3, p4)
        '''
        self.interpret(ops, [])
        p1 = self.getptr(0, llmemory.GCREF)
        p2 = self.getptr(1, llmemory.GCREF)
        p3 = self.getptr(2, llmemory.GCREF)
        p4 = self.getptr(3, llmemory.GCREF)
        assert p1._obj.intval & (WORD-1) == 0    # aligned
        assert p2._obj.intval & (WORD-1) == 0    # aligned
        assert p3._obj.intval & (WORD-1) == 0    # aligned
        assert p4._obj.intval & (WORD-1) == 0    # aligned
