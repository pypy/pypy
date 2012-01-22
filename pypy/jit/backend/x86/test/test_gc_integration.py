
""" Tests for register allocation for common constructs
"""

import py
from pypy.jit.metainterp.history import BoxInt, ConstInt,\
     BoxPtr, ConstPtr, TreeLoop, TargetToken
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.codewriter import heaptracker
from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.backend.llsupport.descr import GcCache, FieldDescr, FLAG_SIGNED
from pypy.jit.backend.llsupport.gc import GcLLDescription
from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.backend.x86.regalloc import RegAlloc
from pypy.jit.backend.x86.arch import WORD, FRAME_FIXED_SIZE
from pypy.jit.tool.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import rclass, rstr
from pypy.jit.backend.llsupport.gc import GcLLDescr_framework

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
    get_malloc_slowpath_addr = None
    write_barrier_descr = None
    moving_gc = True
    gcrootmap = MockGcRootMap()

    def initialize(self):
        pass

    _record_constptrs = GcLLDescr_framework._record_constptrs.im_func
    rewrite_assembler = GcLLDescr_framework.rewrite_assembler.im_func
    supports_compressed_ptrs = False

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
        calldescr = cpu.calldescrof(TP, TP.ARGS, TP.RESULT,
                                    EffectInfo.MOST_GENERAL)
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

    targettoken = TargetToken()

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
        label(i0, i1, i2, i3, i4, i5, i6, i7, i8, descr=targettoken)
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
        jump(i0, i1, 1, 17, i4, ConstPtr(ptr0), i6, i7, i24, descr=targettoken)
        '''
        self.interpret(ops, [0, 0, 0, 0, 0, 0, 0, 0, 0], run=False)

NOT_INITIALIZED = chr(0xdd)

class GCDescrFastpathMalloc(GcLLDescription):
    gcrootmap = None
    write_barrier_descr = None

    def __init__(self):
        GcLLDescription.__init__(self, None)
        # create a nursery
        NTP = rffi.CArray(lltype.Char)
        self.nursery = lltype.malloc(NTP, 64, flavor='raw')
        for i in range(64):
            self.nursery[i] = NOT_INITIALIZED
        self.addrs = lltype.malloc(rffi.CArray(lltype.Signed), 2,
                                   flavor='raw')
        self.addrs[0] = rffi.cast(lltype.Signed, self.nursery)
        self.addrs[1] = self.addrs[0] + 64
        self.calls = []
        def malloc_slowpath(size):
            self.calls.append(size)
            # reset the nursery
            nadr = rffi.cast(lltype.Signed, self.nursery)
            self.addrs[0] = nadr + size
            return nadr
        self.generate_function('malloc_nursery', malloc_slowpath,
                               [lltype.Signed], lltype.Signed)

    def get_nursery_free_addr(self):
        return rffi.cast(lltype.Signed, self.addrs)

    def get_nursery_top_addr(self):
        return rffi.cast(lltype.Signed, self.addrs) + WORD

    def get_malloc_slowpath_addr(self):
        return self.get_malloc_fn_addr('malloc_nursery')

    def check_nothing_in_nursery(self):
        # CALL_MALLOC_NURSERY should not write anything in the nursery
        for i in range(64):
            assert self.nursery[i] == NOT_INITIALIZED

class TestMallocFastpath(BaseTestRegalloc):

    def setup_method(self, method):
        cpu = CPU(None, None)
        cpu.gc_ll_descr = GCDescrFastpathMalloc()
        cpu.setup_once()
        self.cpu = cpu

    def test_malloc_fastpath(self):
        ops = '''
        []
        p0 = call_malloc_nursery(16)
        p1 = call_malloc_nursery(32)
        p2 = call_malloc_nursery(16)
        finish(p0, p1, p2)
        '''
        self.interpret(ops, [])
        # check the returned pointers
        gc_ll_descr = self.cpu.gc_ll_descr
        nurs_adr = rffi.cast(lltype.Signed, gc_ll_descr.nursery)
        ref = self.cpu.get_latest_value_ref
        assert rffi.cast(lltype.Signed, ref(0)) == nurs_adr + 0
        assert rffi.cast(lltype.Signed, ref(1)) == nurs_adr + 16
        assert rffi.cast(lltype.Signed, ref(2)) == nurs_adr + 48
        # check the nursery content and state
        gc_ll_descr.check_nothing_in_nursery()
        assert gc_ll_descr.addrs[0] == nurs_adr + 64
        # slowpath never called
        assert gc_ll_descr.calls == []

    def test_malloc_slowpath(self):
        ops = '''
        []
        p0 = call_malloc_nursery(16)
        p1 = call_malloc_nursery(32)
        p2 = call_malloc_nursery(24)     # overflow
        finish(p0, p1, p2)
        '''
        self.interpret(ops, [])
        # check the returned pointers
        gc_ll_descr = self.cpu.gc_ll_descr
        nurs_adr = rffi.cast(lltype.Signed, gc_ll_descr.nursery)
        ref = self.cpu.get_latest_value_ref
        assert rffi.cast(lltype.Signed, ref(0)) == nurs_adr + 0
        assert rffi.cast(lltype.Signed, ref(1)) == nurs_adr + 16
        assert rffi.cast(lltype.Signed, ref(2)) == nurs_adr + 0
        # check the nursery content and state
        gc_ll_descr.check_nothing_in_nursery()
        assert gc_ll_descr.addrs[0] == nurs_adr + 24
        # this should call slow path once
        assert gc_ll_descr.calls == [24]
