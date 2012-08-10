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

    def test_rewrite_one_setfield_gc(self):
        self.check_rewrite("""
            [p1, p2]
            setfield_gc(p1, p2, descr=tzdescr)
            jump()
        """, """
            [p1]
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setfield_gc(p2, p2, descr=tzdescr)
            jump()
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

    def test_ignore_some_operations(self):
        oplist = [
            "guard_true(i1) [i2]",    # all guards
            "i3 = int_add(i1, i2)",   # all pure operations
            "f3 = float_abs(f1)",
            "i3 = ptr_eq(p1, p2)",
            "i3 = force_token()",
            "i3 = read_timestamp()",
            "i3 = mark_opaque_ptr(p1)",
            "debug_merge_point(i1, i2)",
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
            stm_read_before()
            p2 = getfield_gc(p1, descr=tzdescr)
            stm_read_after()
            jump(p2)
        """)

    def test_rewrite_getarrayitem_gc(self):
        self.check_rewrite("""
            [p1, i2]
            i3 = getarrayitem_gc(p1, i2, descr=adescr)
            jump(i3)
        """, """
            [p1, i2]
            stm_read_before()
            i3 = stm_getarrayitem_gc(p1, i2, descr=adescr)
            stm_read_after()
            jump(i3)
        """)

    def test_rewrite_getinteriorfield_gc(self):
        self.check_rewrite("""
            [p1, i2]
            i3 = getinteriorfield_gc(p1, ...)
            jump(i3)
        """, """
            [p1, i2]
            stm_read_before()
            i3 = stm_getinteriorfield_gc(p1, ...)
            stm_read_after()
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
            stm_read_before()
            p2 = getfield_gc(p1, descr=tzdescr)
            i2 = getfield_gc(p1, descr=tydescr)
            stm_read_after()
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
            stm_read_before()
            p2 = getfield_gc(p1, descr=tzdescr)
            stm_read_after()
            stm_read_before()
            i2 = getfield_gc(p2, descr=tydescr)
            stm_read_after()
            jump(p2, i2)
        """)

    def test_move_forward_getfield_gc(self):
        self.check_rewrite("""
            [p1]
            p2 = getfield_gc(p1, descr=tzdescr)
            guard_nonnull(p2) [i1]
            i2 = getfield_gc(p1, descr=tydescr)
            jump(p2, i2)
        """, """
            [p1]
            stm_read_before()
            p2 = getfield_gc(p1, descr=tzdescr)
            i2 = getfield_gc(p1, descr=tydescr)
            stm_read_after()
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
            stm_read_before()
            p2 = getfield_gc(p1, descr=tzdescr)
            stm_read_after()
            call(123)
            stm_read_before()
            i2 = getfield_gc(p1, descr=tydescr)
            stm_read_after()
            jump(p2, i2)
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
            call(521)     # stm_become_inevitable
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
            call(521)     # stm_become_inevitable
            i3 = getfield_raw(i1, descr=?)
            label(i1, i2, i3)
            call(521)     # stm_become_inevitable
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
            call(521)     # stm_become_inevitable
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
            call(521)     # stm_become_inevitable
            i3 = getinteriorfield_raw(i1, 5, descr=?)
            i4 = getinteriorfield_raw(i2, i3, descr=?)
            jump(i3, i4)
        """)

    def test_new_turns_into_malloc(self):
        self.check_rewrite("""
            []
            p0 = new(descr=sdescr)
            jump(p0)
        """, """
            []
            p0 = call_malloc_nursery(%(sdescr.size)d)
            setfield_gc(p0, 1234, descr=tiddescr)
            jump(p0)
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
            [p1, p2, i3, i2, i3]
            setarrayitem_gc(p1, i2, p2, descr=?)
            i4 = read_timestamp()
            setarrayitem_gc(p1, i3, i3, descr=?)
            jump()
        """, """
            [p1, p1, i3]
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setarrayitem_gc(p1, i2, p2, descr=?)
            i4 = read_timestamp()
            setarrayitem_gc(p1, i3, p3, descr=?)
            jump()
        """)

    def test_rewrite_several_setinteriorfield_gc(self):
        self.check_rewrite("""
            [p1, p2, i3, i2, i3]
            setinteriorfield_gc(p1, i2, p2, descr=?)
            setinteriorfield_gc(p1, i3, i3, descr=?)
            jump()
        """, """
            [p1, p1, i3]
            cond_call_gc_wb(p1, 0, descr=wbdescr)
            setinteriorfield_gc(p1, i2, p2, descr=?)
            setinteriorfield_gc(p1, i3, p3, descr=?)
            jump()
        """)

    def test_rewrite_strsetitem_unicodesetitem(self):
        self.check_rewrite("""
            [p1, i2, i3]
            strsetitem(p1, i2, i3)
            unicodesetitem(p1, i2, i3)
            jump()
        """, """
            [p1, p2, i3]
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
                call(521)     # stm_become_inevitable
                %s
                cond_call_gc_wb(p7, 0, descr=wbdescr)
                setfield_gc(p7, 10, descr=tydescr)
                jump(i2, p7)
            """ % op)

    def test_copystrcontent(self):
        xxx  #?

    def test_call_dont_force(self):
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
