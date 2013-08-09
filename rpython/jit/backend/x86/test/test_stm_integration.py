import py
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, rstr
from rpython.jit.metainterp.history import ResOperation, TargetToken,\
     JitCellToken
from rpython.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt,
                                            ConstPtr, Box, Const,
                                            BasicFailDescr, BasicFinalDescr)
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.x86.arch import WORD
from rpython.jit.backend.x86.rx86 import fits_in_32bits
from rpython.jit.backend.llsupport import symbolic
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.executor import execute
from rpython.jit.backend.test.runner_test import LLtypeBackendTest
from rpython.jit.tool.oparser import parse
from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.backend.llsupport.gc import BarrierDescr
from rpython.jit.backend.llsupport.test.test_gc_integration import (
    GCDescrShadowstackDirect, BaseTestRegalloc, JitFrameDescrs)
from rpython.jit.backend.llsupport import jitframe
from rpython.memory.gc.stmgc import StmGC
import itertools, sys
import ctypes

CPU = getcpuclass()

class MockSTMRootMap(object):
    is_shadow_stack = True
    is_stm = True
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

class FakeSTMBarrier(BarrierDescr):
    def __init__(self, gc_ll_descr, stmcat, func):
        BarrierDescr.__init__(self, gc_ll_descr)
        self.stmcat = stmcat
        self.returns_modified_object = True
        self.B_FUNCPTR_MOD = lltype.Ptr(lltype.FuncType(
            [llmemory.Address], llmemory.Address))
        self.write_barrier_fn = llhelper(self.B_FUNCPTR_MOD, func)
    def get_barrier_funcptr(self, returns_modified_object):
        assert returns_modified_object
        return self.write_barrier_fn
    def get_barrier_fn(self, cpu, returns_modified_object):
        assert returns_modified_object
        return self.write_barrier_fn

# ____________________________________________________________

def allocate_protected(TP, tid=123, n=1, zero=True):
    obj = lltype.malloc(TP, n=n, zero=zero)
    obj.h_tid = rffi.cast(lltype.Unsigned, 
                            StmGC.GCFLAG_OLD|StmGC.GCFLAG_WRITE_BARRIER | tid)
    obj.h_revision = rffi.cast(lltype.Signed, -sys.maxint)
    return obj

def jitframe_allocate(frame_info):
    frame = allocate_protected(JITFRAME,
                               frame_info.jfi_frame_depth, zero=True)
    frame.jf_frame_info = frame_info
    return frame

JITFRAME = lltype.GcStruct(
    'JITFRAME',
    ('h_tid', lltype.Unsigned),
    ('h_revision', lltype.Signed),
    ('h_original', lltype.Unsigned),
    ('jf_frame_info', lltype.Ptr(jitframe.JITFRAMEINFO)),
    ('jf_descr', llmemory.GCREF),
    ('jf_force_descr', llmemory.GCREF),
    ('jf_extra_stack_depth', lltype.Signed),
    ('jf_guard_exc', llmemory.GCREF),
    ('jf_gcmap', lltype.Ptr(jitframe.GCMAP)),
    ('jf_gc_trace_state', lltype.Signed),
    ('jf_frame', lltype.Array(lltype.Signed)),
    adtmeths = {
        'allocate': jitframe_allocate,
    },
)

JITFRAMEPTR = lltype.Ptr(JITFRAME)

class FakeGCHeaderBuilder:
    size_gc_header = WORD


class GCDescrStm(GCDescrShadowstackDirect):
    def __init__(self):
        GCDescrShadowstackDirect.__init__(self)
        self.gcrootmap = MockSTMRootMap()
        self.gcheaderbuilder = FakeGCHeaderBuilder()
        self.write_barrier_descr = None
        self.llop1 = None
        self.rb_called_on = []
        self.wb_called_on = []
        self.ptr_eq_called_on = []
        self.stm = True

        def read_barrier(obj):
            self.rb_called_on.append(obj)
            return obj
        def write_barrier(obj):
            self.wb_called_on.append(obj)
            return obj

        self.P2Rdescr = FakeSTMBarrier(self, 'P2R', read_barrier)
        self.P2Wdescr = FakeSTMBarrier(self, 'P2W', write_barrier)
        
        self.do_write_barrier = None
        self.get_nursery_top_addr = None
        self.get_nursery_free_addr = None

        def malloc_str(length):
            assert False
        self.generate_function('malloc_str', malloc_str,
                               [lltype.Signed])
        def malloc_unicode(length):
            assert False
        self.generate_function('malloc_unicode', malloc_unicode,
                               [lltype.Signed])
        def inevitable():
            pass
        self.generate_function('stm_try_inevitable',
                               inevitable, [],
                               RESULT=lltype.Void)
        def ptr_eq(x, y):
            self.ptr_eq_called_on.append((x, y))
            return x == y
        self.generate_function('stm_ptr_eq', ptr_eq, [llmemory.GCREF] * 2,
                               RESULT=lltype.Bool)

    def malloc_jitframe(self, frame_info):
        """ Allocate a new frame, overwritten by tests
        """
        frame = JITFRAME.allocate(frame_info)
        self.frames.append(frame)
        return frame

    def getframedescrs(self, cpu):
        descrs = JitFrameDescrs()
        descrs.arraydescr = cpu.arraydescrof(JITFRAME)
        for name in ['jf_descr', 'jf_guard_exc', 'jf_force_descr',
                     'jf_frame_info', 'jf_gcmap', 'jf_extra_stack_depth']:
            setattr(descrs, name, cpu.fielddescrof(JITFRAME, name))
        descrs.jfi_frame_depth = cpu.fielddescrof(jitframe.JITFRAMEINFO,
                                                  'jfi_frame_depth')
        descrs.jfi_frame_size = cpu.fielddescrof(jitframe.JITFRAMEINFO,
                                                  'jfi_frame_size')
        return descrs
        
    def get_malloc_slowpath_addr(self):
        return None

    def clear_lists(self):
        self.rb_called_on[:] = []
        self.wb_called_on[:] = []
        self.ptr_eq_called_on[:] = []


class TestGcStm(BaseTestRegalloc):
    
    def setup_method(self, meth):
        cpu = CPU(None, None)
        cpu.gc_ll_descr = GCDescrStm()
        self.p2wd = cpu.gc_ll_descr.P2Wdescr
        self.p2rd = cpu.gc_ll_descr.P2Rdescr

        TP = rffi.CArray(lltype.Signed)
        self.priv_rev_num = lltype.malloc(TP, 1, flavor='raw')
        self.clear_read_cache()
        
        cpu.assembler._get_stm_private_rev_num_addr = self.get_priv_rev_num
        cpu.assembler._get_stm_read_barrier_cache_addr = self.get_read_cache
        
        S = lltype.GcForwardReference()
        S.become(lltype.GcStruct(
            'S', ('h_tid', lltype.Unsigned),
            ('h_revision', lltype.Signed),
            ('h_original', lltype.Unsigned)))
        cpu.gc_ll_descr.fielddescr_tid = None # not needed
        # = cpu.fielddescrof(S, 'h_tid')
        self.S = S
        self.cpu = cpu

    def teardown_method(self, meth):
        rffi.aroundstate._cleanup_()
        
    def assert_in(self, called_on, args):
        for i, ref in enumerate(args):
            assert rffi.cast_ptr_to_adr(ref) == called_on[i]
            
    def assert_not_in(self, called_on, args):
        for ref in args:
            assert rffi.cast_ptr_to_adr(ref) not in called_on

    def get_priv_rev_num(self):
        return rffi.cast(lltype.Signed, self.priv_rev_num)

    def get_read_cache(self):
        return rffi.cast(lltype.Signed, self.read_cache_adr)

    def clear_read_cache(self):
        TP = rffi.CArray(lltype.Signed)
        entries = (StmGC.FX_MASK + 1) / WORD
        self.read_cache = lltype.malloc(TP, n=entries, flavor='raw',
                                        track_allocation=False, zero=True)
        self.read_cache_adr = lltype.malloc(TP, 1, flavor='raw',
                                            track_allocation=False)
        self.read_cache_adr[0] = rffi.cast(lltype.Signed, self.read_cache)

    def set_cache_item(self, obj):
        obj_int = rffi.cast(lltype.Signed, obj)
        idx = (obj_int & StmGC.FX_MASK) / WORD
        self.read_cache[idx] = obj_int

    def allocate_prebuilt_s(self, tid=66):
        s = lltype.malloc(self.S, zero=True)
        s.h_tid = rffi.cast(lltype.Unsigned, StmGC.PREBUILT_FLAGS | tid)
        s.h_revision = rffi.cast(lltype.Signed, StmGC.PREBUILT_REVISION)
        return s
        
    def test_read_barrier_fastpath(self):
        cpu = self.cpu
        cpu.setup_once()
        PRIV_REV = rffi.cast(lltype.Signed, StmGC.PREBUILT_REVISION)
        self.priv_rev_num[0] = PRIV_REV
        called_on = cpu.gc_ll_descr.rb_called_on
        for rev in [PRIV_REV+4, PRIV_REV]:
            cpu.gc_ll_descr.clear_lists()
            self.clear_read_cache()
            
            s = self.allocate_prebuilt_s()
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            s.h_revision = rev
            
            p0 = BoxPtr()
            operations = [
                ResOperation(rop.COND_CALL_STM_B, [p0], None,
                             descr=self.p2rd),
                ResOperation(rop.FINISH, [p0], None, 
                             descr=BasicFinalDescr(0)),
                ]
            inputargs = [p0]
            looptoken = JitCellToken()
            cpu.compile_loop(inputargs, operations, looptoken)
            self.cpu.execute_token(looptoken, sgcref)
            
            # check if rev-fastpath worked
            if rev == PRIV_REV:
                # fastpath
                assert not called_on
            else:
                self.assert_in(called_on, [sgcref])

            # now add it to the read-cache and check
            # that it will never call the read_barrier
            cpu.gc_ll_descr.clear_lists()
            self.set_cache_item(sgcref)
            
            self.cpu.execute_token(looptoken, sgcref)
            # not called:
            assert not called_on

    def test_write_barrier_fastpath(self):
        cpu = self.cpu
        cpu.setup_once()
        PRIV_REV = rffi.cast(lltype.Signed, StmGC.PREBUILT_REVISION)
        self.priv_rev_num[0] = PRIV_REV
        called_on = cpu.gc_ll_descr.wb_called_on
        
        for rev in [PRIV_REV+4, PRIV_REV]:
            cpu.gc_ll_descr.clear_lists()
            
            s = self.allocate_prebuilt_s()
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            s.h_revision = rev
            
            p0 = BoxPtr()
            operations = [
                ResOperation(rop.COND_CALL_STM_B, [p0], None,
                             descr=self.p2wd),
                ResOperation(rop.FINISH, [p0], None, 
                             descr=BasicFinalDescr(0)),
                ]
            inputargs = [p0]
            looptoken = JitCellToken()
            cpu.compile_loop(inputargs, operations, looptoken)
            self.cpu.execute_token(looptoken, sgcref)
            
            # check if rev-fastpath worked
            if rev == PRIV_REV:
                # fastpath and WRITE_BARRIER not set
                assert not called_on
            else:
                self.assert_in(called_on, [sgcref])

            # now set WRITE_BARRIER -> always call slowpath
            cpu.gc_ll_descr.clear_lists()
            s.h_tid |= StmGC.GCFLAG_WRITE_BARRIER
            self.cpu.execute_token(looptoken, sgcref)
            self.assert_in(called_on, [sgcref])

    def test_ptr_eq_fastpath(self):
        cpu = self.cpu
        cpu.setup_once()
        called_on = cpu.gc_ll_descr.ptr_eq_called_on

        i0 = BoxInt()
        i1 = BoxInt()
        sa, sb = (rffi.cast(llmemory.GCREF, self.allocate_prebuilt_s()),
                  rffi.cast(llmemory.GCREF, self.allocate_prebuilt_s()))
        ss = [sa, sa, sb, sb,
              lltype.nullptr(llmemory.GCREF.TO),
              lltype.nullptr(llmemory.GCREF.TO),
              ]
        for s1, s2 in itertools.combinations(ss, 2):
            ps = [BoxPtr(), BoxPtr(),
                  ConstPtr(s1),
                  ConstPtr(s2)]
            for p1, p2 in itertools.combinations(ps, 2):
                for guard in [None, rop.GUARD_TRUE, rop.GUARD_FALSE]:
                    cpu.gc_ll_descr.clear_lists()

                    # BUILD OPERATIONS:
                    i = i0
                    guarddescr = BasicFailDescr()
                    finaldescr = BasicFinalDescr()
                    operations = [ResOperation(rop.PTR_EQ, [p1, p2], i0)]
                    if guard is not None:
                        gop = ResOperation(guard, [i0], None, 
                                           descr=guarddescr)
                        gop.setfailargs([])
                        operations.append(gop)
                        i = i1
                    # finish must depend on result of ptr_eq if no guard
                    # is inbetween (otherwise ptr_eq gets deleted)
                    # if there is a guard, the result of ptr_eq must not
                    # be used after it again... -> i
                    operations.append(
                        ResOperation(rop.FINISH, [i], None, 
                                     descr=finaldescr)
                        )

                    # COMPILE & EXECUTE LOOP:
                    inputargs = [p for p in (p1, p2) 
                                 if not isinstance(p, Const)]
                    looptoken = JitCellToken()
                    c_loop = cpu.compile_loop(inputargs + [i1], operations, 
                                              looptoken)
                    print c_loop
                    args = [s for i, s in enumerate((s1, s2))
                            if not isinstance((p1, p2)[i], Const)] + [1]
                    
                    frame = self.cpu.execute_token(looptoken, *args)
                    frame = rffi.cast(JITFRAMEPTR, frame)
                    guard_failed = frame.jf_descr is not finaldescr
                    
                    # CHECK:
                    a, b = s1, s2
                    if isinstance(p1, Const):
                        s1 = p1.value
                    if isinstance(p2, Const):
                        s2 = p2.value
                        
                    if s1 == s2 or \
                      rffi.cast(lltype.Signed, s1) == 0 or \
                      rffi.cast(lltype.Signed, s2) == 0:
                        assert (s1, s2) not in called_on
                    else:
                        assert [(s1, s2)] == called_on

                    if guard is not None:
                        if s1 == s2:
                            if guard == rop.GUARD_TRUE:
                                assert not guard_failed
                            else:
                                assert guard_failed
                        elif guard == rop.GUARD_FALSE:
                            assert not guard_failed
                        else:
                            assert guard_failed


                        


        
