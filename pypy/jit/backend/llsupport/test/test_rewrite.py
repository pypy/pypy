from pypy.jit.backend.llsupport.descr import *
from pypy.jit.backend.llsupport.gc import *
from pypy.jit.metainterp.gc import get_description
from pypy.jit.tool.oparser import parse
from pypy.jit.metainterp.optimizeopt.util import equaloplists
from pypy.jit.codewriter.heaptracker import register_known_gctype


class Evaluator(object):
    def __init__(self, scope):
        self.scope = scope
    def __getitem__(self, key):
        return eval(key, self.scope)


class RewriteTests(object):
    def check_rewrite(self, frm_operations, to_operations, **namespace):
        S = lltype.GcStruct('S', ('x', lltype.Signed),
                                 ('y', lltype.Signed))
        sdescr = get_size_descr(self.gc_ll_descr, S)
        sdescr.tid = 1234
        #
        T = lltype.GcStruct('T', ('y', lltype.Signed),
                                 ('z', lltype.Ptr(S)),
                                 ('t', lltype.Signed))
        tdescr = get_size_descr(self.gc_ll_descr, T)
        tdescr.tid = 5678
        tzdescr = get_field_descr(self.gc_ll_descr, T, 'z')
        #
        A = lltype.GcArray(lltype.Signed)
        adescr = get_array_descr(self.gc_ll_descr, A)
        adescr.tid = 4321
        alendescr = adescr.lendescr
        #
        B = lltype.GcArray(lltype.Char)
        bdescr = get_array_descr(self.gc_ll_descr, B)
        bdescr.tid = 8765
        blendescr = bdescr.lendescr
        #
        C = lltype.GcArray(lltype.Ptr(S))
        cdescr = get_array_descr(self.gc_ll_descr, C)
        cdescr.tid = 8111
        clendescr = cdescr.lendescr
        #
        E = lltype.GcStruct('Empty')
        edescr = get_size_descr(self.gc_ll_descr, E)
        edescr.tid = 9000
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
        #
        namespace.update(locals())
        #
        for funcname in self.gc_ll_descr._generated_functions:
            namespace[funcname] = self.gc_ll_descr.get_malloc_fn(funcname)
            namespace[funcname + '_descr'] = getattr(self.gc_ll_descr,
                                                     '%s_descr' % funcname)
        #
        ops = parse(frm_operations, namespace=namespace)
        expected = parse(to_operations % Evaluator(namespace),
                         namespace=namespace)
        operations = self.gc_ll_descr.rewrite_assembler(self.cpu,
                                                        ops.operations,
                                                        [])
        equaloplists(operations, expected.operations)


class TestBoehm(RewriteTests):
    def setup_method(self, meth):
        class FakeCPU(object):
            def sizeof(self, STRUCT):
                return SizeDescrWithVTable(102)
        self.cpu = FakeCPU()
        self.gc_ll_descr = GcLLDescr_boehm(None, None, None)

    def test_new(self):
        self.check_rewrite("""
            []
            p0 = new(descr=sdescr)
            jump()
        """, """
            [p1]
            p0 = call_malloc_gc(ConstClass(malloc_fixedsize), %(sdescr.size)d,\
                                descr=malloc_fixedsize_descr)
            jump()
        """)

    def test_no_collapsing(self):
        self.check_rewrite("""
            []
            p0 = new(descr=sdescr)
            p1 = new(descr=sdescr)
            jump()
        """, """
            []
            p0 = call_malloc_gc(ConstClass(malloc_fixedsize), %(sdescr.size)d,\
                                descr=malloc_fixedsize_descr)
            p1 = call_malloc_gc(ConstClass(malloc_fixedsize), %(sdescr.size)d,\
                                descr=malloc_fixedsize_descr)
            jump()
        """)

    def test_new_array_fixed(self):
        self.check_rewrite("""
            []
            p0 = new_array(10, descr=adescr)
            jump()
        """, """
            []
            p0 = call_malloc_gc(ConstClass(malloc_fixedsize), \
                                %(adescr.basesize + 10 * adescr.itemsize)d, \
                                descr=malloc_fixedsize_descr)
            setfield_gc(p0, 10, descr=alendescr)
            jump()
        """)

    def test_new_array_variable(self):
        self.check_rewrite("""
            [i1]
            p0 = new_array(i1, descr=adescr)
            jump()
        """, """
            [i1]
            p0 = call_malloc_gc(ConstClass(malloc_array),   \
                                %(adescr.basesize)d,        \
                                i1,                         \
                                %(adescr.itemsize)d,        \
                                %(adescr.lendescr.offset)d, \
                                descr=malloc_array_descr)
            jump()
        """)

    def test_new_with_vtable(self):
        self.check_rewrite("""
            []
            p0 = new_with_vtable(ConstClass(o_vtable))
            jump()
        """, """
            [p1]
            p0 = call_malloc_gc(ConstClass(malloc_fixedsize), 102, \
                                descr=malloc_fixedsize_descr)
            setfield_gc(p0, ConstClass(o_vtable), descr=vtable_descr)
            jump()
        """)

    def test_newstr(self):
        self.check_rewrite("""
            [i1]
            p0 = newstr(i1)
            jump()
        """, """
            [i1]
            p0 = call_malloc_gc(ConstClass(malloc_array), \
                                %(strdescr.basesize)d,    \
                                i1,                       \
                                %(strdescr.itemsize)d,    \
                                %(strlendescr.offset)d,   \
                                descr=malloc_array_descr)
            jump()
        """)

    def test_newunicode(self):
        self.check_rewrite("""
            [i1]
            p0 = newunicode(10)
            jump()
        """, """
            [i1]
            p0 = call_malloc_gc(ConstClass(malloc_fixedsize),   \
                                %(unicodedescr.basesize +       \
                                  10 * unicodedescr.itemsize)d, \
                                descr=malloc_fixedsize_descr)
            setfield_gc(p0, 10, descr=unicodelendescr)
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
        gcdescr = get_description(config_)
        self.gc_ll_descr = GcLLDescr_framework(gcdescr, None, None, None,
                                               really_not_translated=True)
        self.gc_ll_descr.write_barrier_descr.has_write_barrier_from_array = (
            lambda cpu: True)
        #
        class FakeCPU(object):
            def sizeof(self, STRUCT):
                descr = SizeDescrWithVTable(102)
                descr.tid = 9315
                return descr
        self.cpu = FakeCPU()

    def test_rewrite_assembler_new_to_malloc(self):
        self.check_rewrite("""
            [p1]
            p0 = new(descr=sdescr)
            jump()
        """, """
            [p1]
            p0 = call_malloc_nursery(%(sdescr.size)d)
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
            p0 = call_malloc_nursery(    \
                                %(adescr.basesize + 10 * adescr.itemsize)d)
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
            p0 = call_malloc_nursery(%(bdescr.basesize + 8)d)
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
            setfield_gc(p0, 8765, descr=tiddescr)
            setfield_gc(p0, 5, descr=blendescr)
            p1 = int_add(p0, %(bdescr.basesize + 8)d)
            setfield_gc(p1, 8765, descr=tiddescr)
            setfield_gc(p1, 5, descr=blendescr)
            p2 = int_add(p1, %(bdescr.basesize + 8)d)
            setfield_gc(p2, 8765, descr=tiddescr)
            setfield_gc(p2, 5, descr=blendescr)
            p3 = int_add(p2, %(bdescr.basesize + 8)d)
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
            setfield_gc(p0, 9000, descr=tiddescr)
            p1 = int_add(p0, %(2*WORD)d)
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
            p0 = call_malloc_gc(ConstClass(malloc_array), 1,  \
                                %(bdescr.tid)d, i0,           \
                                descr=malloc_array_descr)
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
            p0 = call_malloc_gc(ConstClass(malloc_fixedsize), \
                                %(bdescr.basesize + 104)d,    \
                                descr=malloc_fixedsize_descr)
            setfield_gc(p0, 8765, descr=tiddescr)
            setfield_gc(p0, 103, descr=blendescr)
            jump()
        """)

    def test_rewrite_assembler_maximal_size_2(self):
        self.gc_ll_descr.max_size_of_young_obj = 300
        self.check_rewrite("""
            []
            p0 = new_array(101, descr=bdescr)
            p1 = new_array(102, descr=bdescr)  # two new_arrays can be combined
            p2 = new_array(103, descr=bdescr)  # but not all three
            jump()
        """, """
            []
            p0 = call_malloc_nursery(    \
                              %(2 * (bdescr.basesize + 104))d)
            setfield_gc(p0, 8765, descr=tiddescr)
            setfield_gc(p0, 101, descr=blendescr)
            p1 = int_add(p0, %(bdescr.basesize + 104)d)
            setfield_gc(p1, 8765, descr=tiddescr)
            setfield_gc(p1, 102, descr=blendescr)
            p2 = call_malloc_nursery(    \
                              %(bdescr.basesize + 104)d)
            setfield_gc(p2, 8765, descr=tiddescr)
            setfield_gc(p2, 103, descr=blendescr)
            jump()
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
            p0 = new_with_vtable(ConstClass(o_vtable))
            jump()
        """, """
            [p1]
            p0 = call_malloc_nursery(104)      # rounded up
            setfield_gc(p0, 9315, descr=tiddescr)
            setfield_gc(p0, ConstClass(o_vtable), descr=vtable_descr)
            jump()
        """)

    def test_new_with_vtable_too_big(self):
        self.gc_ll_descr.max_size_of_young_obj = 100
        self.check_rewrite("""
            []
            p0 = new_with_vtable(ConstClass(o_vtable))
            jump()
        """, """
            [p1]
            p0 = call_malloc_gc(ConstClass(malloc_fixedsize), 104, \
                                descr=malloc_fixedsize_descr)
            setfield_gc(p0, 9315, descr=tiddescr)
            setfield_gc(p0, ConstClass(o_vtable), descr=vtable_descr)
            jump()
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
            setfield_gc(p0, %(strdescr.tid)d, descr=tiddescr)
            setfield_gc(p0, 14, descr=strlendescr)
            p1 = int_add(p0, %(strdescr.basesize + 16 * strdescr.itemsize)d)
            setfield_gc(p1, %(unicodedescr.tid)d, descr=tiddescr)
            setfield_gc(p1, 10, descr=unicodelendescr)
            p2 = call_malloc_gc(ConstClass(malloc_unicode), i2, \
                                descr=malloc_unicode_descr)
            p3 = call_malloc_gc(ConstClass(malloc_str), i2, \
                                descr=malloc_str_descr)
            jump()
        """)

    def test_write_barrier_before_setfield_gc(self):
        self.check_rewrite("""
            [p1, p2]
            setfield_gc(p1, p2, descr=tzdescr)
            jump()
        """, """
            [p1, p2]
            cond_call_gc_wb(p1, p2, descr=wbdescr)
            setfield_raw(p1, p2, descr=tzdescr)
            jump()
        """)

    def test_write_barrier_before_array_without_from_array(self):
        self.gc_ll_descr.write_barrier_descr.has_write_barrier_from_array = (
            lambda cpu: False)
        self.check_rewrite("""
            [p1, i2, p3]
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """, """
            [p1, i2, p3]
            cond_call_gc_wb(p1, p3, descr=wbdescr)
            setarrayitem_raw(p1, i2, p3, descr=cdescr)
            jump()
        """)

    def test_write_barrier_before_short_array(self):
        self.gc_ll_descr.max_size_of_young_obj = 2000
        self.check_rewrite("""
            [i2, p3]
            p1 = new_array(129, descr=cdescr)
            call(123456)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """, """
            [i2, p3]
            p1 = call_malloc_nursery(    \
                                %(cdescr.basesize + 129 * cdescr.itemsize)d)
            setfield_gc(p1, 8111, descr=tiddescr)
            setfield_gc(p1, 129, descr=clendescr)
            call(123456)
            cond_call_gc_wb(p1, p3, descr=wbdescr)
            setarrayitem_raw(p1, i2, p3, descr=cdescr)
            jump()
        """)

    def test_write_barrier_before_long_array(self):
        # the limit of "being too long" is fixed, arbitrarily, at 130
        self.gc_ll_descr.max_size_of_young_obj = 2000
        self.check_rewrite("""
            [i2, p3]
            p1 = new_array(130, descr=cdescr)
            call(123456)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """, """
            [i2, p3]
            p1 = call_malloc_nursery(    \
                                %(cdescr.basesize + 130 * cdescr.itemsize)d)
            setfield_gc(p1, 8111, descr=tiddescr)
            setfield_gc(p1, 130, descr=clendescr)
            call(123456)
            cond_call_gc_wb_array(p1, i2, p3, descr=wbdescr)
            setarrayitem_raw(p1, i2, p3, descr=cdescr)
            jump()
        """)

    def test_write_barrier_before_unknown_array(self):
        self.check_rewrite("""
            [p1, i2, p3]
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """, """
            [p1, i2, p3]
            cond_call_gc_wb_array(p1, i2, p3, descr=wbdescr)
            setarrayitem_raw(p1, i2, p3, descr=cdescr)
            jump()
        """)

    def test_label_makes_size_unknown(self):
        self.check_rewrite("""
            [i2, p3]
            p1 = new_array(5, descr=cdescr)
            label(p1, i2, p3)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """, """
            [i2, p3]
            p1 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p1, 8111, descr=tiddescr)
            setfield_gc(p1, 5, descr=clendescr)
            label(p1, i2, p3)
            cond_call_gc_wb_array(p1, i2, p3, descr=wbdescr)
            setarrayitem_raw(p1, i2, p3, descr=cdescr)
            jump()
        """)

    def test_write_barrier_before_setinteriorfield_gc(self):
        S1 = lltype.GcStruct('S1')
        INTERIOR = lltype.GcArray(('z', lltype.Ptr(S1)))
        interiordescr = get_array_descr(self.gc_ll_descr, INTERIOR)
        interiordescr.tid = 1291
        interiorlendescr = interiordescr.lendescr
        interiorzdescr = get_interiorfield_descr(self.gc_ll_descr,
                                                 INTERIOR, 'z')
        self.check_rewrite("""
            [p1, p2]
            setinteriorfield_gc(p1, 0, p2, descr=interiorzdescr)
            jump(p1, p2)
        """, """
            [p1, p2]
            cond_call_gc_wb(p1, p2, descr=wbdescr)
            setinteriorfield_raw(p1, 0, p2, descr=interiorzdescr)
            jump(p1, p2)
        """, interiorzdescr=interiorzdescr)

    def test_initialization_store(self):
        self.check_rewrite("""
            [p1]
            p0 = new(descr=tdescr)
            setfield_gc(p0, p1, descr=tzdescr)
            jump()
        """, """
            [p1]
            p0 = call_malloc_nursery(%(tdescr.size)d)
            setfield_gc(p0, 5678, descr=tiddescr)
            setfield_gc(p0, p1, descr=tzdescr)
            jump()
        """)

    def test_initialization_store_2(self):
        self.check_rewrite("""
            []
            p0 = new(descr=tdescr)
            p1 = new(descr=sdescr)
            setfield_gc(p0, p1, descr=tzdescr)
            jump()
        """, """
            []
            p0 = call_malloc_nursery(%(tdescr.size + sdescr.size)d)
            setfield_gc(p0, 5678, descr=tiddescr)
            p1 = int_add(p0, %(tdescr.size)d)
            setfield_gc(p1, 1234, descr=tiddescr)
            # <<<no cond_call_gc_wb here>>>
            setfield_gc(p0, p1, descr=tzdescr)
            jump()
        """)

    def test_initialization_store_array(self):
        self.check_rewrite("""
            [p1, i2]
            p0 = new_array(5, descr=cdescr)
            setarrayitem_gc(p0, i2, p1, descr=cdescr)
            jump()
        """, """
            [p1, i2]
            p0 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p0, 8111, descr=tiddescr)
            setfield_gc(p0, 5, descr=clendescr)
            setarrayitem_gc(p0, i2, p1, descr=cdescr)
            jump()
        """)

    def test_non_initialization_store(self):
        self.check_rewrite("""
            [i0]
            p0 = new(descr=tdescr)
            p1 = newstr(i0)
            setfield_gc(p0, p1, descr=tzdescr)
            jump()
        """, """
            [i0]
            p0 = call_malloc_nursery(%(tdescr.size)d)
            setfield_gc(p0, 5678, descr=tiddescr)
            p1 = call_malloc_gc(ConstClass(malloc_str), i0, \
                                descr=malloc_str_descr)
            cond_call_gc_wb(p0, p1, descr=wbdescr)
            setfield_raw(p0, p1, descr=tzdescr)
            jump()
        """)

    def test_non_initialization_store_label(self):
        self.check_rewrite("""
            [p1]
            p0 = new(descr=tdescr)
            label(p0, p1)
            setfield_gc(p0, p1, descr=tzdescr)
            jump()
        """, """
            [p1]
            p0 = call_malloc_nursery(%(tdescr.size)d)
            setfield_gc(p0, 5678, descr=tiddescr)
            label(p0, p1)
            cond_call_gc_wb(p0, p1, descr=wbdescr)
            setfield_raw(p0, p1, descr=tzdescr)
            jump()
        """)
