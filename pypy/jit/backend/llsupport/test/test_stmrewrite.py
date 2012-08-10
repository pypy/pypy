from pypy.jit.backend.llsupport.descr import *
from pypy.jit.backend.llsupport.gc import *
from pypy.jit.metainterp.gc import get_description
from pypy.jit.backend.llsupport.test.test_rewrite import RewriteTests


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
        class FakeCPU(object):
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
        RewriteTests.check_rewrite(self, frm_operations, to_operations,
                                   **namespace)

    def test_rewrite_one_setfield_gc(self):
        self.check_rewrite("""
            [p1, p2]
            setfield_gc(p1, p2, descr=tzdescr)
            jump()
        """, """
            [p1, p2]
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            jump()
        """)

    def test_rewrite_setfield_gc_const(self):
        self.check_rewrite("""
            [p1, p2]
            setfield_gc(ConstPtr(t), p2, descr=tzdescr)
            jump()
        """, """
            [p1, p2]
            p3 = same_as(ConstPtr(t))
            cond_call_gc_wb(p3, 0, descr=wbdescr)
            setfield_gc(p3, p2, descr=tzdescr)
            jump()
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
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            cond_call_gc_wb(p3, 0, descr=wbdescr)
            setfield_gc(p3, p4, descr=tzdescr)
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
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            setfield_gc(p1, i3, descr=tydescr)
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
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setfield_gc(p1, p2, descr=tzdescr)
            label(p1, i3)
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setfield_gc(p1, i3, descr=tydescr)
            jump(p1)
        """)

    def test_remove_debug_merge_point(self):
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
            "i3 = ptr_eq(p1, p2)",
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
                jump(i2)
            """ % op
            self.check_rewrite(testcase, testcase)

    def test_rewrite_getfield_gc(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            stm_read_before(p1, descr=wbdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            stm_read_after(p1)
            jump(p2)
        """)

    def test_rewrite_getfield_gc_const(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(ConstPtr(t), descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            p3 = same_as(ConstPtr(t))
            stm_read_before(p3, descr=wbdescr)
            p2 = getfield_gc(p3, descr=tzdescr)
            stm_read_after(p3)
            jump(p2)
        """)

    def test_rewrite_getarrayitem_gc(self):
        self.check_rewrite("""
            [p1, i2]
            i3 = getarrayitem_gc(p1, i2, descr=adescr)
            jump(i3)
        """, """
            [p1, i2]
            stm_read_before(p1, descr=wbdescr)
            i3 = getarrayitem_gc(p1, i2, descr=adescr)
            stm_read_after(p1)
            jump(i3)
        """)

    def test_rewrite_getinteriorfield_gc(self):
        self.check_rewrite("""
            [p1, i2]
            i3 = getinteriorfield_gc(p1, i2, descr=adescr)
            jump(i3)
        """, """
            [p1, i2]
            stm_read_before(p1, descr=wbdescr)
            i3 = getinteriorfield_gc(p1, i2, descr=adescr)
            stm_read_after(p1)
            jump(i3)
        """)

    def test_rewrite_several_getfield_gcs(self):
        py.test.skip("optimization")
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            i2 = getfield_gc(p1, descr=tydescr)
            jump(p2, i2)
        """, """
            [p1]
            stm_read_before(p1, descr=wbdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            i2 = getfield_gc(p1, descr=tydescr)
            stm_read_after(p1)
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
            stm_read_before(p1, descr=wbdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            stm_read_after(p1)
            stm_read_before(p2, descr=wbdescr)
            i2 = getfield_gc(p2, descr=tydescr)
            stm_read_after(p2)
            jump(p2, i2)
        """)

    def test_move_forward_getfield_gc(self):
        py.test.skip("optimization")
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            guard_nonnull(p2) [i1]
            i2 = getfield_gc(p1, descr=tydescr)
            jump(p2, i2)
        """, """
            [p1]
            stm_read_before(p1, descr=wbdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            i2 = getfield_gc(p1, descr=tydescr)
            stm_read_after(p1)
            guard_nonnull(p2) [i1]
            jump(p2, i2)
        """)

    def test_dont_move_forward_over_sideeffect(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            call(123)
            i2 = getfield_gc(p1, descr=tydescr)
            jump(p2, i2)
        """, """
            [p1]
            stm_read_before(p1, descr=wbdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            stm_read_after(p1)
            call(123)
            stm_read_before(p1, descr=wbdescr)
            i2 = getfield_gc(p1, descr=tydescr)
            stm_read_after(p1)
            jump(p2, i2)
        """)

    def test_rewrite_getfield_gc_on_local(self):
        self.check_rewrite("""
            [p1]
            setfield_gc(p1, 5, descr=tydescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            jump(p2)
        """, """
            [p1]
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setfield_gc(p1, 5, descr=tydescr)
            p2 = getfield_gc(p1, descr=tzdescr)
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
            jump(p2)
        """)

    def test_rewrite_getfield_gc_on_future_local(self):
        py.test.skip("optimization")
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            setfield_gc(p1, 5, descr=tydescr)
            jump(p2)
        """, """
            [p1]
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            setfield_gc(p1, 5, descr=tydescr)
            jump(p2)
        """)

    def test_rewrite_getfield_gc_on_future_local_after_call(self):
        py.test.skip("optimization")
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            call(p2)
            setfield_gc(p1, 5, descr=tydescr)
            jump(p2)
        """, """
            [p1]
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            p2 = getfield_gc(p1, descr=tzdescr)
            call(p2)
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setfield_gc(p1, 5, descr=tydescr)
            jump(p2)
        """)

    def test_getfield_raw(self):
        self.check_rewrite("""
            [i1, i2]
            i3 = getfield_raw(i1, descr=?)
            keepalive(i3)     # random ignored operation
            i4 = getfield_raw(i2, descr=?)
            jump(i3, i4)
        """, """
            [i1, i2]
            $INEV
            i3 = getfield_raw(i1, descr=?)
            keepalive(i3)
            i4 = getfield_raw(i2, descr=?)
            jump(i3, i4)
        """)

    def test_getfield_raw_over_label(self):
        self.check_rewrite("""
            [i1, i2]
            i3 = getfield_raw(i1, descr=?)
            label(i1, i2, i3)
            i4 = getfield_raw(i2, descr=?)
            jump(i3, i4)
        """, """
            [i1, i2]
            $INEV
            i3 = getfield_raw(i1, descr=?)
            label(i1, i2, i3)
            $INEV
            i4 = getfield_raw(i2, descr=?)
            jump(i3, i4)
        """)

    def test_getarrayitem_raw(self):
        self.check_rewrite("""
            [i1, i2]
            i3 = getarrayitem_raw(i1, 5, descr=?)
            i4 = getarrayitem_raw(i2, i3, descr=?)
            jump(i3, i4)
        """, """
            [i1, i2]
            $INEV
            i3 = getarrayitem_raw(i1, 5, descr=?)
            i4 = getarrayitem_raw(i2, i3, descr=?)
            jump(i3, i4)
        """)

    def test_getinteriorfield_raw(self):
        self.check_rewrite("""
            [i1, i2]
            i3 = getinteriorfield_raw(i1, 5, descr=?)
            i4 = getinteriorfield_raw(i2, i3, descr=?)
            jump(i3, i4)
        """, """
            [i1, i2]
            $INEV
            i3 = getinteriorfield_raw(i1, 5, descr=?)
            i4 = getinteriorfield_raw(i2, i3, descr=?)
            jump(i3, i4)
        """)

    def test_rewrite_unrelated_setarrayitem_gcs(self):
        self.check_rewrite("""
            [p1, i1, p2, p3, i3, p4]
            setarrayitem_gc(p1, i1, p2, descr=?)
            setarrayitem_gc(p3, i3, p4, descr=?)
            jump()
        """, """
            [p1, i1, p2, p3, i3, p4]
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setarrayitem_gc(p1, i1, p2, descr=?)
            cond_call_gc_wb(p3, 0, descr=wbdescr)
            setarrayitem_gc(p3, i3, p4, descr=?)
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
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setarrayitem_gc(p1, i2, p2, descr=adescr)
            i4 = read_timestamp()
            setarrayitem_gc(p1, i3, p3, descr=adescr)
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
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setinteriorfield_gc(p1, i2, p2, descr=adescr)
            i4 = read_timestamp()
            setinteriorfield_gc(p1, i3, p3, descr=adescr)
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
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            strsetitem(p1, i2, i3)
            unicodesetitem(p1, i2, i3)
            jump()
        """)

    def test_fallback_to_inevitable(self):
        oplist = [
            "setfield_raw(i1, i2, descr=?)",
            "setarrayitem_raw(i1, i2, i3, descr=?)",
            "setinteriorfield_raw(i1, i2, i3, descr=?)",
            "call_release_gil(123, descr=calldescr2)",
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
                cond_call_gc_wb(p7, 0, descr=wbdescr)
                setfield_gc(p7, 10, descr=tydescr)
                $INEV
                %s
                cond_call_gc_wb(p7, 0, descr=wbdescr)
                setfield_gc(p7, 20, descr=tydescr)
                jump(i2, p7)
            """ % op)

    def test_copystrcontent(self):
        self.check_rewrite("""
            [p1, p2, i1, i2, i3]
            copystrcontent(p1, p2, i1, i2, i3)
            jump()
        """, """
            [p1, p2, i1, i2, i3]
            cond_call_gc_wb(p2, 0, descr=wbdescr)
            stm_read_before(p1, descr=wbdescr)
            copystrcontent(p1, p2, i1, i2, i3)
            stm_read_after(p1)
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
                cond_call_gc_wb(p1, 0, descr=wbdescr)
                setfield_gc(p1, 10, descr=tydescr)
                %s
                setfield_gc(p1, 20, descr=tydescr)
                jump(p1)
            """ % op)

    def test_call_force(self):
        for op in ["call(123, descr=calldescr2)",
                   "call_assembler(123, descr=loopdescr)",
                   "call_may_force(123, descr=calldescr2)",
                   "call_loopinvariant(123, descr=calldescr2)",
                   ]:
            self.check_rewrite("""
                [p1]
                setfield_gc(p1, 10, descr=tydescr)
                %s
                setfield_gc(p1, 20, descr=tydescr)
                jump(p1)
            """ % op, """
                [p1]
                cond_call_gc_wb(p1, 0, descr=wbdescr)
                setfield_gc(p1, 10, descr=tydescr)
                %s
                cond_call_gc_wb(p1, 0, descr=wbdescr)
                setfield_gc(p1, 20, descr=tydescr)
                jump(p1)
            """ % op)
