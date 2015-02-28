from test_rewrite import get_size_descr, get_array_descr, get_description, BaseFakeCPU
from rpython.jit.backend.llsupport.descr import get_size_descr,\
     get_field_descr, get_array_descr, ArrayDescr, FieldDescr,\
     SizeDescrWithVTable, get_interiorfield_descr
from rpython.jit.backend.llsupport.gc import GcLLDescr_boehm,\
     GcLLDescr_framework, MovableObjectTracker
from rpython.jit.backend.llsupport import jitframe, gc
from rpython.jit.metainterp.gc import get_description
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.codewriter.heaptracker import register_known_gctype
from rpython.jit.metainterp.history import JitCellToken, FLOAT
from rpython.rtyper.lltypesystem import lltype, rffi, lltype, llmemory
from rpython.rtyper import rclass
from rpython.jit.backend.x86.arch import WORD
from rpython.rlib import rgc

class Evaluator(object):
    def __init__(self, scope):
        self.scope = scope
    def __getitem__(self, key):
        return eval(key, self.scope)


class FakeLoopToken(object):
    pass

# The following class is based on rpython.jit.backend.llsupport.test.test_rewrite.RewriteTests.
# It's modified to be able to test the object pinning specific features.
class RewriteTests(object):
    def check_rewrite(self, frm_operations, to_operations, **namespace):
        # objects to use inside the test
        A = lltype.GcArray(lltype.Signed)
        adescr = get_array_descr(self.gc_ll_descr, A)
        adescr.tid = 4321
        alendescr = adescr.lendescr
        #
        pinned_obj_type = lltype.GcStruct('PINNED_STRUCT', ('my_int', lltype.Signed))
        pinned_obj_my_int_descr = get_field_descr(self.gc_ll_descr, pinned_obj_type, 'my_int')
        pinned_obj_ptr = lltype.malloc(pinned_obj_type)
        pinned_obj_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, pinned_obj_ptr)
        assert rgc.pin(pinned_obj_gcref)
        #
        notpinned_obj_type = lltype.GcStruct('NOT_PINNED_STRUCT', ('my_int', lltype.Signed))
        notpinned_obj_my_int_descr = get_field_descr(self.gc_ll_descr, notpinned_obj_type, 'my_int')
        notpinned_obj_ptr = lltype.malloc(notpinned_obj_type)
        notpinned_obj_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, notpinned_obj_ptr)
        #
        ptr_array_descr = self.cpu.arraydescrof(MovableObjectTracker.ptr_array_type)
        #
        vtable_descr = self.gc_ll_descr.fielddescr_vtable
        O = lltype.GcStruct('O', ('parent', rclass.OBJECT),
                                 ('x', lltype.Signed))
        o_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        register_known_gctype(self.cpu, o_vtable, O)
        #
        tiddescr = self.gc_ll_descr.fielddescr_tid
        wbdescr = self.gc_ll_descr.write_barrier_descr
        WORD = globals()['WORD']
        #
        strdescr     = self.gc_ll_descr.str_descr
        unicodedescr = self.gc_ll_descr.unicode_descr
        strlendescr     = strdescr.lendescr
        unicodelendescr = unicodedescr.lendescr

        casmdescr = JitCellToken()
        clt = FakeLoopToken()
        clt._ll_initial_locs = [0, 8]
        frame_info = lltype.malloc(jitframe.JITFRAMEINFO, flavor='raw')
        clt.frame_info = frame_info
        frame_info.jfi_frame_depth = 13
        frame_info.jfi_frame_size = 255
        framedescrs = self.gc_ll_descr.getframedescrs(self.cpu)
        framelendescr = framedescrs.arraydescr.lendescr
        jfi_frame_depth = framedescrs.jfi_frame_depth
        jfi_frame_size = framedescrs.jfi_frame_size
        jf_frame_info = framedescrs.jf_frame_info
        signedframedescr = self.cpu.signedframedescr
        floatframedescr = self.cpu.floatframedescr
        casmdescr.compiled_loop_token = clt
        tzdescr = None # noone cares
        #
        namespace.update(locals())
        #
        for funcname in self.gc_ll_descr._generated_functions:
            namespace[funcname] = self.gc_ll_descr.get_malloc_fn(funcname)
            namespace[funcname + '_descr'] = getattr(self.gc_ll_descr,
                                                     '%s_descr' % funcname)
        #
        ops = parse(frm_operations, namespace=namespace)
        operations = self.gc_ll_descr.rewrite_assembler(self.cpu,
                                                        ops.operations,
                                                        [])
        # make the array containing the GCREF's accessible inside the tests.
        # This must be done after we call 'rewrite_assembler'. Before that
        # call 'last_moving_obj_tracker' is None or filled with some old
        # value.
        namespace['ptr_array_gcref'] = self.gc_ll_descr.last_moving_obj_tracker.ptr_array_gcref
        expected = parse(to_operations % Evaluator(namespace),
                         namespace=namespace)
        equaloplists(operations, expected.operations)
        lltype.free(frame_info, flavor='raw')

class TestFramework(RewriteTests):
    def setup_method(self, meth):
        class config_(object):
            class translation(object):
                gc = 'minimark'
                gcrootfinder = 'asmgcc'
                gctransformer = 'framework'
                gcremovetypeptr = False
        gcdescr = get_description(config_)
        self.gc_ll_descr = GcLLDescr_framework(gcdescr, None, None, None,
                                               really_not_translated=True)
        self.gc_ll_descr.write_barrier_descr.has_write_barrier_from_array = (
            lambda cpu: True)
        #
        class FakeCPU(BaseFakeCPU):
            def sizeof(self, STRUCT):
                descr = SizeDescrWithVTable(104)
                descr.tid = 9315
                return descr
        self.cpu = FakeCPU()

    def test_simple_getfield(self):
        self.check_rewrite("""
            []
            i0 = getfield_gc(ConstPtr(pinned_obj_gcref), descr=pinned_obj_my_int_descr)
            """, """
            []
            p1 = getarrayitem_gc(ConstPtr(ptr_array_gcref), 0, descr=ptr_array_descr)
            i0 = getfield_gc(p1, descr=pinned_obj_my_int_descr)
            """)
        assert len(self.gc_ll_descr.last_moving_obj_tracker._indexes) == 1

    def test_simple_getfield_twice(self):
        self.check_rewrite("""
            []
            i0 = getfield_gc(ConstPtr(pinned_obj_gcref), descr=pinned_obj_my_int_descr)
            i1 = getfield_gc(ConstPtr(notpinned_obj_gcref), descr=notpinned_obj_my_int_descr)
            i2 = getfield_gc(ConstPtr(pinned_obj_gcref), descr=pinned_obj_my_int_descr)
            """, """
            []
            p1 = getarrayitem_gc(ConstPtr(ptr_array_gcref), 0, descr=ptr_array_descr)
            i0 = getfield_gc(p1, descr=pinned_obj_my_int_descr)
            i1 = getfield_gc(ConstPtr(notpinned_obj_gcref), descr=notpinned_obj_my_int_descr)
            p2 = getarrayitem_gc(ConstPtr(ptr_array_gcref), 1, descr=ptr_array_descr)
            i2 = getfield_gc(p2, descr=pinned_obj_my_int_descr)
            """)
        assert len(self.gc_ll_descr.last_moving_obj_tracker._indexes) == 2
