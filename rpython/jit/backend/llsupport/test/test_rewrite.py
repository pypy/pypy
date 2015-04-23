from rpython.jit.backend.llsupport.descr import get_size_descr,\
     get_field_descr, get_array_descr, ArrayDescr, FieldDescr,\
     SizeDescrWithVTable, get_interiorfield_descr
from rpython.jit.backend.llsupport.gc import GcLLDescr_boehm,\
     GcLLDescr_framework
from rpython.jit.backend.llsupport import jitframe
from rpython.jit.metainterp.gc import get_description
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.codewriter.heaptracker import register_known_gctype
from rpython.jit.metainterp.history import JitCellToken, FLOAT
from rpython.jit.metainterp.history import AbstractFailDescr
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper import rclass
from rpython.jit.backend.x86.arch import WORD

class Evaluator(object):
    def __init__(self, scope):
        self.scope = scope
    def __getitem__(self, key):
        return eval(key, self.scope)


class FakeLoopToken(object):
    pass

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
        strhashdescr     = self.gc_ll_descr.str_hash_descr
        unicodehashdescr = self.gc_ll_descr.unicode_hash_descr

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
        jf_savedata = framedescrs.jf_savedata
        jf_force_descr = framedescrs.jf_force_descr
        jf_descr = framedescrs.jf_descr
        jf_guard_exc = framedescrs.jf_guard_exc
        jf_forward = framedescrs.jf_forward
        jf_extra_stack_depth = framedescrs.jf_extra_stack_depth
        signedframedescr = self.cpu.signedframedescr
        floatframedescr = self.cpu.floatframedescr
        casmdescr.compiled_loop_token = clt
        #
        guarddescr = AbstractFailDescr()
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
        lltype.free(frame_info, flavor='raw')

class FakeTracker(object):
    pass

class BaseFakeCPU(object):
    JITFRAME_FIXED_SIZE = 0

    def __init__(self):
        self.tracker = FakeTracker()
        self._cache = {}
        self.signedframedescr = ArrayDescr(3, 8, FieldDescr('len', 0, 0, 0), 0)
        self.floatframedescr = ArrayDescr(5, 8, FieldDescr('len', 0, 0, 0), 0)

    def getarraydescr_for_frame(self, tp):
        if tp == FLOAT:
            return self.floatframedescr
        return self.signedframedescr

    def unpack_arraydescr_size(self, d):
        return 0, d.itemsize, 0

    def unpack_fielddescr(self, d):
        return d.offset

    def arraydescrof(self, ARRAY):
        try:
            return self._cache[ARRAY]
        except KeyError:
            r = ArrayDescr(1, 2, FieldDescr('len', 0, 0, 0), 0)
            self._cache[ARRAY] = r
            return r

    def fielddescrof(self, STRUCT, fname):
        key = (STRUCT, fname)
        try:
            return self._cache[key]
        except KeyError:
            r = FieldDescr(fname, 1, 1, 1)
            self._cache[key] = r
            return r

class TestBoehm(RewriteTests):
    def setup_method(self, meth):
        class FakeCPU(BaseFakeCPU):
            def sizeof(self, STRUCT):
                return SizeDescrWithVTable(102, gc_fielddescrs=[])
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
            p0 = call_malloc_gc(ConstClass(malloc_array),   \
                                %(adescr.basesize)d,        \
                                10,                         \
                                %(adescr.itemsize)d,        \
                                %(adescr.lendescr.offset)d, \
                                descr=malloc_array_descr)
            jump()
        """)
##      should ideally be:
##            p0 = call_malloc_gc(ConstClass(malloc_fixedsize), \
##                                %(adescr.basesize + 10 * adescr.itemsize)d, \
##                                descr=malloc_fixedsize_descr)
##            setfield_gc(p0, 10, descr=alendescr)

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
            p0 = call_malloc_gc(ConstClass(malloc_array),   \
                                %(unicodedescr.basesize)d,  \
                                10,                         \
                                %(unicodedescr.itemsize)d,  \
                                %(unicodelendescr.offset)d, \
                                descr=malloc_array_descr)
            jump()
        """)
##      should ideally be:
##            p0 = call_malloc_gc(ConstClass(malloc_fixedsize),   \
##                                %(unicodedescr.basesize +       \
##                                  10 * unicodedescr.itemsize)d, \
##                                descr=malloc_fixedsize_descr)
##            setfield_gc(p0, 10, descr=unicodelendescr)


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
        self.gc_ll_descr.malloc_zero_filled = False
        #
        class FakeCPU(BaseFakeCPU):
            def sizeof(self, STRUCT):
                descr = SizeDescrWithVTable(104, gc_fielddescrs=[])
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
            [i0, p1]
            p0 = new_array(i0, descr=nonstd_descr)
            setarrayitem_gc(p0, i0, p1)
            jump(i0)
        """, """
            [i0, p1]
            p0 = call_malloc_gc(ConstClass(malloc_array_nonstandard), \
                                64, 8,                                \
                                %(nonstd_descr.lendescr.offset)d,     \
                                6464, i0,                             \
                                descr=malloc_array_nonstandard_descr)
            cond_call_gc_wb_array(p0, i0, descr=wbdescr)
            setarrayitem_gc(p0, i0, p1)
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
            p0 = call_malloc_gc(ConstClass(malloc_big_fixedsize), 104, 9315, \
                                descr=malloc_big_fixedsize_descr)
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
            setfield_gc(p0, 0, descr=strhashdescr)
            p1 = int_add(p0, %(strdescr.basesize + 16 * strdescr.itemsize)d)
            setfield_gc(p1, %(unicodedescr.tid)d, descr=tiddescr)
            setfield_gc(p1, 10, descr=unicodelendescr)
            setfield_gc(p1, 0, descr=unicodehashdescr)
            p2 = call_malloc_nursery_varsize(2, %(unicodedescr.itemsize)d, i2,\
                                descr=unicodedescr)
            setfield_gc(p2, i2, descr=unicodelendescr)
            setfield_gc(p2, 0, descr=unicodehashdescr)
            p3 = call_malloc_nursery_varsize(1, 1, i2, \
                                descr=strdescr)
            setfield_gc(p3, i2, descr=strlendescr)
            setfield_gc(p3, 0, descr=strhashdescr)
            jump()
        """)

    def test_write_barrier_before_setfield_gc(self):
        self.check_rewrite("""
            [p1, p2]
            setfield_gc(p1, p2, descr=tzdescr)
            jump()
        """, """
            [p1, p2]
            cond_call_gc_wb(p1, descr=wbdescr)
            setfield_gc(p1, p2, descr=tzdescr)
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
            cond_call_gc_wb(p1, descr=wbdescr)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """)

    def test_write_barrier_before_short_array(self):
        self.gc_ll_descr.max_size_of_young_obj = 2000
        self.check_rewrite("""
            [i2, p3]
            p1 = new_array_clear(129, descr=cdescr)
            call(123456)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """, """
            [i2, p3]
            p1 = call_malloc_nursery(    \
                                %(cdescr.basesize + 129 * cdescr.itemsize)d)
            setfield_gc(p1, 8111, descr=tiddescr)
            setfield_gc(p1, 129, descr=clendescr)
            zero_array(p1, 0, 129, descr=cdescr)
            call(123456)
            cond_call_gc_wb(p1, descr=wbdescr)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """)

    def test_write_barrier_before_long_array(self):
        # the limit of "being too long" is fixed, arbitrarily, at 130
        self.gc_ll_descr.max_size_of_young_obj = 2000
        self.check_rewrite("""
            [i2, p3]
            p1 = new_array_clear(130, descr=cdescr)
            call(123456)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """, """
            [i2, p3]
            p1 = call_malloc_nursery(    \
                                %(cdescr.basesize + 130 * cdescr.itemsize)d)
            setfield_gc(p1, 8111, descr=tiddescr)
            setfield_gc(p1, 130, descr=clendescr)
            zero_array(p1, 0, 130, descr=cdescr)
            call(123456)
            cond_call_gc_wb_array(p1, i2, descr=wbdescr)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """)

    def test_write_barrier_before_unknown_array(self):
        self.check_rewrite("""
            [p1, i2, p3]
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """, """
            [p1, i2, p3]
            cond_call_gc_wb_array(p1, i2, descr=wbdescr)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """)

    def test_label_makes_size_unknown(self):
        self.check_rewrite("""
            [i2, p3]
            p1 = new_array_clear(5, descr=cdescr)
            label(p1, i2, p3)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
            jump()
        """, """
            [i2, p3]
            p1 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p1, 8111, descr=tiddescr)
            setfield_gc(p1, 5, descr=clendescr)
            zero_array(p1, 0, 5, descr=cdescr)
            label(p1, i2, p3)
            cond_call_gc_wb_array(p1, i2, descr=wbdescr)
            setarrayitem_gc(p1, i2, p3, descr=cdescr)
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
            cond_call_gc_wb_array(p1, 0, descr=wbdescr)
            setinteriorfield_gc(p1, 0, p2, descr=interiorzdescr)
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
            p0 = new_array_clear(5, descr=cdescr)
            setarrayitem_gc(p0, i2, p1, descr=cdescr)
            jump()
        """, """
            [p1, i2]
            p0 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p0, 8111, descr=tiddescr)
            setfield_gc(p0, 5, descr=clendescr)
            zero_array(p0, 0, 5, descr=cdescr)
            setarrayitem_gc(p0, i2, p1, descr=cdescr)
            jump()
        """)

    def test_zero_array_reduced_left(self):
        self.check_rewrite("""
            [p1, p2]
            p0 = new_array_clear(5, descr=cdescr)
            setarrayitem_gc(p0, 1, p1, descr=cdescr)
            setarrayitem_gc(p0, 0, p2, descr=cdescr)
            jump()
        """, """
            [p1, p2]
            p0 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p0, 8111, descr=tiddescr)
            setfield_gc(p0, 5, descr=clendescr)
            zero_array(p0, 2, 3, descr=cdescr)
            setarrayitem_gc(p0, 1, p1, descr=cdescr)
            setarrayitem_gc(p0, 0, p2, descr=cdescr)
            jump()
        """)

    def test_zero_array_reduced_right(self):
        self.check_rewrite("""
            [p1, p2]
            p0 = new_array_clear(5, descr=cdescr)
            setarrayitem_gc(p0, 3, p1, descr=cdescr)
            setarrayitem_gc(p0, 4, p2, descr=cdescr)
            jump()
        """, """
            [p1, p2]
            p0 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p0, 8111, descr=tiddescr)
            setfield_gc(p0, 5, descr=clendescr)
            zero_array(p0, 0, 3, descr=cdescr)
            setarrayitem_gc(p0, 3, p1, descr=cdescr)
            setarrayitem_gc(p0, 4, p2, descr=cdescr)
            jump()
        """)

    def test_zero_array_not_reduced_at_all(self):
        self.check_rewrite("""
            [p1, p2]
            p0 = new_array_clear(5, descr=cdescr)
            setarrayitem_gc(p0, 3, p1, descr=cdescr)
            setarrayitem_gc(p0, 2, p2, descr=cdescr)
            setarrayitem_gc(p0, 1, p2, descr=cdescr)
            jump()
        """, """
            [p1, p2]
            p0 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p0, 8111, descr=tiddescr)
            setfield_gc(p0, 5, descr=clendescr)
            zero_array(p0, 0, 5, descr=cdescr)
            setarrayitem_gc(p0, 3, p1, descr=cdescr)
            setarrayitem_gc(p0, 2, p2, descr=cdescr)
            setarrayitem_gc(p0, 1, p2, descr=cdescr)
            jump()
        """)

    def test_zero_array_reduced_completely(self):
        self.check_rewrite("""
            [p1, p2]
            p0 = new_array_clear(5, descr=cdescr)
            setarrayitem_gc(p0, 3, p1, descr=cdescr)
            setarrayitem_gc(p0, 4, p2, descr=cdescr)
            setarrayitem_gc(p0, 0, p1, descr=cdescr)
            setarrayitem_gc(p0, 2, p2, descr=cdescr)
            setarrayitem_gc(p0, 1, p2, descr=cdescr)
            jump()
        """, """
            [p1, p2]
            p0 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p0, 8111, descr=tiddescr)
            setfield_gc(p0, 5, descr=clendescr)
            zero_array(p0, 5, 0, descr=cdescr)
            setarrayitem_gc(p0, 3, p1, descr=cdescr)
            setarrayitem_gc(p0, 4, p2, descr=cdescr)
            setarrayitem_gc(p0, 0, p1, descr=cdescr)
            setarrayitem_gc(p0, 2, p2, descr=cdescr)
            setarrayitem_gc(p0, 1, p2, descr=cdescr)
            jump()
        """)

    def test_zero_array_reduced_left_with_call(self):
        self.check_rewrite("""
            [p1, p2]
            p0 = new_array_clear(5, descr=cdescr)
            setarrayitem_gc(p0, 0, p1, descr=cdescr)
            call(321321)
            setarrayitem_gc(p0, 1, p2, descr=cdescr)
            jump()
        """, """
            [p1, p2]
            p0 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p0, 8111, descr=tiddescr)
            setfield_gc(p0, 5, descr=clendescr)
            zero_array(p0, 1, 4, descr=cdescr)
            setarrayitem_gc(p0, 0, p1, descr=cdescr)
            call(321321)
            cond_call_gc_wb(p0, descr=wbdescr)
            setarrayitem_gc(p0, 1, p2, descr=cdescr)
            jump()
        """)

    def test_zero_array_reduced_left_with_label(self):
        self.check_rewrite("""
            [p1, p2]
            p0 = new_array_clear(5, descr=cdescr)
            setarrayitem_gc(p0, 0, p1, descr=cdescr)
            label(p0, p2)
            setarrayitem_gc(p0, 1, p2, descr=cdescr)
            jump()
        """, """
            [p1, p2]
            p0 = call_malloc_nursery(    \
                                %(cdescr.basesize + 5 * cdescr.itemsize)d)
            setfield_gc(p0, 8111, descr=tiddescr)
            setfield_gc(p0, 5, descr=clendescr)
            zero_array(p0, 1, 4, descr=cdescr)
            setarrayitem_gc(p0, 0, p1, descr=cdescr)
            label(p0, p2)
            cond_call_gc_wb_array(p0, 1, descr=wbdescr)
            setarrayitem_gc(p0, 1, p2, descr=cdescr)
            jump()
        """)

    def test_zero_array_varsize(self):
        self.check_rewrite("""
            [p1, p2, i3]
            p0 = new_array_clear(i3, descr=bdescr)
            jump()
        """, """
            [p1, p2, i3]
            p0 = call_malloc_nursery_varsize(0, 1, i3, descr=bdescr)
            setfield_gc(p0, i3, descr=blendescr)
            zero_array(p0, 0, i3, descr=bdescr)
            jump()
        """)

    def test_zero_array_varsize_cannot_reduce(self):
        self.check_rewrite("""
            [p1, p2, i3]
            p0 = new_array_clear(i3, descr=bdescr)
            setarrayitem_gc(p0, 0, p1, descr=bdescr)
            jump()
        """, """
            [p1, p2, i3]
            p0 = call_malloc_nursery_varsize(0, 1, i3, descr=bdescr)
            setfield_gc(p0, i3, descr=blendescr)
            zero_array(p0, 0, i3, descr=bdescr)
            cond_call_gc_wb_array(p0, 0, descr=wbdescr)
            setarrayitem_gc(p0, 0, p1, descr=bdescr)
            jump()
        """)

    def test_initialization_store_potentially_large_array(self):
        # the write barrier cannot be omitted, because we might get
        # an array with cards and the GC assumes that the write
        # barrier is always called, even on young (but large) arrays
        self.check_rewrite("""
            [i0, p1, i2]
            p0 = new_array(i0, descr=bdescr)
            setarrayitem_gc(p0, i2, p1, descr=bdescr)
            jump()
        """, """
            [i0, p1, i2]
            p0 = call_malloc_nursery_varsize(0, 1, i0, descr=bdescr)
            setfield_gc(p0, i0, descr=blendescr)
            cond_call_gc_wb_array(p0, i2, descr=wbdescr)
            setarrayitem_gc(p0, i2, p1, descr=bdescr)
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
            zero_ptr_field(p0, %(tdescr.gc_fielddescrs[0].offset)s)
            p1 = call_malloc_nursery_varsize(1, 1, i0, \
                                descr=strdescr)
            setfield_gc(p1, i0, descr=strlendescr)
            setfield_gc(p1, 0, descr=strhashdescr)
            cond_call_gc_wb(p0, descr=wbdescr)
            setfield_gc(p0, p1, descr=tzdescr)
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
            zero_ptr_field(p0, %(tdescr.gc_fielddescrs[0].offset)s)
            label(p0, p1)
            cond_call_gc_wb(p0, descr=wbdescr)
            setfield_gc(p0, p1, descr=tzdescr)
            jump()
        """)

    def test_multiple_writes(self):
        self.check_rewrite("""
            [p0, p1, p2]
            setfield_gc(p0, p1, descr=tzdescr)
            setfield_gc(p0, p2, descr=tzdescr)
            jump(p1, p2, p0)
        """, """
            [p0, p1, p2]
            cond_call_gc_wb(p0, descr=wbdescr)
            setfield_gc(p0, p1, descr=tzdescr)
            setfield_gc(p0, p2, descr=tzdescr)
            jump(p1, p2, p0)
        """)

    def test_rewrite_call_assembler(self):
        self.check_rewrite("""
        [i0, f0]
        i2 = call_assembler(i0, f0, descr=casmdescr)
        """, """
        [i0, f0]
        i1 = getfield_raw(ConstClass(frame_info), descr=jfi_frame_size)
        p1 = call_malloc_nursery_varsize_frame(i1)
        setfield_gc(p1, 0, descr=tiddescr)
        i2 = getfield_raw(ConstClass(frame_info), descr=jfi_frame_depth)
        setfield_gc(p1, 0, descr=jf_extra_stack_depth)
        setfield_gc(p1, NULL, descr=jf_savedata)
        setfield_gc(p1, NULL, descr=jf_force_descr)
        setfield_gc(p1, NULL, descr=jf_descr)
        setfield_gc(p1, NULL, descr=jf_guard_exc)
        setfield_gc(p1, NULL, descr=jf_forward)
        setfield_gc(p1, i2, descr=framelendescr)
        setfield_gc(p1, ConstClass(frame_info), descr=jf_frame_info)
        setarrayitem_gc(p1, 0, i0, descr=signedframedescr)
        setarrayitem_gc(p1, 1, f0, descr=floatframedescr)
        i3 = call_assembler(p1, descr=casmdescr)
        """)

    def test_int_add_ovf(self):
        self.check_rewrite("""
            [i0]
            p0 = new(descr=tdescr)
            i1 = int_add_ovf(i0, 123)
            guard_overflow(descr=guarddescr) []
            jump()
        """, """
            [i0]
            p0 = call_malloc_nursery(%(tdescr.size)d)
            setfield_gc(p0, 5678, descr=tiddescr)
            zero_ptr_field(p0, %(tdescr.gc_fielddescrs[0].offset)s)
            i1 = int_add_ovf(i0, 123)
            guard_overflow(descr=guarddescr) []
            jump()
        """)

    def test_int_gt(self):
        self.check_rewrite("""
            [i0]
            p0 = new(descr=tdescr)
            i1 = int_gt(i0, 123)
            guard_false(i1, descr=guarddescr) []
            jump()
        """, """
            [i0]
            p0 = call_malloc_nursery(%(tdescr.size)d)
            setfield_gc(p0, 5678, descr=tiddescr)
            zero_ptr_field(p0, %(tdescr.gc_fielddescrs[0].offset)s)
            i1 = int_gt(i0, 123)
            guard_false(i1, descr=guarddescr) []
            jump()
        """)

    def test_zero_ptr_field_before_getfield(self):
        # This case may need to be fixed in the metainterp/optimizeopt
        # already so that it no longer occurs for rewrite.py.  But anyway
        # it's a good idea to make sure rewrite.py is correct on its own.
        self.check_rewrite("""
            []
            p0 = new(descr=tdescr)
            p1 = getfield_gc(p0, descr=tdescr)
            jump(p1)
        """, """
            []
            p0 = call_malloc_nursery(%(tdescr.size)d)
            setfield_gc(p0, 5678, descr=tiddescr)
            zero_ptr_field(p0, %(tdescr.gc_fielddescrs[0].offset)s)
            p1 = getfield_gc(p0, descr=tdescr)
            jump(p1)
        """)
