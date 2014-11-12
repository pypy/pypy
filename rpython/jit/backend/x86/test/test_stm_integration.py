import py
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, rstr
from rpython.rtyper import rclass
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
from rpython.jit.metainterp import history
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.rlib import rgc
from rpython.rtyper.llinterp import LLException
import itertools, sys
import ctypes

def cast_to_int(obj):
    if isinstance(obj, rgc._GcRef):
        return rgc.cast_gcref_to_int(obj)
    else:
        return rffi.cast(lltype.Signed, obj)

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

def allocate_protected(TP, n=1, zero=True, tid=124):
    obj = lltype.malloc(TP, n=n, zero=zero)
    obj.h_tid = rffi.cast(lltype.Unsigned,
                          StmGC.GCFLAG_OLD|StmGC.GCFLAG_WRITE_BARRIER | tid)
    obj.h_revision = rffi.cast(lltype.Signed, -sys.maxint)
    return obj

def allocate_prebuilt(TP, n=1, zero=True, tid=123):
    obj = lltype.malloc(TP, n=n, zero=zero)
    obj.h_tid = rffi.cast(lltype.Unsigned, StmGC.PREBUILT_FLAGS | tid)
    obj.h_revision = rffi.cast(lltype.Signed, StmGC.PREBUILT_REVISION)
    return obj

def jitframe_allocate(frame_info):
    frame = allocate_protected(JITFRAME, n=frame_info.jfi_frame_depth, 
                               zero=True)
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

class fakellop:
    PRIV_REV = 66
    def __init__(self):
        self.TP = rffi.CArray(lltype.Signed)
        self.privrevp = lltype.malloc(self.TP, n=1, flavor='raw', 
                                      track_allocation=False, zero=True)
        self.privrevp[0] = fakellop.PRIV_REV

        entries = (StmGC.FX_MASK + 1) / WORD
        self.read_cache = lltype.malloc(self.TP, n=entries, flavor='raw',
                                        track_allocation=False, zero=True)
        self.read_cache_adr = lltype.malloc(self.TP, 1, flavor='raw',
                                            track_allocation=False)
        self.read_cache_adr[0] = rffi.cast(lltype.Signed, self.read_cache)
        
    def set_cache_item(self, obj, value):
        obj_int = rffi.cast(lltype.Signed, obj)
        idx = (obj_int & StmGC.FX_MASK) / WORD
        self.read_cache[idx] = rffi.cast(lltype.Signed, value)
        
    def stm_get_adr_of_private_rev_num(self, _):
        return self.privrevp

    def stm_get_adr_of_read_barrier_cache(self, _):
        return self.read_cache_adr

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

        self.A2Rdescr = FakeSTMBarrier(self, 'A2R', read_barrier)
        self.A2Idescr = FakeSTMBarrier(self, 'A2I', read_barrier)
        self.Q2Rdescr = FakeSTMBarrier(self, 'Q2R', read_barrier)
        self.A2Wdescr = FakeSTMBarrier(self, 'A2W', write_barrier)
        self.A2Vdescr = FakeSTMBarrier(self, 'A2V', write_barrier)
        self.V2Wdescr = FakeSTMBarrier(self, 'V2W', write_barrier)
        
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
            print "=== ptr_eq", hex(cast_to_int(x)), hex(cast_to_int(y))
            self.ptr_eq_called_on.append((cast_to_int(x), cast_to_int(y)))
            return x == y
        self.generate_function('stm_ptr_eq', ptr_eq, [llmemory.GCREF] * 2,
                               RESULT=lltype.Bool)

        def stm_allocate_nonmovable_int_adr(obj):
            assert False # should not be reached
            return rgc.cast_gcref_to_int(obj)
        self.generate_function('stm_allocate_nonmovable_int_adr', 
                               stm_allocate_nonmovable_int_adr, 
                               [llmemory.GCREF],
                               RESULT=lltype.Signed)

        def malloc_big_fixedsize(size, tid):
            print "malloc:", size, tid
            if size > sys.maxint / 2:
                # for testing exception
                raise LLException(0, 0)
            
            entries = size + StmGC.GCHDRSIZE
            TP = rffi.CArray(lltype.Char)
            obj = lltype.malloc(TP, n=entries, flavor='raw',
                                track_allocation=False, zero=True)
            objptr = rffi.cast(StmGC.GCHDRP, obj)
            objptr.h_tid = rffi.cast(lltype.Unsigned,
                                     StmGC.GCFLAG_OLD
                                     | StmGC.GCFLAG_WRITE_BARRIER | tid)
            objptr.h_revision = rffi.cast(lltype.Signed, -sys.maxint)
            print "return:", obj, objptr
            return rffi.cast(llmemory.GCREF, objptr)
        self.generate_function('malloc_big_fixedsize', malloc_big_fixedsize,
                               [lltype.Signed] * 2)

        
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

        def latest_descr(self, deadframe):
            deadframe = lltype.cast_opaque_ptr(JITFRAMEPTR, deadframe)
            descr = deadframe.jf_descr
            res = history.AbstractDescr.show(self, descr)
            assert isinstance(res, history.AbstractFailDescr)
            return res
        import types
        cpu.get_latest_descr = types.MethodType(latest_descr, cpu,
                                                cpu.__class__)
        

        self.a2wd = cpu.gc_ll_descr.A2Wdescr
        self.a2vd = cpu.gc_ll_descr.A2Vdescr
        self.v2wd = cpu.gc_ll_descr.V2Wdescr
        self.a2rd = cpu.gc_ll_descr.A2Rdescr
        self.a2id = cpu.gc_ll_descr.A2Idescr
        self.q2rd = cpu.gc_ll_descr.Q2Rdescr

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
            assert rffi.cast_ptr_to_adr(ref) in called_on
            
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

    
        
    def test_gc_read_barrier_fastpath(self):
        from rpython.jit.backend.llsupport.gc import STMReadBarrierDescr
        descr = STMReadBarrierDescr(self.cpu.gc_ll_descr, 'A2R')

        called = []
        def read(obj):
            called.append(obj)
            return obj

        functype = lltype.Ptr(lltype.FuncType(
            [llmemory.Address], llmemory.Address))
        funcptr = llhelper(functype, read)
        descr.b_failing_case_ptr = funcptr
        descr.llop1 = fakellop()

        # -------- TEST --------
        for rev in [fakellop.PRIV_REV+4, fakellop.PRIV_REV]:
            called[:] = []
            
            s = self.allocate_prebuilt_s()
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            s.h_revision = rev

            descr._do_barrier(sgcref,
                              returns_modified_object=True)
                        
            # check if rev-fastpath worked
            if rev == fakellop.PRIV_REV:
                # fastpath
                self.assert_not_in(called, [sgcref])
            else:
                self.assert_in(called, [sgcref])

            # now check if sgcref in readcache:
            called[:] = []
            descr.llop1.set_cache_item(sgcref, sgcref)
            descr._do_barrier(sgcref,
                              returns_modified_object=True)
            self.assert_not_in(called, [sgcref])
            descr.llop1.set_cache_item(sgcref, 0)


    def test_gc_repeat_read_barrier_fastpath(self):
        from rpython.jit.backend.llsupport.gc import STMReadBarrierDescr
        descr = STMReadBarrierDescr(self.cpu.gc_ll_descr, 'Q2R')

        called = []
        def read(obj):
            called.append(obj)
            return obj

        functype = lltype.Ptr(lltype.FuncType(
            [llmemory.Address], llmemory.Address))
        funcptr = llhelper(functype, read)
        descr.b_failing_case_ptr = funcptr
        descr.llop1 = fakellop()

        # -------- TEST --------
        for flags in [StmGC.GCFLAG_PUBLIC_TO_PRIVATE|StmGC.GCFLAG_MOVED, 0]:
            called[:] = []
            
            s = self.allocate_prebuilt_s()
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            s.h_tid |= flags

            descr._do_barrier(sgcref,
                              returns_modified_object=True)
                        
            # check if rev-fastpath worked
            if not flags:
                # fastpath
                self.assert_not_in(called, [sgcref])
            else:
                self.assert_in(called, [sgcref])

    def test_gc_immutable_read_barrier_fastpath(self):
        from rpython.jit.backend.llsupport.gc import STMReadBarrierDescr
        descr = STMReadBarrierDescr(self.cpu.gc_ll_descr, 'A2I')

        called = []
        def read(obj):
            called.append(obj)
            return obj

        functype = lltype.Ptr(lltype.FuncType(
            [llmemory.Address], llmemory.Address))
        funcptr = llhelper(functype, read)
        descr.b_failing_case_ptr = funcptr
        descr.llop1 = fakellop()

        # -------- TEST --------
        for flags in [StmGC.GCFLAG_STUB, 0]:
            called[:] = []
            
            s = self.allocate_prebuilt_s()
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            s.h_tid |= flags

            descr._do_barrier(sgcref, returns_modified_object=True)
                        
            # check if rev-fastpath worked
            if not flags:
                # fastpath
                self.assert_not_in(called, [sgcref])
            else:
                self.assert_in(called, [sgcref])



    def test_gc_write_barrier_fastpath(self):
        from rpython.jit.backend.llsupport.gc import STMWriteBarrierDescr
        descr = STMWriteBarrierDescr(self.cpu.gc_ll_descr, 'A2W')

        called = []
        def write(obj):
            called.append(obj)
            return obj

        functype = lltype.Ptr(lltype.FuncType(
            [llmemory.Address], llmemory.Address))
        funcptr = llhelper(functype, write)
        descr.b_failing_case_ptr = funcptr
        descr.llop1 = fakellop()

        # -------- TEST --------
        for rev in [fakellop.PRIV_REV+4, fakellop.PRIV_REV]:
            called[:] = []
            
            s = self.allocate_prebuilt_s()
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            s.h_revision = rev

            descr._do_barrier(sgcref,
                              returns_modified_object=True)
                        
            # check if fastpath worked
            if rev == fakellop.PRIV_REV:
                # fastpath
                self.assert_not_in(called, [sgcref])
            else:
                self.assert_in(called, [sgcref])
                
            # now set WRITE_BARRIER -> always call slowpath
            called[:] = []
            s.h_tid |= StmGC.GCFLAG_WRITE_BARRIER
            descr._do_barrier(sgcref, 
                              returns_modified_object=True)
            self.assert_in(called, [sgcref])

    def test_gc_repeat_write_barrier_fastpath(self):
        from rpython.jit.backend.llsupport.gc import STMWriteBarrierDescr
        descr = STMWriteBarrierDescr(self.cpu.gc_ll_descr, 'V2W')

        called = []
        def write(obj):
            called.append(obj)
            return obj

        functype = lltype.Ptr(lltype.FuncType(
            [llmemory.Address], llmemory.Address))
        funcptr = llhelper(functype, write)
        descr.b_failing_case_ptr = funcptr
        descr.llop1 = fakellop()

        # -------- TEST --------
        s = self.allocate_prebuilt_s()
        sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)

        descr._do_barrier(sgcref,
                          returns_modified_object=True)
                        
        # fastpath (WRITE_BARRIER not set)
        self.assert_not_in(called, [sgcref])

        # now set WRITE_BARRIER -> always call slowpath
        s.h_tid |= StmGC.GCFLAG_WRITE_BARRIER
        descr._do_barrier(sgcref, 
            returns_modified_object=True)
        self.assert_in(called, [sgcref])

    def test_gc_noptr_write_barrier_fastpath(self):
        from rpython.jit.backend.llsupport.gc import STMWriteBarrierDescr
        descr = STMWriteBarrierDescr(self.cpu.gc_ll_descr, 'A2V')

        called = []
        def write(obj):
            called.append(obj)
            return obj

        functype = lltype.Ptr(lltype.FuncType(
            [llmemory.Address], llmemory.Address))
        funcptr = llhelper(functype, write)
        descr.b_failing_case_ptr = funcptr
        descr.llop1 = fakellop()

        # -------- TEST --------
        for rev in [fakellop.PRIV_REV+4, fakellop.PRIV_REV]:
            called[:] = []
            
            s = self.allocate_prebuilt_s()
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            s.h_revision = rev

            descr._do_barrier(sgcref, returns_modified_object=True)
                        
            # check if fastpath worked
            if rev == fakellop.PRIV_REV:
                # fastpath
                self.assert_not_in(called, [sgcref])
            else:
                self.assert_in(called, [sgcref])
                
            # now set WRITE_BARRIER -> no effect
            called[:] = []
            s.h_tid |= StmGC.GCFLAG_WRITE_BARRIER
            descr._do_barrier(sgcref, returns_modified_object=True)
            if rev == fakellop.PRIV_REV:
                # fastpath
                self.assert_not_in(called, [sgcref])
            else:
                self.assert_in(called, [sgcref])

                        
        
    def test_read_barrier_fastpath(self):
        cpu = self.cpu
        cpu.gc_ll_descr.init_nursery(100)
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
                             descr=self.a2rd),
                ResOperation(rop.FINISH, [p0], None, 
                             descr=BasicFinalDescr(0)),
                ]
            inputargs = [p0]
            looptoken = JitCellToken()
            cpu.compile_loop(None, inputargs, operations, looptoken)
            self.cpu.execute_token(looptoken, sgcref)
            
            # check if rev-fastpath worked
            if rev == PRIV_REV:
                # fastpath
                self.assert_not_in(called_on, [sgcref])
            else:
                self.assert_in(called_on, [sgcref])

            # now add it to the read-cache and check
            # that it will never call the read_barrier
            cpu.gc_ll_descr.clear_lists()
            self.set_cache_item(sgcref)
            
            self.cpu.execute_token(looptoken, sgcref)
            # not called:
            assert not called_on

    def test_repeat_read_barrier_fastpath(self):
        cpu = self.cpu
        cpu.gc_ll_descr.init_nursery(100)
        cpu.setup_once()

        called_on = cpu.gc_ll_descr.rb_called_on
        for flags in [StmGC.GCFLAG_PUBLIC_TO_PRIVATE|StmGC.GCFLAG_MOVED, 0]:
            cpu.gc_ll_descr.clear_lists()
            self.clear_read_cache()
            
            s = self.allocate_prebuilt_s()
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            s.h_tid |= flags
            
            p0 = BoxPtr()
            operations = [
                ResOperation(rop.COND_CALL_STM_B, [p0], None,
                             descr=self.q2rd),
                ResOperation(rop.FINISH, [p0], None, 
                             descr=BasicFinalDescr(0)),
                ]
            inputargs = [p0]
            looptoken = JitCellToken()
            cpu.compile_loop(None, inputargs, operations, looptoken)
            self.cpu.execute_token(looptoken, sgcref)
            
            # check if rev-fastpath worked
            if not flags:
                # fastpath
                self.assert_not_in(called_on, [sgcref])
            else:
                self.assert_in(called_on, [sgcref])

    def test_immutable_read_barrier_fastpath(self):
        cpu = self.cpu
        cpu.gc_ll_descr.init_nursery(100)
        cpu.setup_once()

        called_on = cpu.gc_ll_descr.rb_called_on
        for flags in [StmGC.GCFLAG_STUB, 0]:
            cpu.gc_ll_descr.clear_lists()
            self.clear_read_cache()
            
            s = self.allocate_prebuilt_s()
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            s.h_tid |= flags
            
            p0 = BoxPtr()
            operations = [
                ResOperation(rop.COND_CALL_STM_B, [p0], None,
                             descr=self.a2id),
                ResOperation(rop.FINISH, [p0], None, 
                             descr=BasicFinalDescr(0)),
                ]
            inputargs = [p0]
            looptoken = JitCellToken()
            cpu.compile_loop(None, inputargs, operations, looptoken)
            self.cpu.execute_token(looptoken, sgcref)
            
            # check if rev-fastpath worked
            if not flags:
                # fastpath
                self.assert_not_in(called_on, [sgcref])
            else:
                self.assert_in(called_on, [sgcref])



    def test_write_barrier_fastpath(self):
        cpu = self.cpu
        cpu.gc_ll_descr.init_nursery(100)
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
                             descr=self.a2wd),
                ResOperation(rop.FINISH, [p0], None, 
                             descr=BasicFinalDescr(0)),
                ]
            inputargs = [p0]
            looptoken = JitCellToken()
            cpu.compile_loop(None, inputargs, operations, looptoken)
            self.cpu.execute_token(looptoken, sgcref)
            
            # check if rev-fastpath worked
            if rev == PRIV_REV:
                # fastpath and WRITE_BARRIER not set
                self.assert_not_in(called_on, [sgcref])
            else:
                self.assert_in(called_on, [sgcref])

            # now set WRITE_BARRIER -> always call slowpath
            cpu.gc_ll_descr.clear_lists()
            s.h_tid |= StmGC.GCFLAG_WRITE_BARRIER
            self.cpu.execute_token(looptoken, sgcref)
            self.assert_in(called_on, [sgcref])

    def test_repeat_write_barrier_fastpath(self):
        cpu = self.cpu
        cpu.gc_ll_descr.init_nursery(100)
        cpu.setup_once()

        called_on = cpu.gc_ll_descr.wb_called_on
        cpu.gc_ll_descr.clear_lists()
            
        s = self.allocate_prebuilt_s()
        sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)

        p0 = BoxPtr()
        operations = [
            ResOperation(rop.COND_CALL_STM_B, [p0], None,
                         descr=self.v2wd),
            ResOperation(rop.FINISH, [p0], None, 
                        descr=BasicFinalDescr(0)),
            ]
        
        inputargs = [p0]
        looptoken = JitCellToken()
        cpu.compile_loop(None, inputargs, operations, looptoken)
        self.cpu.execute_token(looptoken, sgcref)
            
        # fastpath and WRITE_BARRIER not set
        self.assert_not_in(called_on, [sgcref])

        # now set WRITE_BARRIER -> always call slowpath
        cpu.gc_ll_descr.clear_lists()
        s.h_tid |= StmGC.GCFLAG_WRITE_BARRIER
        self.cpu.execute_token(looptoken, sgcref)
        self.assert_in(called_on, [sgcref])

    def test_noptr_write_barrier_fastpath(self):
        cpu = self.cpu
        cpu.gc_ll_descr.init_nursery(100)
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
                             descr=self.a2vd),
                ResOperation(rop.FINISH, [p0], None, 
                             descr=BasicFinalDescr(0)),
                ]
            inputargs = [p0]
            looptoken = JitCellToken()
            cpu.compile_loop(None, inputargs, operations, looptoken)
            self.cpu.execute_token(looptoken, sgcref)
            
            # check if rev-fastpath worked
            if rev == PRIV_REV:
                # fastpath and WRITE_BARRIER not set
                self.assert_not_in(called_on, [sgcref])
            else:
                self.assert_in(called_on, [sgcref])

            # now set WRITE_BARRIER -> no effect
            cpu.gc_ll_descr.clear_lists()
            s.h_tid |= StmGC.GCFLAG_WRITE_BARRIER
            self.cpu.execute_token(looptoken, sgcref)
            if rev == PRIV_REV:
                # fastpath and WRITE_BARRIER not set
                self.assert_not_in(called_on, [sgcref])
            else:
                self.assert_in(called_on, [sgcref])

            
    def test_ptr_eq_fastpath(self):
        cpu = self.cpu
        cpu.gc_ll_descr.init_nursery(100)
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
                for guard in [None, rop.GUARD_TRUE, rop.GUARD_FALSE,
                              rop.GUARD_VALUE]:
                    cpu.gc_ll_descr.clear_lists()

                    # BUILD OPERATIONS:
                    i = i0
                    guarddescr = BasicFailDescr()
                    finaldescr = BasicFinalDescr()
                    if guard == rop.GUARD_VALUE:
                        gop = ResOperation(rop.GUARD_VALUE, [p1, p2], None,
                                           descr=guarddescr)
                        gop.setfailargs([])
                        operations = [gop]
                        i = i1
                    else:
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
                    print operations

                    
                    # COMPILE & EXECUTE LOOP:
                    inputargs = [p for p in (p1, p2) 
                                 if not isinstance(p, Const)]
                    looptoken = JitCellToken()
                    c_loop = cpu.compile_loop(None, inputargs + [i1],
                                              operations, looptoken)

                    args = [s for i, s in enumerate((s1, s2))
                            if not isinstance((p1, p2)[i], Const)] + [7]
                                        
                    deadframe = self.cpu.execute_token(looptoken, *args)
                    frame = rffi.cast(JITFRAMEPTR, deadframe)
                    frame_adr = rffi.cast(lltype.Signed, frame.jf_descr)
                    guard_failed = frame_adr != id(finaldescr)

                    # CHECK:
                    a, b = cast_to_int(s1), cast_to_int(s2)
                    if isinstance(p1, Const):
                        a = cast_to_int(p1.value)
                    if isinstance(p2, Const):
                        b = cast_to_int(p2.value)
                        
                    # XXX: there is now no function being called in the
                    # slowpath, so we can't check if fast- vs. slowpath
                    # works :/
                    
                    # if a == b or a == 0 or b == 0:
                    #     assert (a, b) not in called_on
                    #     assert (b, a) not in called_on
                    # else:
                    #     assert ([(a, b)] == called_on
                    #             or [(b, a)] == called_on)

                    if guard is not None:
                        if a == b:
                            if guard in (rop.GUARD_TRUE, rop.GUARD_VALUE):
                                assert not guard_failed
                            else:
                                assert guard_failed
                        elif guard == rop.GUARD_FALSE:
                            assert not guard_failed
                        else:
                            assert guard_failed


    
        
    def test_assembler_call(self):
        cpu = self.cpu
        cpu.gc_ll_descr.init_nursery(100)
        cpu.setup_once()
        
        called = []
        def assembler_helper(deadframe, virtualizable):
            frame = rffi.cast(JITFRAMEPTR, deadframe)
            frame_adr = rffi.cast(lltype.Signed, frame.jf_descr)
            called.append(frame_adr)
            return 4 + 9

        FUNCPTR = lltype.Ptr(lltype.FuncType([llmemory.GCREF,
                                              llmemory.GCREF],
                                             lltype.Signed))
        class FakeJitDriverSD:
            index_of_virtualizable = -1
            _assembler_helper_ptr = llhelper(FUNCPTR, assembler_helper)
            assembler_helper_adr = llmemory.cast_ptr_to_adr(
                _assembler_helper_ptr)

        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7, i8, i9]
        i10 = int_add(i0, i1)
        i11 = int_add(i10, i2)
        i12 = int_add(i11, i3)
        i13 = int_add(i12, i4)
        i14 = int_add(i13, i5)
        i15 = int_add(i14, i6)
        i16 = int_add(i15, i7)
        i17 = int_add(i16, i8)
        i18 = int_add(i17, i9)
        finish(i18)'''
        loop = parse(ops)
        looptoken = JitCellToken()
        looptoken.outermost_jitdriver_sd = FakeJitDriverSD()
        finish_descr = loop.operations[-1].getdescr()
        self.cpu.done_with_this_frame_descr_int = BasicFinalDescr()
        self.cpu.compile_loop(None, loop.inputargs, loop.operations, looptoken)
        ARGS = [lltype.Signed] * 10
        RES = lltype.Signed
        FakeJitDriverSD.portal_calldescr = self.cpu.calldescrof(
            lltype.Ptr(lltype.FuncType(ARGS, RES)), ARGS, RES,
            EffectInfo.MOST_GENERAL)
        args = [i+1 for i in range(10)]
        deadframe = self.cpu.execute_token(looptoken, *args)
        
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7, i8, i9]
        i10 = int_add(i0, 42)
        i11 = call_assembler(i10, i1, i2, i3, i4, i5, i6, i7, i8, i9, descr=looptoken)
        guard_not_forced()[]
        finish(i11)
        '''
        loop = parse(ops, namespace=locals())
        othertoken = JitCellToken()
        self.cpu.compile_loop(None, loop.inputargs, loop.operations,
                              othertoken)
        args = [i+1 for i in range(10)]
        deadframe = self.cpu.execute_token(othertoken, *args)
        assert called == [id(finish_descr)]
        del called[:]
        
        # compile a replacement
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7, i8, i9]
        i10 = int_sub(i0, i1)
        i11 = int_sub(i10, i2)
        i12 = int_sub(i11, i3)
        i13 = int_sub(i12, i4)
        i14 = int_sub(i13, i5)
        i15 = int_sub(i14, i6)
        i16 = int_sub(i15, i7)
        i17 = int_sub(i16, i8)
        i18 = int_sub(i17, i9)
        finish(i18)'''
        loop2 = parse(ops)
        looptoken2 = JitCellToken()
        looptoken2.outermost_jitdriver_sd = FakeJitDriverSD()
        self.cpu.compile_loop(None, loop2.inputargs, loop2.operations,
                              looptoken2)
        finish_descr2 = loop2.operations[-1].getdescr()

        # install it
        self.cpu.redirect_call_assembler(looptoken, looptoken2)

        # now call_assembler should go to looptoken2
        args = [i+1 for i in range(10)]
        deadframe = self.cpu.execute_token(othertoken, *args)
        assert called == [id(finish_descr2)]


    def test_call_malloc_gc(self):
        cpu = self.cpu
        cpu.gc_ll_descr.init_nursery(100)
        cpu.setup_once()

        size = WORD*3
        addr = cpu.gc_ll_descr.get_malloc_fn_addr('malloc_big_fixedsize')
        typeid = 11
        descr = cpu.gc_ll_descr.malloc_big_fixedsize_descr

        p0 = BoxPtr()
        ops1 = [ResOperation(rop.CALL_MALLOC_GC, 
                             [ConstInt(addr), ConstInt(size), ConstInt(typeid)],
                             p0, descr),
                ResOperation(rop.FINISH, [p0], None, 
                             descr=BasicFinalDescr(0)),
                ]

        inputargs = []
        looptoken = JitCellToken()
        c_loop = cpu.compile_loop(None, inputargs, ops1, 
                                  looptoken)
        
        args = []
        
        frame = self.cpu.execute_token(looptoken, *args)


    def test_assembler_call_propagate_exc(self):
        cpu = self.cpu
        cpu._setup_descrs()
        cpu.gc_ll_descr.init_nursery(100)

        excdescr = BasicFailDescr(666)
        cpu.propagate_exception_descr = excdescr
        cpu.setup_once()    # xxx redo it, because we added
                            # propagate_exception

        def assembler_helper(deadframe, virtualizable):
            #assert cpu.get_latest_descr(deadframe) is excdescr
            # let's assume we handled that
            return 3

        FUNCPTR = lltype.Ptr(lltype.FuncType([llmemory.GCREF,
                                              llmemory.GCREF],
                                             lltype.Signed))
        class FakeJitDriverSD:
            index_of_virtualizable = -1
            _assembler_helper_ptr = llhelper(FUNCPTR, assembler_helper)
            assembler_helper_adr = llmemory.cast_ptr_to_adr(
                _assembler_helper_ptr)



        addr = cpu.gc_ll_descr.get_malloc_fn_addr('malloc_big_fixedsize')
        typeid = 11
        descr = cpu.gc_ll_descr.malloc_big_fixedsize_descr

        p0 = BoxPtr()
        i0 = BoxInt()
        ops = [ResOperation(rop.CALL_MALLOC_GC, 
                            [ConstInt(addr), i0, ConstInt(typeid)],
                            p0, descr),
               ResOperation(rop.FINISH, [p0], None, 
                            descr=BasicFinalDescr(0)),
               ]

        inputargs = [i0]
        looptoken = JitCellToken()
        looptoken.outermost_jitdriver_sd = FakeJitDriverSD()
        c_loop = cpu.compile_loop(None, inputargs, ops, looptoken)
        
        ARGS = [lltype.Signed] * 10
        RES = lltype.Signed
        FakeJitDriverSD.portal_calldescr = cpu.calldescrof(
            lltype.Ptr(lltype.FuncType(ARGS, RES)), ARGS, RES,
            EffectInfo.MOST_GENERAL)
        i1 = ConstInt(sys.maxint - 1)
        i2 = BoxInt()
        finaldescr = BasicFinalDescr(1)
        not_forced = ResOperation(rop.GUARD_NOT_FORCED, [], None,
                                  descr=BasicFailDescr(1))
        not_forced.setfailargs([])
        no_exception = ResOperation(rop.GUARD_NO_EXCEPTION, [], None,
                                    descr=BasicFailDescr(2))
        no_exception.setfailargs([])
        ops = [ResOperation(rop.CALL_ASSEMBLER, [i1], i2, descr=looptoken),
               not_forced,
               no_exception,
               ResOperation(rop.FINISH, [i1], None, descr=finaldescr),
               ]
        othertoken = JitCellToken()
        cpu.done_with_this_frame_descr_int = BasicFinalDescr()
        c_loop = cpu.compile_loop(None, [], ops, othertoken)
        
        deadframe = cpu.execute_token(othertoken)
        frame = rffi.cast(JITFRAMEPTR, deadframe)
        descr = rffi.cast(lltype.Signed, frame.jf_descr)
        assert descr != id(finaldescr)


    def test_write_barrier_on_spilled(self):
        cpu = self.cpu

        PRIV_REV = rffi.cast(lltype.Signed, StmGC.PREBUILT_REVISION)
        self.priv_rev_num[0] = PRIV_REV

        s = self.allocate_prebuilt_s()
        other_s = self.allocate_prebuilt_s()
        sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
        other_sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, other_s)
        s.h_revision = PRIV_REV+4
        other_s.h_revision = PRIV_REV+4

        called_on = []
        def write_barrier(obj):
            called_on.append(obj)
            if llmemory.cast_ptr_to_adr(sgcref) == obj:
                return rffi.cast(llmemory.Address, other_sgcref)
            return obj
        A2W = FakeSTMBarrier(cpu.gc_ll_descr, 'A2W', write_barrier)
        old_a2w = cpu.gc_ll_descr.A2Wdescr
        cpu.gc_ll_descr.A2Wdescr = A2W

        cpu.gc_ll_descr.init_nursery(100)
        cpu.setup_once()

        
        from rpython.jit.tool.oparser import FORCE_SPILL
        p0 = BoxPtr()
        spill = FORCE_SPILL(None)
        spill.initarglist([p0])
        operations = [
            ResOperation(rop.COND_CALL_STM_B, [p0], None,
                         descr=A2W),
            spill,
            ResOperation(rop.COND_CALL_STM_B, [p0], None,
                         descr=A2W),
            ResOperation(rop.FINISH, [p0], None, 
                             descr=BasicFinalDescr(0)),
            ]
        inputargs = [p0]
        looptoken = JitCellToken()
        print cpu.compile_loop(None, inputargs, operations, looptoken)
        cpu.execute_token(looptoken, sgcref)

        # the second write-barrier must see the result of the
        # first one
        self.assert_in(called_on, [sgcref, other_sgcref])

        # for other tests:
        cpu.gc_ll_descr.A2Wdescr = old_a2w

    
        


        


        
