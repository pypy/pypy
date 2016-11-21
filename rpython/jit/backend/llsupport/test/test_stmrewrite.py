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
    words += ['GC_LOAD_F', 'GC_LOAD_I', 'GC_LOAD_INDEXED_F', 'GC_LOAD_INDEXED_I',
              'GC_LOAD_INDEXED_R', 'GC_LOAD_R', 'GC_STORE', 'GC_STORE_INDEXED']
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
    words.append('ESCAPE_F')
    words.append('ESCAPE_I')
    words.append('ESCAPE_R')
    words.append('ESCAPE_N')
    words.append('FORCE_SPILL')
    words.append('VEC_LOAD_F')
    words.append('VEC_LOAD_I')
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
        header_init = r"""
            gc_store(\1, %(stmflagsdescr.offset)s, 0, %(stmflagsdescr.field_size)s)
            gc_store(\1, 0,  %(\2.tid)d, %(tiddescr.field_size)s)
        """
        import re
        p = re.compile(r"\$INIT\((p\d+),\s*(\w+)\)")
        to_operations = p.sub(header_init, to_operations)
        frm_operations = frm_operations.replace('$INEV', inev)
        frm_operations = frm_operations.replace('$HCS', hcs)
        to_operations  = to_operations .replace('$INEV', inev)
        to_operations  = to_operations .replace('$HCS', hcs)
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
                call_shortcut = None
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
            gc_store(p1, %(tzdescr.offset)s, p2, %(tzdescr.field_size)s)
            #gc_store(p1, %(tzdescr.offset)s,  p2, %(tzdescr.field_size)s)
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
            gc_store(p1, %(tzdescr.offset)s,  i2, %(tzdescr.field_size)s)
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
            gc_store(ConstPtr(t), %(tzdescr.offset)s,  p2, %(tzdescr.field_size)s)
            jump()
            """, t=NULL)

    def test_rewrite_one_getfield_gc(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc_r(p1, descr=tzdescr)
            jump()
        """, """
            [p1]
            stm_read(p1)
            p2 = gc_load_r(p1, %(tzdescr.offset)s, %(tzdescr.field_size)s)
            #p2 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
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
            stm_read(p1)
            p3 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
            p4 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
            stm_read(p2)
            p5 = gc_load_r(p2,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
            p6 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
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
            gc_store(p1, 0,  i2, %(tydescr.field_size)s)
            p3 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
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
            stm_read(p1)
            p3 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
            cond_call_gc_wb(p2, descr=wbdescr)
            gc_store(p2, %(tzdescr.offset)s,  p0, %(tzdescr.field_size)s)
            p4 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
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
            gc_store(p3, %(tzdescr.offset)s,  p1, %(tzdescr.field_size)s)
            p2 = call_malloc_nursery(%(tdescr.size)d)
            $INIT(p2,tdescr)
            cond_call_gc_wb(p3, descr=wbdescr)
            gc_store(p3, %(tzdescr.offset)s,  p1, %(tzdescr.field_size)s)
            gc_store(p2, %(tdescr.gc_fielddescrs[0].offset)s, 0, %(tdescr.gc_fielddescrs[0].field_size)s)
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
            stm_read(p1)
            p2 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
            p3 = call_malloc_nursery(%(tdescr.size)d)
            $INIT(p3,tdescr)
            gc_store(p3, %(tdescr.gc_fielddescrs[0].offset)s, 0, %(tdescr.gc_fielddescrs[0].field_size)s)
            p4 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
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
            $INIT(p2,tdescr)
            gc_store(p2, %(tzdescr.offset)s,  p1, %(tzdescr.field_size)s)
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
            $INIT(p2,tdescr)
            gc_store(p2, %(tdescr.gc_fielddescrs[0].offset)s, 0, %(tdescr.gc_fielddescrs[0].field_size)s)
            p1 = gc_load_r(p2,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
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
            gc_store(p1, %(tzdescr.offset)s,  p2, %(tzdescr.field_size)s)
            cond_call_gc_wb(p3, descr=wbdescr)
            gc_store(p3, %(tzdescr.offset)s,  p4, %(tzdescr.field_size)s)
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
            gc_store(p1, %(tzdescr.offset)s,  p2, %(tzdescr.field_size)s)
            gc_store(p1, 0,  i3, %(tydescr.field_size)s)
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
            gc_store(p1, %(tzdescr.offset)s,  p2, %(tzdescr.field_size)s)
            label(p1, i3)
            cond_call_gc_wb(p1, descr=wbdescr)
            gc_store(p1, 0,  i3, %(tydescr.field_size)s)
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
                finish()
            """ % op

    def test_rewrite_getfield_gc_const(self):
        TP = lltype.GcArray(lltype.Signed)
        NULL = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(TP))
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc_r(ConstPtr(t), descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            stm_read(ConstPtr(t))
            p2 = gc_load_r(ConstPtr(t),  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
            jump(p2)
        """, t=NULL)

    def test_rewrite_getarrayitem_gc(self):
        self.check_rewrite("""
            [p1, i2]
            i3 = getarrayitem_gc_i(p1, i2, descr=adescr)
            jump(i3)
        """, """
            [p1, i2]
            stm_read(p1)
            i3 = gc_load_indexed_i(p1, i2, %(adescr.itemsize)s, %(adescr.basesize)s, -%(adescr.itemsize)s)
            jump(i3)
        """)

    def test_rewrite_getinteriorfield_gc(self):
        self.check_rewrite("""
            [p1, i2]
            i3 = getinteriorfield_gc_i(p1, i2, descr=intzdescr)
            jump(i3)
        """, """
            [p1, i2]
            stm_read(p1)
            i3 = gc_load_indexed_i(p1,i2,%(itxdescr.fielddescr.field_size)d,%(itxdescr.arraydescr.basesize + itxdescr.fielddescr.offset)d,%(itxdescr.fielddescr.field_size)d)
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
            stm_read(p1)
            p2 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
            stm_read(p2)
            i2 = gc_load_i(p2, 0, -%(tydescr.field_size)s)
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
            stm_read(p1)
            i1 = gc_load_i(p1, 0, -%(tydescr.field_size)s)
            i2 = int_add(i1, 1)
            cond_call_gc_wb(p1, descr=wbdescr)
            gc_store(p1, 0,  i2, %(tydescr.field_size)s)
            jump(p1)
        """)

    def test_rewrite_getfield_gc_on_future_local_after_call(self):
        # XXX could detect CALLs that cannot interrupt the transaction
        # and/or could use the L category
        class fakeextrainfo:
            oopspecindex = 0
            call_shortcut = None
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
            stm_read(p1)
            p2 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
            call_n(p2, descr=calldescr1)
            cond_call_gc_wb(p1, descr=wbdescr)
            gc_store(p1, 0, 5, %(tydescr.field_size)s)
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
            i3 = gc_load_i(i1, 0, -%(tydescr.field_size)s)
            keepalive(i3)
            i4 = gc_load_i(i2, 0, -%(tydescr.field_size)s)
            jump(i3, i4)
        """)

    def test_getfield_raw_stm_dont_track_raw_accesses(self):
        c1 = GcCache(False)
        F = lltype.Struct('F', ('x', lltype.Signed),
                          hints={'stm_dont_track_raw_accesses': True})
        fadescr = get_field_descr(c1, F, 'x')
        self.check_rewrite("""
            [i1]
            i2 = getfield_raw_i(i1, descr=fadescr)
            jump(i2)
        """, """
            [i1]
            i2 = gc_load_i(i1, 0, -%(fasize)d)
            jump(i2)
        """, fadescr=fadescr, fasize=fadescr.field_size)

    def test_setfield_raw_stm_dont_track_raw_accesses(self):
        c1 = GcCache(False)
        F = lltype.Struct('F', ('x', lltype.Signed),
                          hints={'stm_dont_track_raw_accesses': True})
        fadescr = get_field_descr(c1, F, 'x')
        self.check_rewrite("""
            [i1]
            setfield_raw(i1, 42, descr=fadescr)
            jump(i1)
        """, """
            [i1]
            gc_store(i1, 0, 42, %(fadescr.field_size)s)
            jump(i1)
        """, fadescr=fadescr)

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
            i2 = gc_load_i(i1, %(aadescr.basesize+5*aadescr.itemsize)s, -%(aadescr.itemsize)s)
            #i2 = gc_load_indexed_i(i1, 5, %(aadescr.itemsize)s, %(aadescr.basesize)s, -%(aadescr.itemsize)s)
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
            %(setarrayitem('i1', 5, 42, aadescr))s
            #gc_store_indexed(i1, 5, 42, %(aadescr.itemsize)s, %(aadescr.basesize)s, %(aadescr.itemsize)s)
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
            i3 = gc_load_i(i1, 0, -%(tydescr.field_size)d)
            label(i1, i2, i3)
            $INEV
            i4 = gc_load_i(i2, 0, -%(tydescr.field_size)d)
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
            i3 = gc_load_i(i1, %(adescr.basesize+5*adescr.itemsize)s, -%(adescr.itemsize)s)
            #i3 = gc_load_indexed_i(i1, 5, %(adescr.itemsize)s, %(adescr.basesize)s, -%(adescr.itemsize)s)
            i4 = gc_load_indexed_i(i2, i3, %(adescr.itemsize)s, %(adescr.basesize)s, -%(adescr.itemsize)s)
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
            gc_store_indexed(p1, i1, p2, %(adescr.itemsize)s, %(adescr.basesize)s, %(adescr.itemsize)s)
            cond_call_gc_wb_array(p3, i3, descr=wbdescr)
            gc_store_indexed(p3, i3, p4, %(adescr.itemsize)s, %(adescr.basesize)s, %(adescr.itemsize)s)
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
            gc_store_indexed(p1, i2, p2, %(adescr.itemsize)s, %(adescr.basesize)s, %(adescr.itemsize)s)
            i4 = force_token()
            cond_call_gc_wb_array(p1, i3, descr=wbdescr)
            gc_store_indexed(p1, i3, p3, %(adescr.itemsize)s, %(adescr.basesize)s, %(adescr.itemsize)s)
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
            gc_store_indexed(p1,i2,p2,%(intzdescr.fielddescr.field_size)d,%(intzdescr.arraydescr.basesize+intzdescr.fielddescr.offset)d,%(intzdescr.fielddescr.field_size)d)
            i4 = force_token()
            cond_call_gc_wb_array(p1, i3, descr=wbdescr)
            gc_store_indexed(p1,i3,p3,%(intzdescr.fielddescr.field_size)d,%(intzdescr.arraydescr.basesize+intzdescr.fielddescr.offset)d,%(intzdescr.fielddescr.field_size)d)
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
            gc_store_indexed(p1,i2,i3,1,%(strdescr.basesize-1)d,1)
            gc_store_indexed(p1,i2,i3,%(unicodedescr.itemsize)d,%(unicodedescr.basesize)d,%(unicodedescr.itemsize)d)
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
            gc_store(p1, %(strlendescr.offset)s,  i3, %(strlendescr.field_size)s)
            gc_store(p1, 0, 0, %(strhashdescr.field_size)s)
            cond_call_gc_wb(p1, descr=wbdescr)
            gc_store_indexed(p1,i2,i3,1,%(strdescr.basesize-1)d,1)
            gc_store_indexed(p1,i2,i3,%(unicodedescr.itemsize)d,%(unicodedescr.basesize)d,%(unicodedescr.itemsize)d)
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
            i4 = gc_load_indexed_i(p1,i2,1,%(strdescr.basesize-1)d,1)
            i5 = gc_load_indexed_i(p1,i2,%(unicodedescr.itemsize)d,%(unicodedescr.basesize)d,%(unicodedescr.itemsize)d)
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
            stm_read(p1)
            i1 = gc_load_i(p1, 0, -%(tydescr.field_size)s)

            cond_call_gc_wb(p7, descr=wbdescr)
            gc_store(p7, 0, 10, %(tydescr.field_size)s)

            $HCS

            cond_call_gc_wb(p7, descr=wbdescr)
            gc_store(p7, 0, 20, %(tydescr.field_size)s)

            stm_read(p1)
            i3 = gc_load_i(p1, 0, -%(tydescr.field_size)s)

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
            gc_store(p7, 0, 10, %(tydescr.field_size)s)
            call_release_gil_n(123, descr=calldescr2)
            guard_not_forced() []

            cond_call_gc_wb(p7, descr=wbdescr)
            gc_store(p7, 0, 20, %(tydescr.field_size)s)

            jump(i2, p7)
        """, calldescr2=calldescr2)

    def test_fallback_to_inevitable(self):
        T = rffi.CArrayPtr(rffi.TIME_T)
        calldescr2 = get_call_descr(self.gc_ll_descr, [T], rffi.TIME_T)
        oplist = [
            ("setfield_raw(i1, i2, descr=tydescr)",
             "gc_store(i1, 0,  i2, %(tydescr.field_size)s)"),
            ("setarrayitem_raw(i1, i2, i3, descr=adescr)",
             "gc_store_indexed(i1, i2, i3, %(adescr.itemsize)s, %(adescr.basesize)s, %(adescr.itemsize)s)"),
            #"setinteriorfield_raw(i1, i2, i3, descr=intzdescr)", -- no such op
            ("escape_n(i1)","escape_n(i1)"),    # a generic unknown operation
            ]
        for op, rop in oplist:
            self.check_rewrite("""
                [i1, i2, i3, p7]
                setfield_gc(p7, 10, descr=tydescr)
                %s
                setfield_gc(p7, 20, descr=tydescr)
                jump(i2, p7)
            """ % op, """
                [i1, i2, i3, p7]
                cond_call_gc_wb(p7, descr=wbdescr)
                gc_store(p7, 0, 10, %%(tydescr.field_size)s)
                $INEV
                %s
                cond_call_gc_wb(p7, descr=wbdescr)
                gc_store(p7, 0, 20, %%(tydescr.field_size)s)

                jump(i2, p7)
            """ % rop, calldescr2=calldescr2)

    def test_copystrcontent_new(self):
        self.check_rewrite("""
            [p1, i1, i2, i3]
            p2 = newstr(i3)
            copystrcontent(p1, p2, i1, i2, i3)
            jump()
        """, """
            [p1, i1, i2, i3]
            p2 = call_malloc_nursery_varsize(1, 1, i3, descr=strdescr)
            gc_store(p2, %(strlendescr.offset)s,  i3, %(strlendescr.field_size)s)
            gc_store(p2, 0, 0, %(strhashdescr.field_size)s)
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
                jump(p1)
            """ % op)

    def test_call_force(self):
        class fakeextrainfo:
            oopspecindex=0
            call_shortcut = None
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
                gc_store(p1, 0, 10, %%(tydescr.field_size)s)
                %s
                %s
                %s
                cond_call_gc_wb(p1, descr=wbdescr)
                gc_store(p1, 0, 20, %%(tydescr.field_size)s)

                jump(p1)
            """ % (op, guard, tr_break), calldescr2=calldescr2)

    def test_call_assembler(self):
        self.check_rewrite("""
        [i0, f0]
        i2 = call_assembler_i(i0, f0, descr=casmdescr)
        guard_not_forced()[]
        """, """
        [i0, f0]
        i1 = gc_load_i(ConstClass(frame_info),  1, %(jfi_frame_depth.field_size)s)
        p1 = call_malloc_nursery_varsize_frame(i1)
        gc_store(p1, %(stmflagsdescr.offset)s,  0, %(stmflagsdescr.field_size)s)
        gc_store(p1, 0, 0, %(tiddescr.field_size)s)

        gc_store(p1, 1, 0, %(jf_extra_stack_depth.field_size)s)
        gc_store(p1, 1, NULL, %(jf_savedata.field_size)s)
        gc_store(p1, 1, NULL, %(jf_force_descr.field_size)s)
        gc_store(p1, 1, NULL, %(jf_descr.field_size)s)
        gc_store(p1, 1, NULL, %(jf_guard_exc.field_size)s)
        gc_store(p1, 1, NULL, %(jf_forward.field_size)s)

        gc_store(p1, 0, i1, %(framelendescr.field_size)s)
        gc_store(p1, 1, ConstClass(frame_info), %(jf_frame_info.field_size)s)
        gc_store(p1, 3, i0, 8)
        gc_store(p1, 13, f0, 8)

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
        stm_read(p1)
        p2 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
        cond_call_gc_wb(p1, descr=wbdescr)
        gc_store(p1, %(tzdescr.offset)s,  p2, %(tzdescr.field_size)s)

        i1 = gc_load_i(ConstClass(frame_info),  1, %(jfi_frame_depth.field_size)s)
        p5 = call_malloc_nursery_varsize_frame(i1)
        gc_store(p5, %(stmflagsdescr.offset)s,  0, %(stmflagsdescr.field_size)s)
        gc_store(p5, 0, 0, %(tiddescr.field_size)s)
        gc_store(p5, 1, 0, %(jf_extra_stack_depth.field_size)s)
        gc_store(p5, 1, NULL, %(jf_savedata.field_size)s)
        gc_store(p5, 1, NULL, %(jf_force_descr.field_size)s)
        gc_store(p5, 1, NULL, %(jf_descr.field_size)s)
        gc_store(p5, 1, NULL, %(jf_guard_exc.field_size)s)
        gc_store(p5, 1, NULL, %(jf_forward.field_size)s)
        gc_store(p5, 0, i1, %(framelendescr.field_size)s)
        gc_store(p5, 1, ConstClass(frame_info), %(jf_frame_info.field_size)s)
        gc_store(p5, 3, i0, 8)
        gc_store(p5, 13, f0, 8)
        i3 = call_assembler_i(p5, descr=casmdescr)
        guard_not_forced() []

        stm_read(p1)
        p3 = gc_load_r(p1,  %(tzdescr.field_size)s, %(tzdescr.field_size)s)
        cond_call_gc_wb(p1, descr=wbdescr)
        gc_store(p1, %(tzdescr.offset)s,  p3, %(tzdescr.field_size)s)
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
            $INIT(p0,sdescr)
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
            $INIT(p0,sdescr)
            p1 = nursery_ptr_increment(p0, %(sdescr.size)d)
            $INIT(p1,tdescr)
            p2 = nursery_ptr_increment(p1, %(tdescr.size)d)
            $INIT(p2,sdescr)
            gc_store(p1, %(tdescr.gc_fielddescrs[0].offset)s, 0, %(tdescr.gc_fielddescrs[0].field_size)s)
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
            $INIT(p0,adescr)
            gc_store(p0, 0, 10, %(alendescr.field_size)s)
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
            $INIT(p0,sdescr)
            p1 = nursery_ptr_increment(p0, %(sdescr.size)d)
            $INIT(p1,adescr)
            gc_store(p1, 0, 10, %(alendescr.field_size)s)
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
            $INIT(p0,bdescr)
            gc_store(p0, 0, 6, %(blendescr.field_size)s)
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
            $INIT(p0,bdescr)
            gc_store(p0, 0, 5, %(blendescr.field_size)s)
            p1 = nursery_ptr_increment(p0, %(bdescr.basesize + 8)d)
            $INIT(p1,bdescr)
            gc_store(p1, 0, 5, %(blendescr.field_size)s)
            p2 = nursery_ptr_increment(p1, %(bdescr.basesize + 8)d)
            $INIT(p2,bdescr)
            gc_store(p2, 0, 5, %(blendescr.field_size)s)
            p3 = nursery_ptr_increment(p2, %(bdescr.basesize + 8)d)
            $INIT(p3,bdescr)
            gc_store(p3, 0, 5, %(blendescr.field_size)s)
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
            $INIT(p0,edescr)
            p1 = nursery_ptr_increment(p0, %(2*WORD)d)
            $INIT(p1,edescr)
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
            gc_store(p0, 0, i0, %(blendescr.field_size)s)
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
        gc_store(p0, %(strlendescr.offset)s,  i0, %(strlendescr.field_size)s)
        gc_store(p0, 0, 0, %(strhashdescr.field_size)s)
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

            p0 = call_r(ConstClass(malloc_array_nonstandard), \
                                64, 8,                                \
                                %(nonstd_descr.lendescr.offset)d,     \
                                6464, i0,                             \
                                descr=malloc_array_nonstandard_descr)
            check_memory_error(p0)
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
            p0 = call_r(ConstClass(malloc_array), 1,  \
                                %(bdescr.tid)d, 103,          \
                                descr=malloc_array_descr)
            check_memory_error(p0)
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
            $INIT(p0,bdescr)
            gc_store(p0, 0, 101, %(blendescr.field_size)s)
            p1 = nursery_ptr_increment(p0, %(bdescr.basesize + 104)d)
            $INIT(p1,bdescr)
            gc_store(p1, 0, 102, %(blendescr.field_size)s)
            p2 = call_malloc_nursery(    \
                              %(bdescr.basesize + 104)d)
            $INIT(p2,bdescr)
            gc_store(p2, 0, 103, %(blendescr.field_size)s)
        """)

    def test_rewrite_assembler_huge_size(self):
        # "huge" is defined as "larger than 0xffffff bytes, or 16MB"
        self.check_rewrite("""
            []
            p0 = new_array(20000000, descr=bdescr)
            jump()
        """, """
            []
            p0 = call_r(ConstClass(malloc_array), 1, \
                                %(bdescr.tid)d, 20000000,    \
                                descr=malloc_array_descr)
            check_memory_error(p0)
            jump()
        """)

    def test_new_with_vtable(self):
        self.check_rewrite("""
            []
            p0 = new_with_vtable(descr=o_descr)
        """, """
            [p1]
            p0 = call_malloc_nursery(104)      # rounded up
            $INIT(p0,o_descr)
            gc_store(p0, 0, ConstClass(o_vtable), %(vtable_descr.field_size)s)
        """)

    def test_new_with_vtable_too_big(self):
        self.gc_ll_descr.max_size_of_young_obj = 100
        self.check_rewrite("""
            []
            p0 = new_with_vtable(descr=o_descr)
        """, """
            [p1]
            p0 = call_r(ConstClass(malloc_big_fixedsize), 104, 9315, \
                                descr=malloc_big_fixedsize_descr)
            check_memory_error(p0)
            gc_store(p0, 0, ConstClass(o_vtable), %(vtable_descr.field_size)s)
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
                      %(strdescr.basesize + 15 * strdescr.itemsize + \
                        unicodedescr.basesize + 10 * unicodedescr.itemsize)d)
            $INIT(p0,unicodedescr)
            gc_store(p0, %(strlendescr.offset)s, 14, %(strlendescr.field_size)s)
            gc_store(p0, 0, 0, %(strhashdescr.field_size)s)

            p1 = nursery_ptr_increment(p0, %(strdescr.basesize + 15 * strdescr.itemsize)d)
            $INIT(p1, unicodedescr)
            gc_store(p1, %(unicodelendescr.offset)s, 10, %(strlendescr.field_size)s)
            gc_store(p1, 0, 0, %(unicodehashdescr.field_size)s)

            p2 = call_malloc_nursery_varsize(2, 4, i2, \
                                descr=unicodedescr)
            gc_store(p2, %(unicodelendescr.offset)s, i2, %(strlendescr.field_size)s)
            gc_store(p2, 0, 0, %(unicodehashdescr.field_size)s)

            p3 = call_malloc_nursery_varsize(1, 1, i2, \
                                descr=strdescr)
            gc_store(p3, %(strlendescr.offset)s, i2, %(strlendescr.field_size)s)
            gc_store(p3, 0, 0, %(strhashdescr.field_size)s)

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
            $INIT(p1,cdescr)
            gc_store(p1, 0, 5, %(clendescr.field_size)s)
            %(zero_array('p1', 0, 5, 'cdescr', cdescr))s
            label(p1, i2, p3)
            cond_call_gc_wb_array(p1, i2, descr=wbdescr)
            gc_store_indexed(p1, i2, p3, %(cdescr.itemsize)s, %(cdescr.basesize)s, %(cdescr.itemsize)s)
        """)

    def test_transaction_break_makes_size_unknown(self):
        class fakeextrainfo:
            call_shortcut = None
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
            $INIT(p0, bdescr)
            gc_store(p0, 0, 5, %(blendescr.field_size)s)

            p1 = nursery_ptr_increment(p0, %(bdescr.basesize + 8)d)
            $INIT(p1, bdescr)
            gc_store(p1, 0, 5, %(blendescr.field_size)s)

            call_may_force_n(12345, descr=calldescr2)   # stm_transaction_break
            guard_not_forced() []

            p2 = call_malloc_nursery(    \
                              %(bdescr.basesize + 8)d)
            $INIT(p2, bdescr)
            gc_store(p2, 0, 5, %(blendescr.field_size)s)
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
                p2 = getfield_gc_r(p1, descr=uxdescr)
                i4 = getarrayitem_gc%(pure)s_i(p4, i1, descr=vdescr)
                jump(p2)
            """ % d, """
                [p1, p3, i1, p4]
                %(comment)s stm_read(p1)
                p2 = gc_load_r(p1, 0, -%%(uxdescr.field_size)s)
                %(comment)s stm_read(p4)
                i4 = gc_load_indexed_i(p4, i1, %%(vdescr.itemsize)s, %%(vdescr.basesize)s, %%(vdescr.itemsize)s)
                jump(p2)
            """ % d, uxdescr=uxdescr, vdescr=vdescr)

    def test_stm_location_1(self):
        self.check_rewrite("""
            [p1, p2]
            setfield_gc(p1, p2, descr=tzdescr) {50}
        """, """
            [p1, p2]
            cond_call_gc_wb(p1, descr=wbdescr) {50}
            gc_store(p1, %(tzdescr.offset)s, p2, %(tzdescr.field_size)s) {50}
            #setfield_gc(p1, p2, descr=tzdescr) {50}
        """)

    def test_stm_location_2(self):
        self.check_rewrite("""
            [i1]
            i3 = getfield_raw_i(i1, descr=tydescr) {52}
        """, """
            [i1]
            $INEV {52}
            i3 = gc_load_i(i1, 0, -%(tydescr.field_size)d) {52}
        """)

    def test_stm_location_3(self):
        self.check_rewrite("""
        [i0, f0]
        i2 = call_assembler_i(i0, f0, descr=casmdescr) {54}
        guard_not_forced() [] {55}
        """, """
        [i0, f0]
        i1 = gc_load_i(ConstClass(frame_info),  1, %(jfi_frame_depth.field_size)s) {54}
        p1 = call_malloc_nursery_varsize_frame(i1) {54}
        gc_store(p1, %(stmflagsdescr.offset)s,  0, %(stmflagsdescr.field_size)s) {54}
        gc_store(p1, 0, 0, %(tiddescr.field_size)s) {54}
        gc_store(p1, 1, 0, %(jf_extra_stack_depth.field_size)s) {54}
        gc_store(p1, 1, NULL, %(jf_savedata.field_size)s) {54}
        gc_store(p1, 1, NULL, %(jf_force_descr.field_size)s) {54}
        gc_store(p1, 1, NULL, %(jf_descr.field_size)s) {54}
        gc_store(p1, 1, NULL, %(jf_guard_exc.field_size)s) {54}
        gc_store(p1, 1, NULL, %(jf_forward.field_size)s) {54}
        gc_store(p1, 0, i1, %(framelendescr.field_size)s) {54}
        gc_store(p1, 1, ConstClass(frame_info), %(jf_frame_info.field_size)s) {54}
        gc_store(p1, 3, i0, 8)
        gc_store(p1, 13, f0, 8)
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
            gc_store_indexed(p1, i3, p3, %(cdescr.itemsize)s, %(cdescr.basesize)s, %(cdescr.itemsize)s) {81}
        """)

    def test_stm_should_break_transaction_no_malloc(self):
        self.check_rewrite("""
        []
        i1 = stm_should_break_transaction()
        jump(i1)
        """, """
        []
        i1 = stm_should_break_transaction()
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
        $INIT(p2,tdescr)
        i1 = stm_should_break_transaction()
        gc_store(p2, %(tdescr.gc_fielddescrs[0].offset)s, 0, %(tdescr.gc_fielddescrs[0].field_size)s)
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
        $INIT(p2, tdescr)
        gc_store(p2, %(tdescr.gc_fielddescrs[0].offset)s, 0, %(tdescr.gc_fielddescrs[0].field_size)s)
        label()
        i1 = stm_should_break_transaction()
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
        $INIT(p2,tdescr)
        gc_store(p2, %(tdescr.gc_fielddescrs[0].offset)s, 0, %(tdescr.gc_fielddescrs[0].field_size)s)
        $INEV
        escape_n()
        """)
