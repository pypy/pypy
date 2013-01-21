
""" Tests for register allocation for common constructs
"""

from rpython.jit.metainterp.history import TargetToken, BasicFinalDescr,\
     JitCellToken
from rpython.jit.backend.llsupport.gc import GcLLDescription, GcLLDescr_boehm,\
     GcLLDescr_framework, GcCache
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.x86.arch import WORD, JITFRAME_FIXED_SIZE
from rpython.jit.backend.llsupport import jitframe
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.annlowlevel import llhelper

from rpython.jit.backend.x86.test.test_regalloc import BaseTestRegalloc
from rpython.jit.backend.x86.regalloc import gpr_reg_mgr_cls
from rpython.jit.codewriter.effectinfo import EffectInfo

CPU = getcpuclass()

class TestRegallocGcIntegration(BaseTestRegalloc):
    
    cpu = CPU(None, None)
    cpu.gc_ll_descr = GcLLDescr_boehm(None, None, None)
    cpu.setup_once()
    
    S = lltype.GcForwardReference()
    S.become(lltype.GcStruct('S', ('field', lltype.Ptr(S)),
                             ('int', lltype.Signed)))

    fielddescr = cpu.fielddescrof(S, 'field')

    struct_ptr = lltype.malloc(S)
    struct_ref = lltype.cast_opaque_ptr(llmemory.GCREF, struct_ptr)
    child_ptr = lltype.nullptr(S)
    struct_ptr.field = child_ptr


    intdescr = cpu.fielddescrof(S, 'int')
    ptr0 = struct_ref

    targettoken = TargetToken()
    targettoken2 = TargetToken()

    namespace = locals().copy()

    def test_basic(self):
        ops = '''
        [p0]
        p1 = getfield_gc(p0, descr=fielddescr)
        finish(p1)
        '''
        self.interpret(ops, [self.struct_ptr])
        assert not self.getptr(0, lltype.Ptr(self.S))

    def test_guard(self):
        ops = '''
        [i0, p0, i1, p1]
        p3 = getfield_gc(p0, descr=fielddescr)
        guard_true(i0) [p0, i1, p1, p3]
        '''
        s1 = lltype.malloc(self.S)
        s2 = lltype.malloc(self.S)
        s1.field = s2
        self.interpret(ops, [0, s1, 1, s2])
        frame = lltype.cast_opaque_ptr(jitframe.JITFRAMEPTR, self.deadframe)
        # p0 and p3 should be in registers, p1 not so much
        assert self.getptr(0, lltype.Ptr(self.S)) == s1
        # this is a fairly CPU specific check
        assert len(frame.jf_gcmap) == 1
        # the gcmap should contain three things, p0, p1 and p3
        # p3 stays in a register
        # while p0 and p1 are on the frame
        assert frame.jf_gcmap[0] == (1 << 11) | (1 << 12) | (1 << 31)
        assert frame.jf_frame[11]
        assert frame.jf_frame[12]
        assert frame.jf_frame[31]

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
        i11 = getfield_gc(i4, descr=intdescr)
        guard_nonnull(i11) [i4, i5, i6, i7, i0, i1, i11, i8]
        i13 = getfield_gc(i11, descr=intdescr)
        guard_isnull(i13) [i4, i5, i6, i7, i0, i1, i11, i8]
        i15 = getfield_gc(i4, descr=intdescr)
        i17 = int_lt(i15, 0)
        guard_false(i17) [i4, i5, i6, i7, i0, i1, i11, i15, i8]
        i18 = getfield_gc(i11, descr=intdescr)
        i19 = int_ge(i15, i18)
        guard_false(i19) [i4, i5, i6, i7, i0, i1, i11, i15, i8]
        i20 = int_lt(i15, 0)
        guard_false(i20) [i4, i5, i6, i7, i0, i1, i11, i15, i8]
        i21 = getfield_gc(i11, descr=intdescr)
        i22 = getfield_gc(i11, descr=intdescr)
        i23 = int_mul(i15, i22)
        i24 = int_add(i21, i23)
        i25 = getfield_gc(i4, descr=intdescr)
        i27 = int_add(i25, 1)
        setfield_gc(i4, i27, descr=intdescr)
        i29 = getfield_raw(144839744, descr=intdescr)
        i31 = int_and(i29, -2141192192)
        i32 = int_is_true(i31)
        guard_false(i32) [i4, i6, i7, i0, i1, i24]
        i33 = getfield_gc(i0, descr=intdescr)
        guard_value(i33, ConstPtr(ptr0)) [i4, i6, i7, i0, i1, i33, i24]
        jump(i0, i1, 1, 17, i4, ConstPtr(ptr0), i6, i7, i24, descr=targettoken)
        '''
        self.interpret(ops, [0, 0, 0, 0, 0, 0, 0, 0, 0], run=False)

NOT_INITIALIZED = chr(0xdd)

class GCDescrFastpathMalloc(GcLLDescription):
    gcrootmap = None
    write_barrier_descr = None
    passes_frame = True

    def __init__(self, callback):
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
        def malloc_slowpath(size, frame):
            if callback is not None:
                callback(frame)
            if self.gcrootmap is not None:   # hook
                self.gcrootmap.hook_malloc_slowpath()
            self.calls.append(size)
            # reset the nursery
            nadr = rffi.cast(lltype.Signed, self.nursery)
            self.addrs[0] = nadr + size
            return nadr
        self.generate_function('malloc_nursery', malloc_slowpath,
                               [lltype.Signed, jitframe.JITFRAMEPTR],
                               lltype.Signed)

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

    def teardown_method(self, method):
        lltype.free(self.cpu.gc_ll_descr.addrs, flavor='raw')
        lltype.free(self.cpu.gc_ll_descr.nursery, flavor='raw')

    def getcpu(self, callback):
        cpu = CPU(None, None)
        cpu.gc_ll_descr = GCDescrFastpathMalloc(callback)
        cpu.setup_once()
        return cpu

    def test_malloc_fastpath(self):
        self.cpu = self.getcpu(None)
        ops = '''
        [i0]
        p0 = call_malloc_nursery(16)
        p1 = call_malloc_nursery(32)
        p2 = call_malloc_nursery(16)
        guard_true(i0) [p0, p1, p2]
        '''
        self.interpret(ops, [0])
        # check the returned pointers
        gc_ll_descr = self.cpu.gc_ll_descr
        nurs_adr = rffi.cast(lltype.Signed, gc_ll_descr.nursery)
        ref = lambda n: self.cpu.get_ref_value(self.deadframe, n)
        assert rffi.cast(lltype.Signed, ref(0)) == nurs_adr + 0
        assert rffi.cast(lltype.Signed, ref(1)) == nurs_adr + 16
        assert rffi.cast(lltype.Signed, ref(2)) == nurs_adr + 48
        # check the nursery content and state
        gc_ll_descr.check_nothing_in_nursery()
        assert gc_ll_descr.addrs[0] == nurs_adr + 64
        # slowpath never called
        assert gc_ll_descr.calls == []

    def test_malloc_slowpath(self):
        def check(frame):
            assert len(frame.jf_gcmap) == 1
            assert frame.jf_gcmap[0] == (2 | (1<<29) | (1 << 30))
        
        self.cpu = self.getcpu(check)
        ops = '''
        [i0]
        p0 = call_malloc_nursery(16)
        p1 = call_malloc_nursery(32)
        p2 = call_malloc_nursery(24)     # overflow
        guard_true(i0) [p0, p1, p2]
        '''
        self.interpret(ops, [0])
        # check the returned pointers
        gc_ll_descr = self.cpu.gc_ll_descr
        nurs_adr = rffi.cast(lltype.Signed, gc_ll_descr.nursery)
        ref = lambda n: self.cpu.get_ref_value(self.deadframe, n)
        assert rffi.cast(lltype.Signed, ref(0)) == nurs_adr + 0
        assert rffi.cast(lltype.Signed, ref(1)) == nurs_adr + 16
        assert rffi.cast(lltype.Signed, ref(2)) == nurs_adr + 0
        # check the nursery content and state
        gc_ll_descr.check_nothing_in_nursery()
        assert gc_ll_descr.addrs[0] == nurs_adr + 24
        # this should call slow path once
        assert gc_ll_descr.calls == [24]

    def test_save_regs_around_malloc(self):
        def check(frame):
            x = frame.jf_gcmap
            assert len(x) == 1
            assert bin(x[0]) == '0b1111100000000000000001111111011111'
            # all but two
        
        self.cpu = self.getcpu(check)
        S1 = lltype.GcStruct('S1')
        S2 = lltype.GcStruct('S2', ('s0', lltype.Ptr(S1)),
                                   ('s1', lltype.Ptr(S1)),
                                   ('s2', lltype.Ptr(S1)),
                                   ('s3', lltype.Ptr(S1)),
                                   ('s4', lltype.Ptr(S1)),
                                   ('s5', lltype.Ptr(S1)),
                                   ('s6', lltype.Ptr(S1)),
                                   ('s7', lltype.Ptr(S1)),
                                   ('s8', lltype.Ptr(S1)),
                                   ('s9', lltype.Ptr(S1)),
                                   ('s10', lltype.Ptr(S1)),
                                   ('s11', lltype.Ptr(S1)),
                                   ('s12', lltype.Ptr(S1)),
                                   ('s13', lltype.Ptr(S1)),
                                   ('s14', lltype.Ptr(S1)),
                                   ('s15', lltype.Ptr(S1)))
        cpu = self.cpu
        self.namespace = self.namespace.copy()
        for i in range(16):
            self.namespace['ds%i' % i] = cpu.fielddescrof(S2, 's%d' % i)
        ops = '''
        [i0, p0]
        p1 = getfield_gc(p0, descr=ds0)
        p2 = getfield_gc(p0, descr=ds1)
        p3 = getfield_gc(p0, descr=ds2)
        p4 = getfield_gc(p0, descr=ds3)
        p5 = getfield_gc(p0, descr=ds4)
        p6 = getfield_gc(p0, descr=ds5)
        p7 = getfield_gc(p0, descr=ds6)
        p8 = getfield_gc(p0, descr=ds7)
        p9 = getfield_gc(p0, descr=ds8)
        p10 = getfield_gc(p0, descr=ds9)
        p11 = getfield_gc(p0, descr=ds10)
        p12 = getfield_gc(p0, descr=ds11)
        p13 = getfield_gc(p0, descr=ds12)
        p14 = getfield_gc(p0, descr=ds13)
        p15 = getfield_gc(p0, descr=ds14)
        p16 = getfield_gc(p0, descr=ds15)
        #
        # now all registers are in use
        p17 = call_malloc_nursery(40)
        p18 = call_malloc_nursery(40)     # overflow
        #
        guard_true(i0) [p1, p2, p3, p4, p5, p6, \
            p7, p8, p9, p10, p11, p12, p13, p14, p15, p16]
        '''
        s2 = lltype.malloc(S2)
        for i in range(16):
            setattr(s2, 's%d' % i, lltype.malloc(S1))
        s2ref = lltype.cast_opaque_ptr(llmemory.GCREF, s2)
        #
        self.interpret(ops, [0, s2ref])
        gc_ll_descr = cpu.gc_ll_descr
        gc_ll_descr.check_nothing_in_nursery()
        assert gc_ll_descr.calls == [40]
        # check the returned pointers
        for i in range(16):
            s1ref = self.cpu.get_ref_value(self.deadframe, i)
            s1 = lltype.cast_opaque_ptr(lltype.Ptr(S1), s1ref)
            assert s1 == getattr(s2, 's%d' % i)

class MockShadowStackRootMap(object):
    is_shadow_stack = True
    
    def __init__(self):
        TP = rffi.CArray(lltype.Signed)
        self.stack = lltype.malloc(TP, 10, flavor='raw')
        self.stack_addr = lltype.malloc(TP, 1,
                                        flavor='raw')
        self.stack_addr[0] = rffi.cast(lltype.Signed, self.stack)

    def __del__(self):
        lltype.free(self.stack_addr, flavor='raw')        
        lltype.free(self.stack, flavor='raw')

    def register_asm_addr(self, start, mark):
        pass

    def get_root_stack_top_addr(self):
        return rffi.cast(lltype.Signed, self.stack_addr)

class GCDescrShadowstackDirect(GcLLDescr_framework):
    layoutbuilder = None
    write_barrier_descr = None

    def get_malloc_slowpath_addr(self):
        return 0

    def get_nursery_free_addr(self):
        return 0
    
    def __init__(self):
        GcCache.__init__(self, False, None)
        self.gcrootmap = MockShadowStackRootMap()

class TestGcShadowstackDirect(BaseTestRegalloc):
    
    cpu = CPU(None, None)
    cpu.gc_ll_descr = GCDescrShadowstackDirect()
    cpu.setup_once()

    def test_shadowstack_call(self):
        ofs = self.cpu.get_baseofs_of_frame_field()
        frames = []
        
        def check(i):
            import pdb
            pdb.set_trace()
            assert self.cpu.gc_ll_descr.gcrootmap.stack[0] == i - ofs
            assert len(frame.jf_frame) == JITFRAME_FIXED_SIZE
            # we "collect"
            new_frame = frame.copy()
            self.cpu.gc_ll_descr.gcrootmap.stack[0] = rffi.cast(lltype.Signed, new_frame)
            frames.append(new_frame)

        def check2(i):
            assert self.cpu.gc_ll_descr.gcrootmap.stack[0] == i - ofs
            frame = rffi.cast(jitframe.JITFRAMEPTR, i - ofs)
            assert frame == frames[1]
            assert frame != frames[0]

        CHECK = lltype.FuncType([lltype.Signed], lltype.Void)
        checkptr = llhelper(lltype.Ptr(CHECK), check)
        check2ptr = llhelper(lltype.Ptr(CHECK), check2)
        checkdescr = self.cpu.calldescrof(CHECK, CHECK.ARGS, CHECK.RESULT,
                                          EffectInfo.MOST_GENERAL)
        
        loop = self.parse("""
        []
        i0 = force_token() # this is a bit below the frame
        call(ConstClass(check_adr), i0, descr=checkdescr) # this can collect
        call(ConstClass(check2_adr), i0, descr=checkdescr)
        finish(i0, descr=finaldescr)
        """, namespace={'finaldescr': BasicFinalDescr(),
                        'check_adr': checkptr, 'check2_adr': check2ptr,
                        'checkdescr': checkdescr})
        token = JitCellToken()
        self.cpu.compile_loop(loop.inputargs, loop.operations, token)
        frame = self.cpu.execute_token(token)
