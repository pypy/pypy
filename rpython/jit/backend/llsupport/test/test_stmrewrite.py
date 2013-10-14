from rpython.jit.backend.llsupport.descr import *
from rpython.jit.backend.llsupport.gc import *
from rpython.jit.metainterp.gc import get_description
from rpython.jit.metainterp import resoperation
from rpython.jit.backend.llsupport.test.test_rewrite import (
    RewriteTests, BaseFakeCPU)
from rpython.rtyper.lltypesystem import lltype, rclass, rffi, llmemory


def test_all_operations_with_gc_in_their_name():
    # hack, but will fail if we add a new ResOperation called .._GC_..
    import os, re
    r_gc = re.compile(r"(^|_)GC(_|$)")
    with open(os.path.join(os.path.dirname(
          os.path.dirname(os.path.abspath(__file__))), 'stmrewrite.py')) as f:
        source = f.read()
        words = re.split("\W", source)
    # extra op names with GC in their name but where it's ok if stmrewrite
    # doesn't mention them:
    words.append('CALL_MALLOC_GC')
    words.append('COND_CALL_GC_WB')
    words.append('COND_CALL_GC_WB_ARRAY')
    #
    words = set(words)
    missing = []
    for name in sorted(resoperation.opname.values()):
        if r_gc.search(name):
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
        #
        class FakeCPU(BaseFakeCPU):
            def sizeof(self, STRUCT):
                descr = SizeDescrWithVTable(104)
                descr.tid = 9315
                return descr

        self.cpu = FakeCPU()

    def check_rewrite(self, frm_operations, to_operations, **namespace):
        inev = ("call(ConstClass(stm_try_inevitable),"
                " descr=stm_try_inevitable_descr)")
        frm_operations = frm_operations.replace('$INEV', inev)
        to_operations  = to_operations .replace('$INEV', inev)
        for name, value in self.gc_ll_descr.__dict__.items():
            if name.endswith('descr') and name[1] == '2' and len(name) == 8:
                namespace[name] = value     # "X2Ydescr"
        RewriteTests.check_rewrite(self, frm_operations, to_operations,
                                   **namespace)

    def test_inevitable_calls(self):
        c1 = GcCache(True)
        T = lltype.GcStruct('T')
        U = lltype.GcStruct('U', ('x', lltype.Signed))
        for inev in (True, False):
            class fakeextrainfo:
                def call_needs_inevitable(self):
                    return inev
        
            calldescr = get_call_descr(c1, [lltype.Ptr(T)], lltype.Ptr(U), 
                                       fakeextrainfo())
            
            self.check_rewrite("""
                []
                call(123, descr=cd)
                jump()
            ""","""
                []
                %s
                call(123, descr=cd)
                stm_transaction_break()
                jump()
            """ % ("$INEV" if inev else "",), cd=calldescr)
    
    def test_rewrite_one_setfield_gc(self):
        self.check_rewrite("""
            [p1, p2]
            setfield_gc(p1, p2, descr=tzdescr)
            jump()
        """, """
            [p1, p2]
            cond_call_stm_b(p1, descr=P2Wdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            stm_transaction_break()
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
            p3 = same_as(ConstPtr(t))
            cond_call_stm_b(p3, descr=P2Wdescr)
            setfield_gc(p3, p2, descr=tzdescr)
            stm_transaction_break()
            jump()
            """, t=NULL)

    def test_invalidate_read_status_after_write_to_constptr(self):
        TP = lltype.GcArray(lltype.Signed)
        NULL = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(TP))
        self.check_rewrite("""
            [p0]
            p1 = same_as(ConstPtr(t))
            p2 = same_as(ConstPtr(t))
            p3 = getfield_gc(p1, descr=tzdescr)
            setfield_gc(p2, p0, descr=tzdescr)
            p4 = getfield_gc(p1, descr=tzdescr)
            jump()
        """, """
            [p0]
            p1 = same_as(ConstPtr(t))
            p2 = same_as(ConstPtr(t))
            cond_call_stm_b(p1, descr=P2Rdescr)
            p3 = getfield_gc(p1, descr=tzdescr)
            cond_call_stm_b(p2, descr=P2Wdescr)
            setfield_gc(p2, p0, descr=tzdescr)
            cond_call_stm_b(p1, descr=P2Rdescr)
            p4 = getfield_gc(p1, descr=tzdescr)
            stm_transaction_break()
            jump()
            """, t=NULL)

    def test_invalidate_read_status_after_write(self):
        self.check_rewrite("""
            [p0]
            p1 = same_as(p0)
            p2 = same_as(p0)
            p4 = getfield_gc(p1, descr=tzdescr)
            setfield_gc(p2, p0, descr=tzdescr)
            p5 = getfield_gc(p1, descr=tzdescr)
            jump()
        """, """
            [p0]
            p1 = same_as(p0)
            p2 = same_as(p0)
            cond_call_stm_b(p1, descr=P2Rdescr)
            p4 = getfield_gc(p1, descr=tzdescr)
            cond_call_stm_b(p2, descr=P2Wdescr)
            setfield_gc(p2, p0, descr=tzdescr)
            cond_call_stm_b(p1, descr=P2Rdescr)
            p5 = getfield_gc(p1, descr=tzdescr)
            stm_transaction_break()
            jump()
        """)

    def test_invalidate_read_status_after_write_to_field(self):
        self.check_rewrite("""
            [p0]
            p1 = getfield_gc(p0, descr=tzdescr)
            p2 = getfield_gc(p0, descr=tzdescr)
            p3 = getfield_gc(p1, descr=tzdescr)
            setfield_gc(p2, p0, descr=tzdescr)
            p4 = getfield_gc(p1, descr=tzdescr)
            jump()
        """, """
            [p0]
            cond_call_stm_b(p0, descr=P2Rdescr)
            p1 = getfield_gc(p0, descr=tzdescr)
            p2 = getfield_gc(p0, descr=tzdescr)
            cond_call_stm_b(p1, descr=P2Rdescr)
            p3 = getfield_gc(p1, descr=tzdescr)
            cond_call_stm_b(p2, descr=P2Wdescr)
            setfield_gc(p2, p0, descr=tzdescr)
            cond_call_stm_b(p1, descr=P2Rdescr)
            p4 = getfield_gc(p1, descr=tzdescr)
            stm_transaction_break()
            jump()
        """)

    def test_invalidate_read_status_after_write_array_interior(self):
        ops = ['getarrayitem_gc', 'getinteriorfield_gc']
        original = """
            [p0, i1, i2]
            p1 = %s(p0, i1, descr=adescr)
            p2 = %s(p0, i2, descr=adescr)
            p3 = getfield_gc(p1, descr=tzdescr)
            setfield_gc(p2, p0, descr=tzdescr)
            p4 = getfield_gc(p1, descr=tzdescr)
            jump()
        """
        rewritten = """
            [p0, i1, i2]
            cond_call_stm_b(p0, descr=P2Rdescr)
            p1 = %s(p0, i1, descr=adescr)
            p2 = %s(p0, i2, descr=adescr)
            cond_call_stm_b(p1, descr=P2Rdescr)
            p3 = getfield_gc(p1, descr=tzdescr)
            cond_call_stm_b(p2, descr=P2Wdescr)
            setfield_gc(p2, p0, descr=tzdescr)
            cond_call_stm_b(p1, descr=P2Rdescr)
            p4 = getfield_gc(p1, descr=tzdescr)
            stm_transaction_break()
            jump()
        """
        for op in ops:
            self.check_rewrite(original % (op, op), 
                               rewritten % (op, op))

    def test_rewrite_write_barrier_after_malloc(self):
        self.check_rewrite("""
            [p1, p3]
            setfield_gc(p3, p1, descr=tzdescr)
            p2 = new(descr=tdescr)
            setfield_gc(p3, p1, descr=tzdescr)
            jump(p2)
        """, """
            [p1, p3]
            cond_call_stm_b(p3, descr=P2Wdescr)
            setfield_gc(p3, p1, descr=tzdescr)
            p2 = call_malloc_gc(ConstClass(malloc_big_fixedsize),    \
                                %(tdescr.size)d, %(tdescr.tid)d, \
                                descr=malloc_big_fixedsize_descr)
            cond_call_stm_b(p3, descr=P2Wdescr)
            setfield_gc(p3, p1, descr=tzdescr)
            stm_transaction_break()
            jump(p2)
        """)

    def test_rewrite_read_barrier_after_malloc(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            p3 = new(descr=tdescr)
            p4 = getfield_gc(p1, descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            cond_call_stm_b(p1, descr=P2Rdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            p3 = call_malloc_gc(ConstClass(malloc_big_fixedsize),    \
                                %(tdescr.size)d, %(tdescr.tid)d, \
                                descr=malloc_big_fixedsize_descr)
            p4 = getfield_gc(p1, descr=tzdescr)
            stm_transaction_break()
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
            p2 = call_malloc_gc(ConstClass(malloc_big_fixedsize),    \
                                %(tdescr.size)d, %(tdescr.tid)d, \
                                descr=malloc_big_fixedsize_descr)
            setfield_gc(p2, p1, descr=tzdescr)
            stm_transaction_break()
            jump(p2)
        """)

    def test_rewrite_unrelated_setfield_gcs(self):
        self.check_rewrite("""
            [p1, p2, p3, p4]
            setfield_gc(p1, p2, descr=tzdescr)
            setfield_gc(p3, p4, descr=tzdescr)
            jump()
        """, """
            [p1, p2, p3, p4]
            cond_call_stm_b(p1, descr=P2Wdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            cond_call_stm_b(p3, descr=P2Wdescr)
            setfield_gc(p3, p4, descr=tzdescr)
            stm_transaction_break()
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
            cond_call_stm_b(p1, descr=P2Wdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            setfield_gc(p1, i3, descr=tydescr)
            stm_transaction_break()
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
            cond_call_stm_b(p1, descr=P2Wdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            label(p1, i3)
            cond_call_stm_b(p1, descr=P2Wdescr)
            setfield_gc(p1, i3, descr=tydescr)
            stm_transaction_break()
            jump(p1)
        """)

    def test_remove_debug_merge_point(self):
        self.check_rewrite("""
            [i1, i2]
            debug_merge_point(i1, i2)
            jump()
        """, """
            [i1, i2]
            stm_transaction_break()
            jump()
        """)

    def test_ignore_some_operations(self):
        oplist = [
            "guard_true(i1) [i2]",    # all guards
            "i3 = int_add(i1, i2)",   # all pure operations
            "f3 = float_abs(f1)",
            "i3 = force_token()",
            "i3 = read_timestamp()",
            "i3 = mark_opaque_ptr(p1)",
            "jit_debug(i1, i2)",
            "keepalive(i1)",
            "i3 = int_sub_ovf(i1, i2)",   # is_ovf operations
            ]
        for op in oplist:       
            testcase = """
                [i1, i2, p1, p2, f1]
                %s
                finish()
            """ % op
            self.check_rewrite(testcase, testcase)

    def test_rewrite_getfield_gc(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            cond_call_stm_b(p1, descr=P2Rdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            stm_transaction_break()
            jump(p2)
        """)

    def test_rewrite_getfield_gc_const(self):
        TP = lltype.GcArray(lltype.Signed)
        NULL = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(TP))
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(ConstPtr(t), descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            p3 = same_as(ConstPtr(t))
            cond_call_stm_b(p3, descr=P2Rdescr)
            p2 = getfield_gc(p3, descr=tzdescr)
            stm_transaction_break()
            jump(p2)
        """, t=NULL)
        # XXX could do better: G2Rdescr

    def test_rewrite_getarrayitem_gc(self):
        self.check_rewrite("""
            [p1, i2]
            i3 = getarrayitem_gc(p1, i2, descr=adescr)
            jump(i3)
        """, """
            [p1, i2]
            cond_call_stm_b(p1, descr=P2Rdescr)
            i3 = getarrayitem_gc(p1, i2, descr=adescr)
            stm_transaction_break()
            jump(i3)
        """)

    def test_rewrite_getinteriorfield_gc(self):
        self.check_rewrite("""
            [p1, i2]
            i3 = getinteriorfield_gc(p1, i2, descr=adescr)
            jump(i3)
        """, """
            [p1, i2]
            cond_call_stm_b(p1, descr=P2Rdescr)
            i3 = getinteriorfield_gc(p1, i2, descr=adescr)
            stm_transaction_break()
            jump(i3)
        """)

    def test_rewrite_several_getfield_gcs(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            i2 = getfield_gc(p1, descr=tydescr)
            jump(p2, i2)
        """, """
            [p1]
            cond_call_stm_b(p1, descr=P2Rdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            i2 = getfield_gc(p1, descr=tydescr)
            stm_transaction_break()
            jump(p2, i2)
        """)

    def test_rewrite_unrelated_getfield_gcs(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            i2 = getfield_gc(p2, descr=tydescr)
            jump(p2, i2)
        """, """
            [p1]
            cond_call_stm_b(p1, descr=P2Rdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            cond_call_stm_b(p2, descr=P2Rdescr)
            i2 = getfield_gc(p2, descr=tydescr)
            stm_transaction_break()
            jump(p2, i2)
        """)

    def test_getfield_followed_by_setfield(self):
        # XXX coalesce the two barriers into one if there are e.g. no
        # calls inbetween
        self.check_rewrite("""
            [p1]
            i1 = getfield_gc(p1, descr=tydescr)
            i2 = int_add(i1, 1)
            setfield_gc(p1, i2, descr=tydescr)
            jump(p1)
        """, """
            [p1]
            cond_call_stm_b(p1, descr=P2Rdescr)
            i1 = getfield_gc(p1, descr=tydescr)
            i2 = int_add(i1, 1)
            cond_call_stm_b(p1, descr=P2Wdescr)
            setfield_gc(p1, i2, descr=tydescr)
            stm_transaction_break()
            jump(p1)
        """)

    def test_setfield_followed_by_getfield(self):
        self.check_rewrite("""
            [p1]
            setfield_gc(p1, 123, descr=tydescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            cond_call_stm_b(p1, descr=P2Wdescr)
            setfield_gc(p1, 123, descr=tydescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            stm_transaction_break()
            jump(p2)
        """)

    def test_rewrite_getfield_gc_on_local_2(self):
        self.check_rewrite("""
            [p0]
            p1 = new(descr=tdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            jump(p2)
        """, """
            [p0]
            p1 = call_malloc_gc(ConstClass(malloc_big_fixedsize),    \
                                %(tdescr.size)d, %(tdescr.tid)d, \
                                descr=malloc_big_fixedsize_descr)
            p2 = getfield_gc(p1, descr=tzdescr)
            stm_transaction_break()
            jump(p2)
        """)

    def test_rewrite_getfield_gc_on_future_local_after_call(self):
        # XXX could detect CALLs that cannot interrupt the transaction
        # and/or could use the L category
        class fakeextrainfo:
            def call_needs_inevitable(self):
                return False
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr1 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T,
                                    fakeextrainfo())
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            call(p2, descr=calldescr1)
            setfield_gc(p1, 5, descr=tydescr)
            jump(p2)
        """, """
            [p1]
            cond_call_stm_b(p1, descr=P2Rdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            call(p2, descr=calldescr1)
            cond_call_stm_b(p1, descr=P2Wdescr)
            setfield_gc(p1, 5, descr=tydescr)
            stm_transaction_break()
            jump(p2)
        """, calldescr1=calldescr1)

    def test_getfield_raw(self):
        self.check_rewrite("""
            [i1, i2]
            i3 = getfield_raw(i1, descr=tydescr)
            keepalive(i3)
            i4 = getfield_raw(i2, descr=tydescr)
            jump(i3, i4)
        """, """
            [i1, i2]
            $INEV
            i3 = getfield_raw(i1, descr=tydescr)
            keepalive(i3)
            i4 = getfield_raw(i2, descr=tydescr)
            stm_transaction_break()
            jump(i3, i4)
        """)

    def test_getfield_raw_stm_dont_track_raw_accesses(self):
        c1 = GcCache(True)
        F = lltype.Struct('F', ('x', lltype.Signed),
                          hints={'stm_dont_track_raw_accesses': True})
        fdescr = get_field_descr(c1, F, 'x')
        self.check_rewrite("""
            [i1]
            i2 = getfield_raw(i1, descr=fdescr)
            jump(i2)
        """, """
            [i1]
            i2 = getfield_raw(i1, descr=fdescr)
            stm_transaction_break()
            jump(i2)
        """, fdescr=fdescr)

    def test_getfield_raw_over_label(self):
        self.check_rewrite("""
            [i1, i2]
            i3 = getfield_raw(i1, descr=tydescr)
            label(i1, i2, i3)
            i4 = getfield_raw(i2, descr=tydescr)
            jump(i3, i4)
        """, """
            [i1, i2]
            $INEV
            i3 = getfield_raw(i1, descr=tydescr)
            label(i1, i2, i3)
            $INEV
            i4 = getfield_raw(i2, descr=tydescr)
            stm_transaction_break()
            jump(i3, i4)
        """)

    def test_getarrayitem_raw(self):
        self.check_rewrite("""
            [i1, i2]
            i3 = getarrayitem_raw(i1, 5, descr=adescr)
            i4 = getarrayitem_raw(i2, i3, descr=adescr)
            jump(i3, i4)
        """, """
            [i1, i2]
            $INEV
            i3 = getarrayitem_raw(i1, 5, descr=adescr)
            i4 = getarrayitem_raw(i2, i3, descr=adescr)
            stm_transaction_break()
            jump(i3, i4)
        """)

    def test_rewrite_unrelated_setarrayitem_gcs(self):
        self.check_rewrite("""
            [p1, i1, p2, p3, i3, p4]
            setarrayitem_gc(p1, i1, p2, descr=adescr)
            setarrayitem_gc(p3, i3, p4, descr=adescr)
            jump()
        """, """
            [p1, i1, p2, p3, i3, p4]
            cond_call_stm_b(p1, descr=P2Wdescr)
            setarrayitem_gc(p1, i1, p2, descr=adescr)
            cond_call_stm_b(p3, descr=P2Wdescr)
            setarrayitem_gc(p3, i3, p4, descr=adescr)
            stm_transaction_break()
            jump()
        """)

    def test_rewrite_several_setarrayitem_gcs(self):
        self.check_rewrite("""
            [p1, p2, i2, p3, i3]
            setarrayitem_gc(p1, i2, p2, descr=adescr)
            i4 = read_timestamp()
            setarrayitem_gc(p1, i3, p3, descr=adescr)
            jump()
        """, """
            [p1, p2, i2, p3, i3]
            cond_call_stm_b(p1, descr=P2Wdescr)
            setarrayitem_gc(p1, i2, p2, descr=adescr)
            i4 = read_timestamp()
            setarrayitem_gc(p1, i3, p3, descr=adescr)
            stm_transaction_break()
            jump()
        """)

    def test_rewrite_several_setinteriorfield_gc(self):
        self.check_rewrite("""
            [p1, p2, i2, p3, i3]
            setinteriorfield_gc(p1, i2, p2, descr=adescr)
            i4 = read_timestamp()
            setinteriorfield_gc(p1, i3, p3, descr=adescr)
            jump()
        """, """
            [p1, p2, i2, p3, i3]
            cond_call_stm_b(p1, descr=P2Wdescr)
            setinteriorfield_gc(p1, i2, p2, descr=adescr)
            i4 = read_timestamp()
            setinteriorfield_gc(p1, i3, p3, descr=adescr)
            stm_transaction_break()
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
            cond_call_stm_b(p1, descr=P2Wdescr)
            strsetitem(p1, i2, i3)
            unicodesetitem(p1, i2, i3)
            stm_transaction_break()
            jump()
        """)
        py.test.skip("XXX not really right: should instead be an assert "
                     "that p1 is already a W")

    def test_call_release_gil(self):
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr2 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T)
        self.check_rewrite("""
            [i1, i2, i3, p7]
            setfield_gc(p7, 10, descr=tydescr)
            call_release_gil(123, descr=calldescr2)
            guard_not_forced() []
            setfield_gc(p7, 20, descr=tydescr)
            jump(i2, p7)
        """, """
            [i1, i2, i3, p7]
            cond_call_stm_b(p7, descr=P2Wdescr)
            setfield_gc(p7, 10, descr=tydescr)
            call_release_gil(123, descr=calldescr2)
            guard_not_forced() []
            stm_transaction_break()
            cond_call_stm_b(p7, descr=P2Wdescr)
            setfield_gc(p7, 20, descr=tydescr)
            stm_transaction_break()
            jump(i2, p7)
        """, calldescr2=calldescr2)
        
    def test_fallback_to_inevitable(self):
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr2 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T)
        oplist = [
            "setfield_raw(i1, i2, descr=tydescr)",
            "setarrayitem_raw(i1, i2, i3, descr=tydescr)",
            "setinteriorfield_raw(i1, i2, i3, descr=adescr)",
            "escape(i1)",    # a generic unknown operation
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
                cond_call_stm_b(p7, descr=P2Wdescr)
                setfield_gc(p7, 10, descr=tydescr)
                $INEV
                %s
                cond_call_stm_b(p7, descr=P2Wdescr)
                setfield_gc(p7, 20, descr=tydescr)
                stm_transaction_break()
                jump(i2, p7)
            """ % op, calldescr2=calldescr2)

    def test_copystrcontent(self):
        self.check_rewrite("""
            [p1, p2, i1, i2, i3]
            copystrcontent(p1, p2, i1, i2, i3)
            jump()
        """, """
            [p1, p2, i1, i2, i3]
            cond_call_stm_b(p2, descr=P2Wdescr)
            cond_call_stm_b(p1, descr=P2Rdescr)
            copystrcontent(p1, p2, i1, i2, i3)
            stm_transaction_break()
            jump()
        """)

    def test_call_dont_force(self):
        py.test.skip("optimization")
        for op in ["call(123, descr=calldescr1)",
                   "call_may_force(123, descr=calldescr1)",
                   "call_loopinvariant(123, descr=calldescr1)",
                   ]:
            self.check_rewrite("""
                [p1]
                setfield_gc(p1, 10, descr=tydescr)
                %s
                setfield_gc(p1, 20, descr=tydescr)
                jump(p1)
            """ % op, """
                [p1]
                cond_call_stm_b(p1, descr=P2Wdescr)
                setfield_gc(p1, 10, descr=tydescr)
                %s
                setfield_gc(p1, 20, descr=tydescr)
                stm_transaction_break()
                jump(p1)
            """ % op)

    def test_call_force(self):
        class fakeextrainfo:
            def call_needs_inevitable(self):
                return False
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr2 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T,
                                    fakeextrainfo())
        for op, guarded in [
                ("call(123, descr=calldescr2)", False),
                ("call_assembler(123, descr=casmdescr)", True),
                ("call_may_force(123, descr=calldescr2)", True),
                ("call_loopinvariant(123, descr=calldescr2)", False),
                ]:
            guard = "guard_not_forced() []" if guarded else ""
            tr_break = "stm_transaction_break()" if guarded else ""
            self.check_rewrite("""
                [p1]
                setfield_gc(p1, 10, descr=tydescr)
                %s
                %s
                setfield_gc(p1, 20, descr=tydescr)
                jump(p1)
            """ % (op, guard), """
                [p1]
                cond_call_stm_b(p1, descr=P2Wdescr)
                setfield_gc(p1, 10, descr=tydescr)
                %s
                %s
                %s
                cond_call_stm_b(p1, descr=P2Wdescr)
                setfield_gc(p1, 20, descr=tydescr)
                stm_transaction_break()
                jump(p1)
            """ % (op, guard, tr_break), calldescr2=calldescr2)

    def test_ptr_eq_null(self):
        self.check_rewrite("""
            [p1, p2]
            i1 = ptr_eq(p1, NULL)
            jump(i1)
        """, """
            [p1, p2]
            i1 = ptr_eq(p1, NULL)
            stm_transaction_break()
            jump(i1)
        """)

    def test_ptr_eq(self):
        self.check_rewrite("""
            [p1, p2]
            i1 = ptr_eq(p1, p2)
            jump(i1)
        """, """
            [p1, p2]
            i1 = ptr_eq(p1, p2)
            stm_transaction_break()
            jump(i1)
        """)

    def test_instance_ptr_eq(self):
        self.check_rewrite("""
            [p1, p2]
            i1 = instance_ptr_eq(p1, p2)
            jump(i1)
        """, """
            [p1, p2]
            i1 = instance_ptr_eq(p1, p2)
            stm_transaction_break()
            jump(i1)
        """)

    def test_ptr_ne(self):
        self.check_rewrite("""
            [p1, p2]
            i1 = ptr_ne(p1, p2)
            jump(i1)
        """, """
            [p1, p2]
            i1 = ptr_ne(p1, p2)
            stm_transaction_break()
            jump(i1)
        """)

    def test_instance_ptr_ne(self):
        self.check_rewrite("""
            [p1, p2]
            i1 = instance_ptr_ne(p1, p2)
            jump(i1)
        """, """
            [p1, p2]
            i1 = instance_ptr_ne(p1, p2)
            stm_transaction_break()
            jump(i1)
        """)

    def test_ptr_eq_other_direct_cases(self):
        py.test.skip("can also keep ptr_eq if both args are L or W, "
                     "or if one arg is freshly malloced")
