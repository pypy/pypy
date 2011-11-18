from pypy.jit.backend.llsupport.descr import *
from pypy.jit.backend.llsupport.gc import *
from pypy.jit.metainterp.gc import get_description
from pypy.jit.tool.oparser import parse


class Evaluator(object):
    def __init__(self, scope):
        self.scope = scope
    def __getitem__(self, key):
        return eval(key, self.scope)


class RewriteTests(object):
    def check_rewrite(self, frm_operations, to_operations):
        self.gc_ll_descr.translate_support_code = False
        try:
            S = lltype.GcStruct('S', ('x', lltype.Signed),
                                     ('y', lltype.Signed))
            sdescr = get_size_descr(self.gc_ll_descr, S)
            sdescr.tid = 1234
            #
            T = lltype.GcStruct('T', ('y', lltype.Signed),
                                     ('z', lltype.Signed),
                                     ('t', lltype.Signed))
            tdescr = get_size_descr(self.gc_ll_descr, T)
            tdescr.tid = 5678
            #
            A = lltype.GcArray(lltype.Signed)
            adescr = get_array_descr(self.gc_ll_descr, A)
            adescr.tid = 4321
            alendescr = get_field_arraylen_descr(self.gc_ll_descr, A)
            #
            B = lltype.GcArray(lltype.Char)
            bdescr = get_array_descr(self.gc_ll_descr, B)
            bdescr.tid = 8765
            blendescr = get_field_arraylen_descr(self.gc_ll_descr, B)
            #
            E = lltype.GcStruct('Empty')
            edescr = get_size_descr(self.gc_ll_descr, E)
            edescr.tid = 9000
            #
            tiddescr = self.gc_ll_descr.fielddescr_tid
            WORD = globals()['WORD']
            #
            ops = parse(frm_operations, namespace=locals())
            expected = parse(to_operations % Evaluator(locals()),
                             namespace=locals())
            operations = self.gc_ll_descr.rewrite_assembler(None,
                                                            ops.operations,
                                                            [])
        finally:
            self.gc_ll_descr.translate_support_code = True
        equaloplists(operations, expected.operations)

    def test_new_array_variable(self):
        self.check_rewrite("""
            [i1]
            p0 = new_array(i1, descr=adescr)
            jump()
        """, """
            [i1]
            p0 = malloc_gc(%(adescr.get_base_size(False))d,         \
                           i1, %(adescr.get_item_size(False))d)
            setfield_gc(p0, 4321, descr=tiddescr)
            setfield_gc(p0, 10, descr=alendescr)
            jump()
        """)


class TestBoehm(RewriteTests):
    def setup_method(self, meth):
        self.gc_ll_descr = GcLLDescr_boehm(None, None, None)

    def test_new(self):
        self.check_rewrite("""
            []
            p0 = new(descr=sdescr)
            jump()
        """, """
            [p1]
            p0 = malloc_gc(%(sdescr.size)d, 0, 0)
            setfield_gc(p0, 1234, descr=tiddescr)
            jump()
        """)

    def test_no_collapsing(self):
        self.check_rewrite("""
            []
            p0 = new(descr=sdescr)
            p1 = new(descr=sdescr)
            jump()
        """, """
            [p1]
            p0 = malloc_gc(%(sdescr.size)d, 0, 0)
            setfield_gc(p0, 1234, descr=tiddescr)
            p1 = malloc_gc(%(sdescr.size)d, 0, 0)
            setfield_gc(p1, 1234, descr=tiddescr)
            jump()
        """)

    def test_new_array_fixed(self):
        self.check_rewrite("""
            []
            p0 = new_array(10, descr=adescr)
            jump()
        """, """
            []
            p0 = malloc_gc(%(adescr.get_base_size(False))d,         \
                           10, %(adescr.get_item_size(False))d)
            setfield_gc(p0, 4321, descr=tiddescr)
            setfield_gc(p0, 10, descr=alendescr)
            jump()
        """)


class TestFramework(RewriteTests):
    def setup_method(self, meth):
        class config_(object):
            class translation(object):
                gc = 'hybrid'
                gcrootfinder = 'asmgcc'
                gctransformer = 'framework'
                gcremovetypeptr = False
        class FakeTranslator(object):
            config = config_
        gcdescr = get_description(config_)
        self.gc_ll_descr = GcLLDescr_framework(gcdescr, FakeTranslator(),
                                               None, None)

    def test_rewrite_assembler_new_to_malloc(self):
        self.check_rewrite("""
            [p1]
            p0 = new(descr=sdescr)
            jump()
        """, """
            [p1]
            p0 = malloc_nursery(%(sdescr.size)d)
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
            p0 = malloc_nursery(%(sdescr.size + tdescr.size + sdescr.size)d)
            setfield_gc(p0, 1234, descr=tiddescr)
            p1 = int_add(p0, %(sdescr.size)d)
            setfield_gc(p1, 5678, descr=tiddescr)
            p2 = int_add(p1, %(tdescr.size)d)
            setfield_gc(p2, 1234, descr=tiddescr)
            jump()
        """)

    def test_rewrite_assembler_new_array_fixed_to_malloc(self):
        self.check_rewrite("""
            []
            p0 = new_array(10, descr=adescr)
            jump()
        """, """
            []
            p0 = malloc_nursery(%(adescr.get_base_size(False) +        \
                                  10 * adescr.get_item_size(False))d)
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
            p0 = malloc_nursery(%(sdescr.size +                        \
                                  adescr.get_base_size(False) +        \
                                  10 * adescr.get_item_size(False))d)
            setfield_gc(p0, 1234, descr=tiddescr)
            p1 = int_add(p0, %(sdescr.size)d)
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
            p0 = malloc_nursery(%(adescr.get_base_size(False) + 8)d)
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
            p0 = malloc_nursery(%(4 * (adescr.get_base_size(False) + 8))d)
            setfield_gc(p0, 8765, descr=tiddescr)
            setfield_gc(p0, 5, descr=blendescr)
            p1 = int_add(p0, %(adescr.get_base_size(False) + 8)d)
            setfield_gc(p1, 8765, descr=tiddescr)
            setfield_gc(p1, 5, descr=blendescr)
            p2 = int_add(p1, %(adescr.get_base_size(False) + 8)d)
            setfield_gc(p2, 8765, descr=tiddescr)
            setfield_gc(p2, 5, descr=blendescr)
            p3 = int_add(p2, %(adescr.get_base_size(False) + 8)d)
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
            p0 = malloc_nursery(%(4*WORD)d)
            setfield_gc(p0, 9000, descr=tiddescr)
            p1 = int_add(p0, %(2*WORD)d)
            setfield_gc(p1, 9000, descr=tiddescr)
            jump()
        """)

    def test_rewrite_assembler_maximal_size(self):
        xxx

    def test_rewrite_assembler_variable_size(self):
        xxx

    def test_rewrite_assembler_new_with_vtable(self):
        self.check_rewrite("""
            [p1]
            p0 = new_with_vtable(descr=vdescr)
            jump()
        """, """
            [p1]
            p0 = malloc_nursery(%(vdescr.size)d)
            setfield_gc(p0, 1234, descr=tiddescr)
            ...
            jump()
        """)

    def test_rewrite_assembler_newstr_newunicode(self):
        xxx

