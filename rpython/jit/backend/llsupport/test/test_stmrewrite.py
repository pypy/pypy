from rpython.jit.backend.llsupport.descr import *
from rpython.jit.backend.llsupport.gc import *
from rpython.jit.metainterp.gc import get_description
from rpython.jit.metainterp import resoperation
from rpython.jit.backend.llsupport.test.test_rewrite import (
    RewriteTests, BaseFakeCPU, o_vtable)
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rtyper import rclass


def test_all_operations_with_gc_in_their_name():
    # hack, but will fail if we add a new ResOperation that is not
    # always pure or a guard, and we forget about it
    import os, re
    with open(os.path.join(os.path.dirname(
          os.path.dirname(os.path.abspath(__file__))), 'stmrewrite.py')) as f:
        source = f.read()
        words = re.split("\W", source)
    # op names where it's ok if stmrewrite doesn't mention
    # them individually:
    for opnum, name in resoperation.opname.items():
        if (rop._ALWAYS_PURE_FIRST <= opnum <= rop._ALWAYS_PURE_LAST or
            rop._CALL_FIRST <= opnum <= rop._CALL_LAST or
            rop._GUARD_FIRST <= opnum <= rop._GUARD_LAST or
            rop._OVF_FIRST <= opnum <= rop._OVF_LAST):
            words.append(name)
    # extra op names where it's ok if stmrewrite doesn't mention them:
    words.append('CALL_MALLOC_GC')
    words.append('COND_CALL_GC_WB')
    words.append('COND_CALL_GC_WB_ARRAY')
    # these are handled by rewrite.py (sometimes with some overridden code
    # in stmrewrite.py too)
    words.append('DEBUG_MERGE_POINT')
    words.append('GETFIELD_GC_I')
    words.append('GETFIELD_GC_R')
    words.append('GETFIELD_GC_F')
    words.append('SETFIELD_GC')
    words.append('SETARRAYITEM_GC')
    words.append('VEC_SETARRAYITEM_GC')
    words.append('SETINTERIORFIELD_GC')
    words.append('NEW')
    words.append('NEWSTR')
    words.append('NEWUNICODE')
    words.append('NEW_ARRAY')
    words.append('NEW_ARRAY_CLEAR')
    words.append('NEW_WITH_VTABLE')
    words.append('ZERO_ARRAY')
    words.append('ZERO_PTR_FIELD')
    # these always turn inevitable
    words.append('SETINTERIORFIELD_RAW')
    words.append('RAW_LOAD_I')
    words.append('RAW_LOAD_F')
    words.append('VEC_RAW_LOAD_I')
    words.append('VEC_RAW_LOAD_F')
    words.append('RAW_STORE')
    words.append('VEC_RAW_STORE')
    # these should be processed by the front-end and not reach this point
    words.append('VIRTUAL_REF')
    words.append('VIRTUAL_REF_FINISH')
    #
    words = set(words)
    missing = []
    for name in sorted(resoperation.opname.values()):
        if name not in words:
            missing.append(name)
    assert not missing


class TestStm(RewriteTests):
    def setup_method(self, meth):
        class config_(object):
            class translation(object):
                stm = True
                gc = 'stmgc'
                gcrootfinder = 'stm'
                gctransformer = 'framework'
                gcremovetypeptr = False
        gcdescr = get_description(config_)
        self.gc_ll_descr = GcLLDescr_framework(gcdescr, None, None, None,
                                               really_not_translated=True)
        self.gc_ll_descr.write_barrier_descr.has_write_barrier_from_array = (
            lambda cpu: True)
        self.gc_ll_descr.minimal_size_in_nursery = 16
        self.gc_ll_descr.malloc_zero_filled = False
        assert self.gc_ll_descr.stm
        #
        class FakeCPU(BaseFakeCPU):
            def sizeof(self, STRUCT, is_object):
                assert is_object
                descr = SizeDescr(104, gc_fielddescrs=[],
                                  vtable=o_vtable)
                descr.tid = 9315
                return descr

        self.cpu = FakeCPU()

    def check_rewrite(self, frm_operations, to_operations, **namespace):
        inev = ("call_n(ConstClass(stm_try_inevitable),"
                " descr=stm_try_inevitable_descr)")
        hcs  = ("call_n(ConstClass(stm_hint_commit_soon),"
                " descr=stm_hint_commit_soon_descr)")

        dummyalloc = "p999 = call_malloc_nursery(16)"
        frm_operations = frm_operations.replace('$INEV', inev)
        frm_operations = frm_operations.replace('$HCS', hcs)
        to_operations  = to_operations .replace('$INEV', inev)
        to_operations  = to_operations .replace('$HCS', hcs)
        to_operations  = to_operations .replace('$DUMMYALLOC', dummyalloc)
        for name, value in self.gc_ll_descr.__dict__.items():
            if name.endswith('descr') and name[1] == '2' and len(name) == 8:
                assert name not in namespace
                namespace[name] = value     # "X2Ydescr"
        self.gc_ll_descr.malloc_zero_filled = False
        RewriteTests.check_rewrite(self, frm_operations, to_operations,
                                   **namespace)

    def test_inevitable_calls(self):
        c1 = GcCache(False)
        T = lltype.GcStruct('T')
        U = lltype.GcStruct('U', ('x', lltype.Signed))
        for inev in (True, False):
            class fakeextrainfo:
                oopspecindex = 0
                def call_needs_inevitable(self):
                    return inev

            calldescr = get_call_descr(c1, [lltype.Ptr(T)], lltype.Ptr(U),
                                       fakeextrainfo())

            self.check_rewrite("""
                []
                call_n(123, descr=cd)
                jump()
            ""","""
                []
                %s
                call_n(123, descr=cd)
                $DUMMYALLOC
                jump()
            """ % ("$INEV" if inev else "",), cd=calldescr)

    def test_rewrite_one_setfield_gc(self):
        self.check_rewrite("""
            [p1, p2]
            setfield_gc(p1, p2, descr=tzdescr)
            jump()
        """, """
            [p1, p2]
            cond_call_gc_wb(p1, descr=wbdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            $DUMMYALLOC
            jump()
        """)

    def test_rewrite_one_setfield_gc_i(self):
        self.check_rewrite("""
            [p1, i2]
            setfield_gc(p1, i2, descr=tzdescr)
            jump()
        """, """
            [p1, i2]
            cond_call_gc_wb(p1, descr=wbdescr)
            setfield_gc(p1, i2, descr=tzdescr)
            $DUMMYALLOC
            jump()
        """)

    def test_rewrite_setfield_gc_const(self):
        TP = lltype.GcArray(lltype.Signed)
        NULL = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(TP))
        self.check_rewrite("""
            [p1, p2]
            setfield_gc(ConstPtr(t), p2, descr=tzdescr)
            jump()
        """, """
            [p1, p2]
            cond_call_gc_wb(ConstPtr(t), descr=wbdescr)
            setfield_gc(ConstPtr(t), p2, descr=tzdescr)
            $DUMMYALLOC
            jump()
            """, t=NULL)

    def test_rewrite_one_getfield_gc(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc_r(p1, descr=tzdescr)
            jump()
        """, """
            [p1]
            p2 = getfield_gc_r(p1, descr=tzdescr)
            stm_read(p1)
            $DUMMYALLOC
            jump()
        """)

    def test_rewrite_several_getfield_gc(self):
        self.check_rewrite("""
            [p1, p2]
            p3 = getfield_gc_r(p1, descr=tzdescr)
            p4 = getfield_gc_r(p1, descr=tzdescr)
            p5 = getfield_gc_r(p2, descr=tzdescr)
            p6 = getfield_gc_r(p1, descr=tzdescr)
            jump()
        """, """
            [p1, p2]
            p3 = getfield_gc_r(p1, descr=tzdescr)
            stm_read(p1)
            p4 = getfield_gc_r(p1, descr=tzdescr)
            p5 = getfield_gc_r(p2, descr=tzdescr)
            stm_read(p2)
            p6 = getfield_gc_r(p1, descr=tzdescr)
            $DUMMYALLOC
            jump()
        """)

    def test_rewrite_getfield_after_setfield(self):
        self.check_rewrite("""
            [p1, i2]
            setfield_gc(p1, i2, descr=tydescr)
            p3 = getfield_gc_r(p1, descr=tzdescr)
            jump(p3)
        """, """
            [p1, i2]
            cond_call_gc_wb(p1, descr=wbdescr)
            setfield_gc(p1, i2, descr=tydescr)
            p3 = getfield_gc_r(p1, descr=tzdescr)
            $DUMMYALLOC
             jump(p3)
        """)

    def test_mixed_case(self):
        TP = lltype.GcArray(lltype.Signed)
        NULL = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(TP))
        self.check_rewrite("""
            [p0, p1, p2]
            p3 = getfield_gc_r(p1, descr=tzdescr)
            setfield_gc(p2, p0, descr=tzdescr)
            p4 = getfield_gc_r(p1, descr=tzdescr)
            jump()
        """, """
            [p0, p1, p2]
            p3 = getfield_gc_r(p1, descr=tzdescr)
            stm_read(p1)
            cond_call_gc_wb(p2, descr=wbdescr)
            setfield_gc(p2, p0, descr=tzdescr)
            p4 = getfield_gc_r(p1, descr=tzdescr)
            $DUMMYALLOC
            jump()
            """, t=NULL)

    def test_rewrite_write_barrier_after_malloc(self):
        self.check_rewrite("""
            [p1, p3]
            setfield_gc(p3, p1, descr=tzdescr)
            p2 = new(descr=tdescr)
            setfield_gc(p3, p1, descr=tzdescr)
            jump(p2)
        """, """
            [p1, p3]
            cond_call_gc_wb(p3, descr=wbdescr)
            setfield_gc(p3, p1, descr=tzdescr)
            p2 = call_malloc_nursery(%(tdescr.size)d)
            setfield_gc(p2, 0, descr=stmflagsdescr)
            setfield_gc(p2, %(tdescr.tid)d, descr=tiddescr)
            cond_call_gc_wb(p3, descr=wbdescr)
            setfield_gc(p3, p1, descr=tzdescr)
            zero_ptr_field(p2, %(tdescr.gc_fielddescrs[0].offset)s)
            jump(p2)
        """)

    def test_rewrite_no_read_barrier_after_malloc(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc_r(p1, descr=tzdescr)
            p3 = new(descr=tdescr)
            p4 = getfield_gc_r(p1, descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            p2 = getfield_gc_r(p1, descr=tzdescr)
            stm_read(p1)
            p3 = call_malloc_nursery(%(tdescr.size)d)
            setfield_gc(p3, 0, descr=stmflagsdescr)
            setfield_gc(p3, %(tdescr.tid)d, descr=tiddescr)
            zero_ptr_field(p3, %(tdescr.gc_fielddescrs[0].offset)s)
            p4 = getfield_gc_r(p1, descr=tzdescr)
            jump(p2)
        """)

    def test_rewrite_setfield_gc_on_local(self):
        self.check_rewrite("""
            [p1]
            p2 = new(descr=tdescr)
            setfield_gc(p2, p1, descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            p2 = call_malloc_nursery(%(tdescr.size)d)
            setfield_gc(p2, 0, descr=stmflagsdescr)
            setfield_gc(p2, %(tdescr.tid)d, descr=tiddescr)
            setfield_gc(p2, p1, descr=tzdescr)
            jump(p2)
        """)

    def test_rewrite_getfield_gc_on_local(self):
        self.check_rewrite("""
            []
            p2 = new(descr=tdescr)
            p1 = getfield_gc_r(p2, descr=tzdescr)
            jump(p1)
        """, """
            []
            p2 = call_malloc_nursery(%(tdescr.size)d)
            setfield_gc(p2, 0, descr=stmflagsdescr)
            setfield_gc(p2, %(tdescr.tid)d, descr=tiddescr)
            zero_ptr_field(p2, %(tdescr.gc_fielddescrs[0].offset)s)
            p1 = getfield_gc_r(p2, descr=tzdescr)
            jump(p1)
        """)

    def test_rewrite_unrelated_setfield_gcs(self):
        self.check_rewrite("""
            [p1, p2, p3, p4]
            setfield_gc(p1, p2, descr=tzdescr)
            setfield_gc(p3, p4, descr=tzdescr)
            jump()
        """, """
            [p1, p2, p3, p4]
            cond_call_gc_wb(p1, descr=wbdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            cond_call_gc_wb(p3, descr=wbdescr)
            setfield_gc(p3, p4, descr=tzdescr)
            $DUMMYALLOC
            jump()
        """)

    def test_rewrite_several_setfield_gcs(self):
        self.check_rewrite("""
            [p1, p2, i3]
            setfield_gc(p1, p2, descr=tzdescr)
            setfield_gc(p1, i3, descr=tydescr)
            jump()
        """, """
            [p1, p2, i3]
            cond_call_gc_wb(p1, descr=wbdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            setfield_gc(p1, i3, descr=tydescr)
            $DUMMYALLOC
            jump()
        """)

    def test_rewrite_several_setfield_gcs_over_label(self):
        self.check_rewrite("""
            [p1, p2, i3]
            setfield_gc(p1, p2, descr=tzdescr)
            label(p1, i3)
            setfield_gc(p1, i3, descr=tydescr)
            jump(p1)
        """, """
            [p1, p2, i3]
            cond_call_gc_wb(p1, descr=wbdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            label(p1, i3)
            cond_call_gc_wb(p1, descr=wbdescr)
            setfield_gc(p1, i3, descr=tydescr)
            $DUMMYALLOC
            jump(p1)
        """)

    def test_remove_debug_merge_point(self):
        py.test.skip("why??")
        self.check_rewrite("""
            [i1, i2]
            debug_merge_point(i1, i2)
            jump()
        """, """
            [i1, i2]
            $DUMMYALLOC
            jump()
        """)

    def test_ignore_some_operations(self):
        oplist = [
            "guard_true(i1) [i2]",    # all guards
            "i3 = int_add(i1, i2)",   # all pure operations
            "f3 = float_abs(f1)",
            "i3 = force_token()",
            "jit_debug(i1, i2)",
            "keepalive(i1)",
            "i3 = int_sub_ovf(i1, i2)",   # is_ovf operations
            "increment_debug_counter(i1)",
            "restore_exception(i1, i2)",
            "p3 = save_exception()",
            "i3 = save_exc_class()",
            ]
        for op in oplist:
            testcase = """
                [i1, i2, p1, p2, f1]
                %s
                $DUMMYALLOC
                finish()
            """ % op
            self.check_rewrite(testcase.replace('$DUMMYALLOC', ''), testcase)

    def test_rewrite_getfield_gc_const(self):
        TP = lltype.GcArray(lltype.Signed)
        NULL = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(TP))
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc_r(ConstPtr(t), descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            p2 = getfield_gc_r(ConstPtr(t), descr=tzdescr)
            stm_read(ConstPtr(t))
            $DUMMYALLOC
            jump(p2)
        """, t=NULL)

    def test_rewrite_getarrayitem_gc(self):
        self.check_rewrite("""
            [p1, i2]
            i3 = getarrayitem_gc_i(p1, i2, descr=adescr)
            jump(i3)
        """, """
            [p1, i2]
            i3 = getarrayitem_gc_i(p1, i2, descr=adescr)
            stm_read(p1)
            $DUMMYALLOC
            jump(i3)
        """)

    def test_rewrite_getinteriorfield_gc(self):
        self.check_rewrite("""
            [p1, i2]
            i3 = getinteriorfield_gc_i(p1, i2, descr=intzdescr)
            jump(i3)
        """, """
            [p1, i2]
            i3 = getinteriorfield_gc_i(p1, i2, descr=intzdescr)
            stm_read(p1)
            $DUMMYALLOC
            jump(i3)
        """)

    def test_rewrite_unrelated_getfield_gcs(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc_r(p1, descr=tzdescr)
            i2 = getfield_gc_i(p2, descr=tydescr)
            jump(p2, i2)
        """, """
            [p1]
            p2 = getfield_gc_r(p1, descr=tzdescr)
            stm_read(p1)
            i2 = getfield_gc_i(p2, descr=tydescr)
            stm_read(p2)
            $DUMMYALLOC
            jump(p2, i2)
        """)

    def test_getfield_followed_by_setfield(self):
        # XXX coalesce the two barriers into one if there are e.g. no
        # calls inbetween
        self.check_rewrite("""
            [p1]
            i1 = getfield_gc_i(p1, descr=tydescr) # noptr
            i2 = int_add(i1, 1)
            setfield_gc(p1, i2, descr=tydescr) # noptr
            jump(p1)
        """, """
            [p1]
            i1 = getfield_gc_i(p1, descr=tydescr)
            stm_read(p1)
            i2 = int_add(i1, 1)
            cond_call_gc_wb(p1, descr=wbdescr)
            setfield_gc(p1, i2, descr=tydescr)
            $DUMMYALLOC
            jump(p1)
        """)

    def test_rewrite_getfield_gc_on_future_local_after_call(self):
        # XXX could detect CALLs that cannot interrupt the transaction
        # and/or could use the L category
        class fakeextrainfo:
            oopspecindex = 0
            def call_needs_inevitable(self):
                return False
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr1 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T,
                                    fakeextrainfo())
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc_r(p1, descr=tzdescr)
            call_n(p2, descr=calldescr1)
            setfield_gc(p1, 5, descr=tydescr) # noptr
            jump(p2)
        """, """
            [p1]
            p2 = getfield_gc_r(p1, descr=tzdescr)
            stm_read(p1)
            call_n(p2, descr=calldescr1)
            cond_call_gc_wb(p1, descr=wbdescr)
            setfield_gc(p1, 5, descr=tydescr)
            $DUMMYALLOC
            jump(p2)
        """, calldescr1=calldescr1)

    def test_getfield_raw(self):
        self.check_rewrite("""
            [i1, i2]
            i3 = getfield_raw_i(i1, descr=tydescr)
            keepalive(i3)
            i4 = getfield_raw_i(i2, descr=tydescr)
            jump(i3, i4)
        """, """
            [i1, i2]
            $INEV
            i3 = getfield_raw_i(i1, descr=tydescr)
            keepalive(i3)
            i4 = getfield_raw_i(i2, descr=tydescr)
            $DUMMYALLOC
            jump(i3, i4)
        """)

    def test_getfield_raw_stm_dont_track_raw_accesses(self):
        c1 = GcCache(False)
        F = lltype.Struct('F', ('x', lltype.Signed),
                          hints={'stm_dont_track_raw_accesses': True})
        fdescr = get_field_descr(c1, F, 'x')
        self.check_rewrite("""
            [i1]
            i2 = getfield_raw_i(i1, descr=fdescr)
            jump(i2)
        """, """
            [i1]
            i2 = getfield_raw_i(i1, descr=fdescr)
            $DUMMYALLOC
            jump(i2)
        """, fdescr=fdescr)

    def test_setfield_raw_stm_dont_track_raw_accesses(self):
        c1 = GcCache(False)
        F = lltype.Struct('F', ('x', lltype.Signed),
                          hints={'stm_dont_track_raw_accesses': True})
        fdescr = get_field_descr(c1, F, 'x')
        self.check_rewrite("""
            [i1]
            setfield_raw(i1, 42, descr=fdescr)
            jump(i1)
        """, """
            [i1]
            setfield_raw(i1, 42, descr=fdescr)
            $DUMMYALLOC
            jump(i1)
        """, fdescr=fdescr)

    def test_getarrayitem_raw_stm_dont_track_raw_accesses(self):
        c1 = GcCache(False)
        A = lltype.Array(lltype.Signed, hints={'nolength': True,
                            'stm_dont_track_raw_accesses': True})
        aadescr = get_array_descr(c1, A)
        assert not aadescr.stm_should_track_raw_accesses()
        self.check_rewrite("""
            [i1]
            i2 = getarrayitem_raw_i(i1, 5, descr=aadescr)
            jump(i2)
        """, """
            [i1]
            i2 = getarrayitem_raw_i(i1, 5, descr=aadescr)
            $DUMMYALLOC
            jump(i2)
        """, aadescr=aadescr)

    def test_setarrayitem_raw_stm_dont_track_raw_accesses(self):
        c1 = GcCache(False)
        A = lltype.Array(lltype.Signed, hints={'nolength': True,
                            'stm_dont_track_raw_accesses': True})
        aadescr = get_array_descr(c1, A)
        self.check_rewrite("""
            [i1]
            setarrayitem_raw(i1, 5, 42, descr=aadescr)
            jump(i1)
        """, """
            [i1]
            setarrayitem_raw(i1, 5, 42, descr=aadescr)
            $DUMMYALLOC
            jump(i1)
        """, aadescr=aadescr)

    def test_getfield_raw_over_label(self):
        self.check_rewrite("""
            [i1, i2]
            i3 = getfield_raw_i(i1, descr=tydescr)
            label(i1, i2, i3)
            i4 = getfield_raw_i(i2, descr=tydescr)
            jump(i3, i4)
        """, """
            [i1, i2]
            $INEV
            i3 = getfield_raw_i(i1, descr=tydescr)
            label(i1, i2, i3)
            $INEV
            i4 = getfield_raw_i(i2, descr=tydescr)
            $DUMMYALLOC
            jump(i3, i4)
        """)

    def test_getarrayitem_raw(self):
        self.check_rewrite("""
            [i1, i2]
            i3 = getarrayitem_raw_i(i1, 5, descr=adescr)
            i4 = getarrayitem_raw_i(i2, i3, descr=adescr)
            jump(i3, i4)
        """, """
            [i1, i2]
            $INEV
            i3 = getarrayitem_raw_i(i1, 5, descr=adescr)
            i4 = getarrayitem_raw_i(i2, i3, descr=adescr)
            $DUMMYALLOC
            jump(i3, i4)
        """)

    def test_rewrite_unrelated_setarrayitem_gcs(self):
        self.check_rewrite("""
            [p1, i1, p2, p3, i3, p4]
            setarrayitem_gc(p1, i1, p2, descr=adescr) #noptr
            setarrayitem_gc(p3, i3, p4, descr=adescr) #noptr
            jump()
        """, """
            [p1, i1, p2, p3, i3, p4]
            cond_call_gc_wb_array(p1, i1, descr=wbdescr)
            setarrayitem_gc(p1, i1, p2, descr=adescr)
            cond_call_gc_wb_array(p3, i3, descr=wbdescr)
            setarrayitem_gc(p3, i3, p4, descr=adescr)
            $DUMMYALLOC
            jump()
        """)

    def test_rewrite_several_setarrayitem_gcs(self):
        self.check_rewrite("""
            [p1, p2, i2, p3, i3]
            setarrayitem_gc(p1, i2, p2, descr=adescr) #noptr
            i4 = force_token()
            setarrayitem_gc(p1, i3, p3, descr=adescr) #noptr
            jump()
        """, """
            [p1, p2, i2, p3, i3]
            cond_call_gc_wb_array(p1, i2, descr=wbdescr)
            setarrayitem_gc(p1, i2, p2, descr=adescr)
            i4 = force_token()
            cond_call_gc_wb_array(p1, i3, descr=wbdescr)
            setarrayitem_gc(p1, i3, p3, descr=adescr)
            $DUMMYALLOC
            jump()
        """)

    def test_rewrite_several_setinteriorfield_gc(self):
        self.check_rewrite("""
            [p1, p2, i2, p3, i3]
            setinteriorfield_gc(p1, i2, p2, descr=intzdescr)
            i4 = force_token()
            setinteriorfield_gc(p1, i3, p3, descr=intzdescr)
            jump()
        """, """
            [p1, p2, i2, p3, i3]
            cond_call_gc_wb_array(p1, i2, descr=wbdescr)
            setinteriorfield_gc(p1, i2, p2, descr=intzdescr)
            i4 = force_token()
            cond_call_gc_wb_array(p1, i3, descr=wbdescr)
            setinteriorfield_gc(p1, i3, p3, descr=intzdescr)
            $DUMMYALLOC
            jump()
        """)

    def test_rewrite_strsetitem_unicodesetitem(self):
        self.check_rewrite("""
            [p1, i2, i3]
            strsetitem(p1, i2, i3)
            unicodesetitem(p1, i2, i3)
            jump()
        """, """
            [p1, i2, i3]
            cond_call_gc_wb(p1, descr=wbdescr)
            strsetitem(p1, i2, i3)
            unicodesetitem(p1, i2, i3)
            $DUMMYALLOC
            jump()
        """)

    def test_rewrite_strsetitem_unicodesetitem_on_fresh_malloc(self):
        self.check_rewrite("""
            [i2, i3]
            p1 = newstr(i3)
            strsetitem(p1, i2, i3)
            unicodesetitem(p1, i2, i3)
            jump()
        """, """
            [i2, i3]
            p1 = call_malloc_nursery_varsize(1, 1, i3, descr=strdescr)
            setfield_gc(p1, i3, descr=strlendescr)
            setfield_gc(p1, 0, descr=strhashdescr)
            cond_call_gc_wb(p1, descr=wbdescr)
            strsetitem(p1, i2, i3)
            unicodesetitem(p1, i2, i3)
            jump()
        """)

    def test_rewrite_strgetitem_unicodegetitem(self):
        self.check_rewrite("""
            [p1, i2, i3]
            i4=strgetitem(p1, i2)
            i5=unicodegetitem(p1, i2)
            jump()
        """, """
            [p1, i2, i3]
            i4=strgetitem(p1, i2)
            i5=unicodegetitem(p1, i2)
            $DUMMYALLOC
            jump()
        """)

    def test_hint_commit_soon(self):
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr2 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T)
        self.check_rewrite("""
            [i2, p7, p1]
            i1 = getfield_gc_i(p1, descr=tydescr) # noptr
            setfield_gc(p7, 10, descr=tydescr) #noptr
            stm_hint_commit_soon()
            setfield_gc(p7, 20, descr=tydescr) #noptr
            i3 = getfield_gc_i(p1, descr=tydescr) # noptr
            jump(i2, p7, i1)
        """, """
            [i2, p7, p1]
            i1 = getfield_gc_i(p1, descr=tydescr)
            stm_read(p1)

            cond_call_gc_wb(p7, descr=wbdescr)
            setfield_gc(p7, 10, descr=tydescr)

            $HCS

            cond_call_gc_wb(p7, descr=wbdescr)
            setfield_gc(p7, 20, descr=tydescr)

            i3 = getfield_gc_i(p1, descr=tydescr) # noptr
            stm_read(p1)

            $DUMMYALLOC
            jump(i2, p7, i1)
        """, calldescr2=calldescr2)



    def test_call_release_gil(self):
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr2 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T)
        self.check_rewrite("""
            [i1, i2, i3, p7]
            setfield_gc(p7, 10, descr=tydescr) #noptr
            call_release_gil_n(123, descr=calldescr2)
            guard_not_forced() []
            setfield_gc(p7, 20, descr=tydescr) #noptr
            jump(i2, p7)
        """, """
            [i1, i2, i3, p7]
            cond_call_gc_wb(p7, descr=wbdescr)
            setfield_gc(p7, 10, descr=tydescr)
            call_release_gil_n(123, descr=calldescr2)
            guard_not_forced() []

            cond_call_gc_wb(p7, descr=wbdescr)
            setfield_gc(p7, 20, descr=tydescr)

            $DUMMYALLOC
            jump(i2, p7)
        """, calldescr2=calldescr2)

    def test_fallback_to_inevitable(self):
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr2 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T)
        oplist = [
            "setfield_raw(i1, i2, descr=tydescr)",
            "setarrayitem_raw(i1, i2, i3, descr=adescr)",
            #"setinteriorfield_raw(i1, i2, i3, descr=intzdescr)", -- no such op
            "escape_n(i1)",    # a generic unknown operation
            ]
        for op in oplist:
            self.check_rewrite("""
                [i1, i2, i3, p7]
                setfield_gc(p7, 10, descr=tydescr)
                %s
                setfield_gc(p7, 20, descr=tydescr)
                jump(i2, p7)
            """ % op, """
                [i1, i2, i3, p7]
                cond_call_gc_wb(p7, descr=wbdescr)
                setfield_gc(p7, 10, descr=tydescr)
                $INEV
                %s
                cond_call_gc_wb(p7, descr=wbdescr)
                setfield_gc(p7, 20, descr=tydescr)

                $DUMMYALLOC
                jump(i2, p7)
            """ % op, calldescr2=calldescr2)

    def test_copystrcontent_new(self):
        self.check_rewrite("""
            [p1, i1, i2, i3]
            p2 = newstr(i3)
            copystrcontent(p1, p2, i1, i2, i3)
            jump()
        """, """
            [p1, i1, i2, i3]
            p2 = call_malloc_nursery_varsize(1, 1, i3, descr=strdescr)
            setfield_gc(p2, i3, descr=strlendescr)
            setfield_gc(p2, 0, descr=strhashdescr)
            cond_call_gc_wb(p2, descr=wbdescr)
            copystrcontent(p1, p2, i1, i2, i3)
            jump()
        """)

    def test_copystrcontent_old(self):
        self.check_rewrite("""
            [p1, p2, i1, i2, i3]
            copystrcontent(p1, p2, i1, i2, i3)
            jump()
        """, """
            [p1, p2, i1, i2, i3]
            cond_call_gc_wb(p2, descr=wbdescr)
            copystrcontent(p1, p2, i1, i2, i3)
            $DUMMYALLOC
            jump()
        """)

    def test_call_dont_force(self):
        py.test.skip("optimization")
        for op in ["call_n(123, descr=calldescr1)",
                   "call_may_force_n(123, descr=calldescr1)",
                   "call_loopinvariant_n(123, descr=calldescr1)",
                   ]:
            self.check_rewrite("""
                [p1]
                setfield_gc(p1, 10, descr=tydescr)
                %s
                setfield_gc(p1, 20, descr=tydescr)
                jump(p1)
            """ % op, """
                [p1]
                cond_call_stm_b(p1, descr=A2Wdescr)
                setfield_gc(p1, 10, descr=tydescr)
                %s
                setfield_gc(p1, 20, descr=tydescr)
                $DUMMYALLOC
                jump(p1)
            """ % op)

    def test_call_force(self):
        class fakeextrainfo:
            oopspecindex=0
            def call_needs_inevitable(self):
                return False
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr2 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T,
                                    fakeextrainfo())
        for op, guarded in [
                ("call_n(123, descr=calldescr2)", False),
                ("call_may_force_n(123, descr=calldescr2)", True),
                ("call_loopinvariant_n(123, descr=calldescr2)", False),
                ]:
            guard = "guard_not_forced() []" if guarded else ""
            tr_break = "" if guarded else ""
            self.check_rewrite("""
                [p1]
                setfield_gc(p1, 10, descr=tydescr)
                %s
                %s
                setfield_gc(p1, 20, descr=tydescr)
                jump(p1)
            """ % (op, guard), """
                [p1]
                cond_call_gc_wb(p1, descr=wbdescr)
                setfield_gc(p1, 10, descr=tydescr)
                %s
                %s
                %s
                cond_call_gc_wb(p1, descr=wbdescr)
                setfield_gc(p1, 20, descr=tydescr)

                $DUMMYALLOC
                jump(p1)
            """ % (op, guard, tr_break), calldescr2=calldescr2)

    def test_call_assembler(self):
        self.check_rewrite("""
        [i0, f0]
        i2 = call_assembler_i(i0, f0, descr=casmdescr)
        guard_not_forced()[]
        """, """
        [i0, f0]
        i1 = getfield_raw_i(ConstClass(frame_info), descr=jfi_frame_depth)
        p1 = call_malloc_nursery_varsize_frame(i1)
        setfield_gc(p1, 0, descr=stmflagsdescr)
        setfield_gc(p1, 0, descr=tiddescr)

        setfield_gc(p1, 0, descr=jf_extra_stack_depth)
        setfield_gc(p1, NULL, descr=jf_savedata)
        setfield_gc(p1, NULL, descr=jf_force_descr)
        setfield_gc(p1, NULL, descr=jf_descr)
        setfield_gc(p1, NULL, descr=jf_guard_exc)
        setfield_gc(p1, NULL, descr=jf_forward)

        setfield_gc(p1, i1, descr=framelendescr)
        setfield_gc(p1, ConstClass(frame_info), descr=jf_frame_info)
        setarrayitem_gc(p1, 0, i0, descr=signedframedescr)
        setarrayitem_gc(p1, 1, f0, descr=floatframedescr)
        i3 = call_assembler_i(p1, descr=casmdescr)
        guard_not_forced() []

        """)

    def test_repeat_barrier_after_call_assembler(self):
        self.check_rewrite("""
        [i0, f0, p1]
        p2 = getfield_gc_r(p1, descr=tzdescr)
        setfield_gc(p1, p2, descr=tzdescr)

        i2 = call_assembler_i(i0, f0, descr=casmdescr)
        guard_not_forced()[]

        p3 = getfield_gc_r(p1, descr=tzdescr)
        setfield_gc(p1, p3, descr=tzdescr)
        """, """
        [i0, f0, p1]
        p2 = getfield_gc_r(p1, descr=tzdescr)
        stm_read(p1)
        cond_call_gc_wb(p1, descr=wbdescr)
        setfield_gc(p1, p2, descr=tzdescr)

        i1 = getfield_raw_i(ConstClass(frame_info), descr=jfi_frame_depth)
        p5 = call_malloc_nursery_varsize_frame(i1)
        setfield_gc(p5, 0, descr=stmflagsdescr)
        setfield_gc(p5, 0, descr=tiddescr)
        setfield_gc(p5, 0, descr=jf_extra_stack_depth)
        setfield_gc(p5, NULL, descr=jf_savedata)
        setfield_gc(p5, NULL, descr=jf_force_descr)
        setfield_gc(p5, NULL, descr=jf_descr)
        setfield_gc(p5, NULL, descr=jf_guard_exc)
        setfield_gc(p5, NULL, descr=jf_forward)
        setfield_gc(p5, i1, descr=framelendescr)
        setfield_gc(p5, ConstClass(frame_info), descr=jf_frame_info)
        setarrayitem_gc(p5, 0, i0, descr=signedframedescr)
        setarrayitem_gc(p5, 1, f0, descr=floatframedescr)
        i3 = call_assembler_i(p5, descr=casmdescr)
        guard_not_forced() []

        p3 = getfield_gc_r(p1, descr=tzdescr)
        stm_read(p1)
        cond_call_gc_wb(p1, descr=wbdescr)
        setfield_gc(p1, p3, descr=tzdescr)
        """)

    def test_ptr_eq_null(self):
        self.check_rewrite("""
            [p1, p2]
            i1 = ptr_eq(p1, NULL)
        """, """
            [p1, p2]
            i1 = ptr_eq(p1, NULL)
        """)

    def test_ptr_eq(self):
        self.check_rewrite("""
            [p1, p2]
            i1 = ptr_eq(p1, p2)
        """, """
            [p1, p2]
            i1 = ptr_eq(p1, p2)
        """)

    def test_instance_ptr_eq(self):
        self.check_rewrite("""
            [p1, p2]
            i1 = instance_ptr_eq(p1, p2)
            jump(i1)
        """, """
            [p1, p2]
            i1 = instance_ptr_eq(p1, p2)
            $DUMMYALLOC
            jump(i1)
        """)

    def test_ptr_ne(self):
        self.check_rewrite("""
            [p1, p2]
            i1 = ptr_ne(p1, p2)
        """, """
            [p1, p2]
            i1 = ptr_ne(p1, p2)
        """)

    def test_instance_ptr_ne(self):
        self.check_rewrite("""
            [p1, p2]
            i1 = instance_ptr_ne(p1, p2)
        """, """
            [p1, p2]
            i1 = instance_ptr_ne(p1, p2)
        """)

    # ----------- tests copied from rewrite.py -------------

    def test_rewrite_assembler_new_to_malloc(self):
        self.check_rewrite("""
            [p1]
            p0 = new(descr=sdescr)
            jump()
        """, """
            [p1]
            p0 = call_malloc_nursery(%(sdescr.size)d)
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, 1234, descr=tiddescr)
            jump()
        """)

    def test_rewrite_assembler_new3_to_malloc(self):
        self.check_rewrite("""
            []
            p0 = new(descr=sdescr)
            p1 = new(descr=tdescr)
            p2 = new(descr=sdescr)
            jump()
        """, """
            []
            p0 = call_malloc_nursery(   \
                               %(sdescr.size + tdescr.size + sdescr.size)d)
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, 1234, descr=tiddescr)
            p1 = nursery_ptr_increment(p0, %(sdescr.size)d)
            setfield_gc(p1, 0, descr=stmflagsdescr)
            setfield_gc(p1, 5678, descr=tiddescr)
            p2 = nursery_ptr_increment(p1, %(tdescr.size)d)
            setfield_gc(p2, 0, descr=stmflagsdescr)
            setfield_gc(p2, 1234, descr=tiddescr)
            zero_ptr_field(p1, %(tdescr.gc_fielddescrs[0].offset)s)
            jump()
        """)

    def test_rewrite_assembler_new_array_fixed_to_malloc(self):
        self.check_rewrite("""
            []
            p0 = new_array(10, descr=adescr)
            jump()
        """, """
            []
            p0 = call_malloc_nursery(    \
                                %(adescr.basesize + 10 * adescr.itemsize)d)
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, 4321, descr=tiddescr)
            setfield_gc(p0, 10, descr=alendescr)
            jump()
        """)

    def test_rewrite_assembler_new_and_new_array_fixed_to_malloc(self):
        self.check_rewrite("""
            []
            p0 = new(descr=sdescr)
            p1 = new_array(10, descr=adescr)
            jump()
        """, """
            []
            p0 = call_malloc_nursery(                                  \
                                %(sdescr.size +                        \
                                  adescr.basesize + 10 * adescr.itemsize)d)
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, 1234, descr=tiddescr)
            p1 = nursery_ptr_increment(p0, %(sdescr.size)d)
            setfield_gc(p1, 0, descr=stmflagsdescr)
            setfield_gc(p1, 4321, descr=tiddescr)
            setfield_gc(p1, 10, descr=alendescr)
            jump()
        """)

    def test_rewrite_assembler_round_up(self):
        self.check_rewrite("""
            []
            p0 = new_array(6, descr=bdescr)
            jump()
        """, """
            []
            p0 = call_malloc_nursery(%(bdescr.basesize + 8)d)
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, 8765, descr=tiddescr)
            setfield_gc(p0, 6, descr=blendescr)
            jump()
        """)

    def test_rewrite_assembler_round_up_always(self):
        self.check_rewrite("""
            []
            p0 = new_array(5, descr=bdescr)
            p1 = new_array(5, descr=bdescr)
            p2 = new_array(5, descr=bdescr)
            p3 = new_array(5, descr=bdescr)
            jump()
        """, """
            []
            p0 = call_malloc_nursery(%(4 * (bdescr.basesize + 8))d)
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, 8765, descr=tiddescr)
            setfield_gc(p0, 5, descr=blendescr)
            p1 = nursery_ptr_increment(p0, %(bdescr.basesize + 8)d)
            setfield_gc(p1, 0, descr=stmflagsdescr)
            setfield_gc(p1, 8765, descr=tiddescr)
            setfield_gc(p1, 5, descr=blendescr)
            p2 = nursery_ptr_increment(p1, %(bdescr.basesize + 8)d)
            setfield_gc(p2, 0, descr=stmflagsdescr)
            setfield_gc(p2, 8765, descr=tiddescr)
            setfield_gc(p2, 5, descr=blendescr)
            p3 = nursery_ptr_increment(p2, %(bdescr.basesize + 8)d)
            setfield_gc(p3, 0, descr=stmflagsdescr)
            setfield_gc(p3, 8765, descr=tiddescr)
            setfield_gc(p3, 5, descr=blendescr)
            jump()
        """)

    def test_rewrite_assembler_minimal_size(self):
        self.check_rewrite("""
            []
            p0 = new(descr=edescr)
            p1 = new(descr=edescr)
            jump()
        """, """
            []
            p0 = call_malloc_nursery(%(4*WORD)d)
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, 9000, descr=tiddescr)
            p1 = nursery_ptr_increment(p0, %(2*WORD)d)
            setfield_gc(p1, 0, descr=stmflagsdescr)
            setfield_gc(p1, 9000, descr=tiddescr)
            jump()
        """)

    def test_rewrite_assembler_variable_size(self):
        self.check_rewrite("""
            [i0]
            p0 = new_array(i0, descr=bdescr)
            jump(i0)
        """, """
            [i0]
            p0 = call_malloc_nursery_varsize(0, 1, i0, descr=bdescr)
            setfield_gc(p0, i0, descr=blendescr)

            jump(i0)
        """)

    def test_rewrite_new_string(self):
        self.check_rewrite("""
        [i0]
        p0 = newstr(i0)
        jump(i0)
        """, """
        [i0]
        p0 = call_malloc_nursery_varsize(1, 1, i0, descr=strdescr)
        setfield_gc(p0, i0, descr=strlendescr)
        setfield_gc(p0, 0, descr=strhashdescr)
        jump(i0)
        """)

    def test_rewrite_assembler_nonstandard_array(self):
        # a non-standard array is a bit hard to get; e.g. GcArray(Float)
        # is like that on Win32, but not on Linux.  Build one manually...
        NONSTD = lltype.GcArray(lltype.Float)
        nonstd_descr = get_array_descr(self.gc_ll_descr, NONSTD)
        nonstd_descr.tid = 6464
        nonstd_descr.basesize = 64      # <= hacked
        nonstd_descr.itemsize = 8
        nonstd_descr_gcref = 123
        self.check_rewrite("""
            [i0]
            p0 = new_array(i0, descr=nonstd_descr)
            jump(i0)
        """, """
            [i0]
            p0 = call_malloc_gc(ConstClass(malloc_array_nonstandard), \
                                64, 8,                                \
                                %(nonstd_descr.lendescr.offset)d,     \
                                6464, i0,                             \
                                descr=malloc_array_nonstandard_descr)

            jump(i0)
        """, nonstd_descr=nonstd_descr)

    def test_rewrite_assembler_maximal_size_1(self):
        self.gc_ll_descr.max_size_of_young_obj = 100
        self.check_rewrite("""
            []
            p0 = new_array(103, descr=bdescr)
            jump()
        """, """
            []
            p0 = call_malloc_gc(ConstClass(malloc_array), 1,  \
                                %(bdescr.tid)d, 103,          \
                                descr=malloc_array_descr)

            jump()
        """)

    def test_rewrite_assembler_maximal_size_2(self):
        self.gc_ll_descr.max_size_of_young_obj = 300
        self.check_rewrite("""
            []
            p0 = new_array(101, descr=bdescr)
            p1 = new_array(102, descr=bdescr)  # two new_arrays can be combined
            p2 = new_array(103, descr=bdescr)  # but not all three
        """, """
            []
            p0 = call_malloc_nursery(    \
                              %(2 * (bdescr.basesize + 104))d)
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, 8765, descr=tiddescr)
            setfield_gc(p0, 101, descr=blendescr)
            p1 = nursery_ptr_increment(p0, %(bdescr.basesize + 104)d)
            setfield_gc(p1, 0, descr=stmflagsdescr)
            setfield_gc(p1, 8765, descr=tiddescr)
            setfield_gc(p1, 102, descr=blendescr)
            p2 = call_malloc_nursery(    \
                              %(bdescr.basesize + 104)d)
            setfield_gc(p2, 0, descr=stmflagsdescr)
            setfield_gc(p2, 8765, descr=tiddescr)
            setfield_gc(p2, 103, descr=blendescr)
        """)

    def test_rewrite_assembler_huge_size(self):
        # "huge" is defined as "larger than 0xffffff bytes, or 16MB"
        self.check_rewrite("""
            []
            p0 = new_array(20000000, descr=bdescr)
            jump()
        """, """
            []
            p0 = call_malloc_gc(ConstClass(malloc_array), 1, \
                                %(bdescr.tid)d, 20000000,    \
                                descr=malloc_array_descr)

            jump()
        """)

    def test_new_with_vtable(self):
        self.check_rewrite("""
            []
            p0 = new_with_vtable(descr=o_descr)
        """, """
            [p1]
            p0 = call_malloc_nursery(104)      # rounded up
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, 9315, descr=tiddescr)
            setfield_gc(p0, ConstClass(o_vtable), descr=vtable_descr)
        """)

    def test_new_with_vtable_too_big(self):
        self.gc_ll_descr.max_size_of_young_obj = 100
        self.check_rewrite("""
            []
            p0 = new_with_vtable(descr=o_descr)
        """, """
            [p1]
            p0 = call_malloc_gc(ConstClass(malloc_big_fixedsize), 104, 9315, \
                                descr=malloc_big_fixedsize_descr)
            setfield_gc(p0, ConstClass(o_vtable), descr=vtable_descr)
        """)

    def test_rewrite_assembler_newstr_newunicode(self):
        self.check_rewrite("""
            [i2]
            p0 = newstr(14)
            p1 = newunicode(10)
            p2 = newunicode(i2)
            p3 = newstr(i2)
            jump()
        """, """
            [i2]
            p0 = call_malloc_nursery(                                \
                      %(strdescr.basesize + 16 * strdescr.itemsize + \
                        unicodedescr.basesize + 10 * unicodedescr.itemsize)d)
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, %(strdescr.tid)d, descr=tiddescr)
            setfield_gc(p0, 14, descr=strlendescr)
            setfield_gc(p0, 0, descr=strhashdescr)

            p1 = nursery_ptr_increment(p0, %(strdescr.basesize + 16 * strdescr.itemsize)d)
            setfield_gc(p1, 0, descr=stmflagsdescr)
            setfield_gc(p1, %(unicodedescr.tid)d, descr=tiddescr)
            setfield_gc(p1, 10, descr=unicodelendescr)
            setfield_gc(p1, 0, descr=unicodehashdescr)

            p2 = call_malloc_nursery_varsize(2, 4, i2, \
                                descr=unicodedescr)
            setfield_gc(p2, i2, descr=unicodelendescr)
            setfield_gc(p2, 0, descr=unicodehashdescr)

            p3 = call_malloc_nursery_varsize(1, 1, i2, \
                                descr=strdescr)
            setfield_gc(p3, i2, descr=strlendescr)
            setfield_gc(p3, 0, descr=strhashdescr)

            jump()
        """)

    def test_label_makes_size_unknown(self):
        self.check_rewrite("""
            [i2, p3]
            p1 = new_array_clear(5, descr=cdescr)
            label(p1, i2, p3)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
        """, """
            [i2, p3]
            p1 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p1, 0, descr=stmflagsdescr)
            setfield_gc(p1, 8111, descr=tiddescr)
            setfield_gc(p1, 5, descr=clendescr)
            zero_array(p1, 0, 5, descr=cdescr)
            label(p1, i2, p3)
            cond_call_gc_wb_array(p1, i2, descr=wbdescr)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
        """)

    def test_transaction_break_makes_size_unknown(self):
        class fakeextrainfo:
            def call_needs_inevitable(self):
                return False
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr2 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T,
                                    fakeextrainfo())

        self.gc_ll_descr.max_size_of_young_obj = 300
        self.check_rewrite("""
            [i0, f0]
            p0 = new_array(5, descr=bdescr)
            p1 = new_array(5, descr=bdescr)
            call_may_force_n(12345, descr=calldescr2)   # stm_transaction_break
            guard_not_forced() []
            p2 = new_array(5, descr=bdescr)
        """, """
            [i0, f0]
            p0 = call_malloc_nursery(    \
                              %(2 * (bdescr.basesize + 8))d)
            setfield_gc(p0, 0, descr=stmflagsdescr)
            setfield_gc(p0, 8765, descr=tiddescr)
            setfield_gc(p0, 5, descr=blendescr)
            p1 = nursery_ptr_increment(p0, %(bdescr.basesize + 8)d)
            setfield_gc(p1, 0, descr=stmflagsdescr)
            setfield_gc(p1, 8765, descr=tiddescr)
            setfield_gc(p1, 5, descr=blendescr)

            call_may_force_n(12345, descr=calldescr2)   # stm_transaction_break
            guard_not_forced() []

            p2 = call_malloc_nursery(    \
                              %(bdescr.basesize + 8)d)
            setfield_gc(p2, 0, descr=stmflagsdescr)
            setfield_gc(p2, 8765, descr=tiddescr)
            setfield_gc(p2, 5, descr=blendescr)
        """, calldescr2=calldescr2)


    def test_immutable_getfields(self):
        for imm_hint in [{}, {'immutable':True}]:
            S = lltype.GcStruct('S')
            U = lltype.GcStruct('U',
                ('x', lltype.Signed),
                ('y', lltype.Ptr(S)),
                hints=imm_hint)
            udescr = get_size_descr(self.gc_ll_descr, U)
            udescr.tid = 2123
            uxdescr = get_field_descr(self.gc_ll_descr, U, 'x')
            #uydescr = get_field_descr(self.gc_ll_descr, U, 'y')

            V = lltype.GcArray(('z', lltype.Ptr(S)), hints=imm_hint)
            vdescr = get_array_descr(self.gc_ll_descr, V)
            vdescr.tid = 1233
            #vzdescr = get_interiorfield_descr(self.gc_ll_descr, V, 'z')

            if imm_hint:
                d = {'comment': '#', 'pure': '_pure'}
            else:
                d = {'comment': '', 'pure': ''}

            self.check_rewrite("""
                [p1, p3, i1, p4]
                p2 = getfield_gc%(pure)s_r(p1, descr=uxdescr)
                i4 = getarrayitem_gc%(pure)s_i(p4, i1, descr=vdescr)
                jump(p2)
            """ % d, """
                [p1, p3, i1, p4]
                p2 = getfield_gc%(pure)s_r(p1, descr=uxdescr)
                %(comment)s stm_read(p1)
                i4 = getarrayitem_gc%(pure)s_i(p4, i1, descr=vdescr)
                %(comment)s stm_read(p4)
                $DUMMYALLOC
                jump(p2)
            """ % d, uxdescr=uxdescr, vdescr=vdescr)

    def test_stm_location_1(self):
        self.check_rewrite("""
            [p1, p2]
            setfield_gc(p1, p2, descr=tzdescr) {50}
        """, """
            [p1, p2]
            cond_call_gc_wb(p1, descr=wbdescr) {50}
            setfield_gc(p1, p2, descr=tzdescr) {50}
        """)

    def test_stm_location_2(self):
        self.check_rewrite("""
            [i1]
            i3 = getfield_raw_i(i1, descr=tydescr) {52}
        """, """
            [i1]
            $INEV {52}
            i3 = getfield_raw_i(i1, descr=tydescr) {52}
        """)

    def test_stm_location_3(self):
        self.check_rewrite("""
        [i0, f0]
        i2 = call_assembler_i(i0, f0, descr=casmdescr) {54}
        guard_not_forced() [] {55}
        """, """
        [i0, f0]
        i1 = getfield_raw_i(ConstClass(frame_info), descr=jfi_frame_depth) {54}
        p1 = call_malloc_nursery_varsize_frame(i1) {54}
        setfield_gc(p1, 0, descr=stmflagsdescr)
        setfield_gc(p1, 0, descr=tiddescr) {54}
        setfield_gc(p1, 0, descr=jf_extra_stack_depth)
        setfield_gc(p1, NULL, descr=jf_savedata)
        setfield_gc(p1, NULL, descr=jf_force_descr)
        setfield_gc(p1, NULL, descr=jf_descr)
        setfield_gc(p1, NULL, descr=jf_guard_exc)
        setfield_gc(p1, NULL, descr=jf_forward)
        setfield_gc(p1, i1, descr=framelendescr) {54}
        setfield_gc(p1, ConstClass(frame_info), descr=jf_frame_info) {54}
        setarrayitem_gc(p1, 0, i0, descr=signedframedescr) {54}
        setarrayitem_gc(p1, 1, f0, descr=floatframedescr) {54}
        i3 = call_assembler_i(p1, descr=casmdescr) {54}
        guard_not_forced() [] {55}
        """)

    def test_stm_location_4(self):
        self.check_rewrite("""
            [p1, i2, p3]
            debug_merge_point() {81}
            i3 = int_add(i2, 5)
            setarrayitem_gc(p1, i3, p3, descr=cdescr)
        """, """
            [p1, i2, p3]
            i3 = int_add(i2, 5) {81}
            cond_call_gc_wb_array(p1, i3, descr=wbdescr) {81}
            setarrayitem_gc(p1, i3, p3, descr=cdescr) {81}
        """)

    def test_stm_should_break_transaction_no_malloc(self):
        self.check_rewrite("""
        []
        i1 = stm_should_break_transaction()
        jump(i1)
        """, """
        []
        i1 = stm_should_break_transaction()
        $DUMMYALLOC
        jump(i1)
        """)

    def test_stm_should_break_transaction_with_malloc(self):
        self.check_rewrite("""
        []
        p2 = new(descr=tdescr)
        i1 = stm_should_break_transaction()
        jump(i1)
        """, """
        []
        p2 = call_malloc_nursery(%(tdescr.size)d)
        setfield_gc(p2, 0, descr=stmflagsdescr)
        setfield_gc(p2, %(tdescr.tid)d, descr=tiddescr)
        i1 = stm_should_break_transaction()
        zero_ptr_field(p2, %(tdescr.gc_fielddescrs[0].offset)s)
        jump(i1)
        """)

    def test_double_stm_should_break_allocation(self):
        self.check_rewrite("""
        []
        i1 = stm_should_break_transaction()
        i2 = stm_should_break_transaction()
        jump(i1, i2)
        """, """
        []
        i1 = stm_should_break_transaction()
        i2 = stm_should_break_transaction()
        $DUMMYALLOC
        jump(i1, i2)
        """)

    def test_label_stm_should_break_allocation(self):
        self.check_rewrite("""
        []
        p2 = new(descr=tdescr)
        label()
        i1 = stm_should_break_transaction()
        jump(i1)
        """, """
        []
        p2 = call_malloc_nursery(%(tdescr.size)d)
        setfield_gc(p2, 0, descr=stmflagsdescr)
        setfield_gc(p2, %(tdescr.tid)d, descr=tiddescr)
        zero_ptr_field(p2, %(tdescr.gc_fielddescrs[0].offset)s)
        label()
        i1 = stm_should_break_transaction()
        $DUMMYALLOC
        jump(i1)
        """)

    def test_dummy_alloc_is_before_guard_not_forced_2(self):
        self.check_rewrite("""
        []
        escape_n()
        guard_not_forced_2() []
        finish()
        """, """
        []
        $INEV
        escape_n()
        $DUMMYALLOC
        guard_not_forced_2() []
        finish()
        """)

    def test_zero_before_maymalloc(self):
        self.check_rewrite("""
        []
        p2 = new(descr=tdescr)
        escape_n()
        """, """
        []
        p2 = call_malloc_nursery(%(tdescr.size)d)
        setfield_gc(p2, 0, descr=stmflagsdescr)
        setfield_gc(p2, %(tdescr.tid)d, descr=tiddescr)
        zero_ptr_field(p2, %(tdescr.gc_fielddescrs[0].offset)s)
        $INEV
        escape_n()
        """)
