from rpython.annotator.listdef import s_list_of_strings
from rpython.annotator.model import SomeInteger
from rpython.flowspace.model import Constant, SpaceOperation, mkentrymap
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.objectmodel import always_inline
from rpython.memory.gc.semispace import SemiSpaceGC
from rpython.memory.gctransform.framework import (CollectAnalyzer,
     find_initializing_stores, find_clean_setarrayitems)
from rpython.memory.gctransform.shadowstack import (
     ShadowStackFrameworkGCTransformer)
from rpython.memory.gctransform.test.test_transform import rtype
from rpython.memory.gctransform.transform import GcHighLevelOp
from rpython.rtyper.rtyper import LowLevelOpList
from rpython.translator.backendopt.all import backend_optimizations
from rpython.translator.c.gc import BasicFrameworkGcPolicy
from rpython.translator.exceptiontransform import ExceptionTransformer
from rpython.translator.translator import TranslationContext, graphof
from rpython.translator.unsimplify import varoftype

import py

class FrameworkGcPolicy2(BasicFrameworkGcPolicy):
    class transformerclass(ShadowStackFrameworkGCTransformer):
        root_stack_depth = 100

def test_framework_simple():
    def g(x):
        return x + 1
    class A(object):
        pass
    def entrypoint(argv):
        a = A()
        a.b = g(1)
        return str(a.b)

    from rpython.rtyper.llinterp import LLInterpreter
    from rpython.translator.c.genc import CStandaloneBuilder

    t = rtype(entrypoint, [s_list_of_strings])
    t.config.translation.gc = "minimark"
    cbuild = CStandaloneBuilder(t, entrypoint, t.config,
                                gcpolicy=FrameworkGcPolicy2)
    cbuild.make_entrypoint_wrapper = False
    db = cbuild.build_database()
    entrypointptr = cbuild.getentrypointptr()
    entrygraph = entrypointptr._obj.graph

    r_list_of_strings = t.rtyper.getrepr(s_list_of_strings)
    ll_argv = r_list_of_strings.convert_const([])

    llinterp = LLInterpreter(t.rtyper)

    # FIIIIISH
    setupgraph = db.gctransformer.frameworkgc_setup_ptr.value._obj.graph
    llinterp.eval_graph(setupgraph, [])

    res = llinterp.eval_graph(entrygraph, [ll_argv])

    assert ''.join(res.chars) == "2"

def test_cancollect():
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    def g():
        lltype.malloc(S, zero=True)
    t = rtype(g, [])
    gg = graphof(t, g)
    assert CollectAnalyzer(t).analyze_direct_call(gg)

    def g(x):
        return -x
    t = rtype(g, [int])
    gg = graphof(t, g)
    assert not CollectAnalyzer(t).analyze_direct_call(gg)

def test_cancollect_external():
    fext1 = rffi.llexternal('fext1', [], lltype.Void, releasegil=False)
    def g():
        fext1()
    t = rtype(g, [])
    gg = graphof(t, g)
    assert not CollectAnalyzer(t).analyze_direct_call(gg)

    fext2 = rffi.llexternal('fext2', [], lltype.Void, releasegil=True)
    def g():
        fext2()
    t = rtype(g, [])
    gg = graphof(t, g)
    assert CollectAnalyzer(t).analyze_direct_call(gg)

    S = lltype.GcStruct('S', ('x', lltype.Signed))
    FUNC = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Void))
    fext3 = rffi.llexternal('fext3', [FUNC], lltype.Void, releasegil=False)
    def h(x):
        lltype.malloc(S, zero=True)
    def g():
        fext3(h)
    t = rtype(g, [])
    gg = graphof(t, g)
    assert CollectAnalyzer(t).analyze_direct_call(gg)

def test_no_collect():
    from rpython.rlib import rgc
    from rpython.translator.c.genc import CStandaloneBuilder

    @rgc.no_collect
    def g():
        return 1

    assert g._dont_inline_
    assert g._gc_no_collect_

    def entrypoint(argv):
        return g() + 2

    t = rtype(entrypoint, [s_list_of_strings])
    t.config.translation.gc = "minimark"
    cbuild = CStandaloneBuilder(t, entrypoint, t.config,
                                gcpolicy=FrameworkGcPolicy2)
    cbuild.make_entrypoint_wrapper = False
    db = cbuild.build_database()

def test_no_collect_detection():
    from rpython.rlib import rgc
    from rpython.translator.c.genc import CStandaloneBuilder

    class A(object):
        def __init__(self, x):
            self.x = x

    @rgc.no_collect
    def g():
        return A(1).x

    assert g._dont_inline_
    assert g._gc_no_collect_

    def entrypoint(argv):
        return g() + 2

    t = rtype(entrypoint, [s_list_of_strings])
    t.config.translation.gc = "minimark"
    cbuild = CStandaloneBuilder(t, entrypoint, t.config,
                                gcpolicy=FrameworkGcPolicy2)
    cbuild.make_entrypoint_wrapper = False
    with py.test.raises(Exception) as f:
        cbuild.build_database()
    expected = "'no_collect' function can trigger collection: <function g at "
    assert str(f.value).startswith(expected)

def test_cast_no_collect():
    # mimic some of the behaviour of _siphash24
    from rpython.rlib import rgc
    from rpython.rlib.rarithmetic import r_uint64, r_uint32
    from rpython.translator.c.genc import CStandaloneBuilder

    @always_inline
    def _rotate(x, b):
        return (x << b) | (x >> (64 - b))

    @always_inline
    def _half_round(a, b, c, d, s, t):
        a += b
        c += d
        b = _rotate(b, s) ^ a
        d = _rotate(d, t) ^ c
        a = _rotate(a, 32)
        return a, b, c, d

    @always_inline
    def _double_round(v0, v1, v2, v3):
        v0,v1,v2,v3 = _half_round(v0,v1,v2,v3,13,16)
        v2,v1,v0,v3 = _half_round(v2,v1,v0,v3,17,21)
        v0,v1,v2,v3 = _half_round(v0,v1,v2,v3,13,16)
        v2,v1,v0,v3 = _half_round(v2,v1,v0,v3,17,21)
        return v0, v1, v2, v3

    @rgc.no_collect
    def _siphash24(addr_in, size, SZ=1):
        index = 0
        v0 =  r_uint64(0x736f6d6570736575)
        v1 =  r_uint64(0x646f72616e646f6d)
        v2 =  r_uint64(0x6c7967656e657261)
        v3 =  r_uint64(0x7465646279746573)

        b = r_uint64(size) << 56
        while size >= 8:
            mi = (
              r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index)) |
              r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 1*SZ)) << 8 |
              r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 2*SZ)) << 16 |
              r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 3*SZ)) << 24 |
              r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 4*SZ)) << 32 |
              r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 5*SZ)) << 40 |
              r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 6*SZ)) << 48 |
              r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 7*SZ)) << 56
            )
            size -= 8
            index += 8*SZ
            v3 ^= mi
            v0, v1, v2, v3 = _double_round(v0, v1, v2, v3)
            v0 ^= mi

        t = r_uint64(0)
        if size == 7:
            t = r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 6*SZ)) << 48
            size = 6
        if size == 6:
            t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 5*SZ)) << 40
            size = 5
        if size == 5:
            t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 4*SZ)) << 32
            size = 4
        if size == 4:
            t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 3*SZ))<< 24
            size = 3
        if size == 3:
            t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 2*SZ)) << 16
            size = 2
        if size == 2:
            t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index + 1*SZ)) << 8
            size = 1
        if size == 1:
            t |= r_uint64(llop.raw_load(rffi.UCHAR, addr_in, index))
            size = 0
        assert size == 0

        b |= t

        v3 ^= b
        v0, v1, v2, v3 = _double_round(v0, v1, v2, v3)
        v0 ^= b
        v2 ^= 0xff
        v0, v1, v2, v3 = _double_round(v0, v1, v2, v3)
        v0, v1, v2, v3 = _double_round(v0, v1, v2, v3)

        return (v0 ^ v1) ^ (v2 ^ v3)

    def siphash24(s):
        """'s' is a normal string.  Returns its siphash-2-4 as a r_uint64.
        Don't forget to cast the result to a regular integer if needed,
        e.g. with rarithmetic.intmask().
        """
        with rffi.scoped_nonmovingbuffer(s) as p:
            return _siphash24(llmemory.cast_ptr_to_adr(p), len(s))

    def entrypoint(argv):
        return siphash24('abc')

    t = rtype(entrypoint, [s_list_of_strings])
    t.config.translation.gc = "minimark"
    cbuild = CStandaloneBuilder(t, entrypoint, t.config,
                                gcpolicy=FrameworkGcPolicy2)
    cbuild.make_entrypoint_wrapper = False
    with py.test.raises(Exception) as f:
        cbuild.build_database()
    expected = "'no_collect' function can trigger collection: <function _siphash24 at "
    assert str(f.value).startswith(expected)

def test_custom_trace_function_no_collect():
    from rpython.rlib import rgc
    from rpython.translator.c.genc import CStandaloneBuilder

    S = lltype.GcStruct("MyStructure")
    class Glob:
        pass
    glob = Glob()
    def trace_func(gc, obj, callback, arg):
        glob.foo = (gc, obj)
    lambda_trace_func = lambda: trace_func
    def entrypoint(argv):
        lltype.malloc(S)
        rgc.register_custom_trace_hook(S, lambda_trace_func)
        return 0

    t = rtype(entrypoint, [s_list_of_strings])
    t.config.translation.gc = "minimark"
    cbuild = CStandaloneBuilder(t, entrypoint, t.config,
                                gcpolicy=FrameworkGcPolicy2)
    cbuild.make_entrypoint_wrapper = False
    with py.test.raises(Exception) as f:
        cbuild.build_database()
    assert 'can cause the GC to be called' in str(f.value)
    assert 'trace_func' in str(f.value)
    assert 'MyStructure' in str(f.value)

class WriteBarrierTransformer(ShadowStackFrameworkGCTransformer):
    clean_sets = {}
    GC_PARAMS = {}
    class GCClass(SemiSpaceGC):
        needs_write_barrier = True
        def writebarrier_before_copy(self, source, dest,
                                     source_start, dest_start, length):
            return True

def write_barrier_check(spaceop, needs_write_barrier=True):
    t = TranslationContext()
    t.buildannotator().build_types(lambda x:x, [SomeInteger()])
    t.buildrtyper().specialize()
    transformer = WriteBarrierTransformer(t)
    llops = LowLevelOpList()
    hop = GcHighLevelOp(transformer, spaceop, 0, llops)
    hop.dispatch()
    found = False
    print spaceop, '======>'
    for op in llops:
        print '\t', op
        if op.opname == 'direct_call':
            found = True
    assert found == needs_write_barrier

def test_write_barrier_support_setfield():
    PTR_TYPE2 = lltype.Ptr(lltype.GcStruct('T', ('y', lltype.Signed)))
    PTR_TYPE = lltype.Ptr(lltype.GcStruct('S', ('x', PTR_TYPE2)))
    write_barrier_check(SpaceOperation(
        "setfield",
        [varoftype(PTR_TYPE), Constant('x', lltype.Void),
         varoftype(PTR_TYPE2)],
        varoftype(lltype.Void)))


def test_dont_add_write_barrier_for_constant_new_value():
    PTR_TYPE2 = lltype.Ptr(lltype.GcStruct('T', ('y', lltype.Signed)))
    PTR_TYPE = lltype.Ptr(lltype.GcStruct('S', ('x', PTR_TYPE2)))
    write_barrier_check(SpaceOperation(
        "setfield",
        [varoftype(PTR_TYPE), Constant('x', lltype.Void),
         Constant('foo', varoftype(PTR_TYPE2))],
        varoftype(lltype.Void)), needs_write_barrier=False)

def test_write_barrier_support_setarrayitem():
    PTR_TYPE2 = lltype.Ptr(lltype.GcStruct('T', ('y', lltype.Signed)))
    ARRAYPTR = lltype.Ptr(lltype.GcArray(PTR_TYPE2))
    write_barrier_check(SpaceOperation(
        "setarrayitem",
        [varoftype(ARRAYPTR), varoftype(lltype.Signed),
         varoftype(PTR_TYPE2)],
        varoftype(lltype.Void)))

def test_write_barrier_support_setinteriorfield():
    PTR_TYPE2 = lltype.Ptr(lltype.GcStruct('T', ('y', lltype.Signed)))
    ARRAYPTR2 = lltype.Ptr(lltype.GcArray(('a', lltype.Signed),
                                          ('b', PTR_TYPE2)))
    write_barrier_check(SpaceOperation(
        "setinteriorfield",
        [varoftype(ARRAYPTR2), varoftype(lltype.Signed),
         Constant('b', lltype.Void), varoftype(PTR_TYPE2)],
        varoftype(lltype.Void)))

def test_remove_duplicate_write_barrier():
    from rpython.translator.c.genc import CStandaloneBuilder
    from rpython.flowspace.model import summary

    class A(object):
        pass
    glob_a_1 = A()
    glob_a_2 = A()

    def f(a, cond):
        a.x = a
        a.z = a
        if cond:
            a.y = a
    def g():
        f(glob_a_1, 5)
        f(glob_a_2, 0)
    t = rtype(g, [])
    t.config.translation.gc = "minimark"
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=FrameworkGcPolicy2)
    cbuild.make_entrypoint_wrapper = False
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    assert summary(ff)['direct_call'] == 1    # only one remember_young_pointer

def test_find_initializing_stores():

    class A(object):
        pass
    class B(object):
        pass
    def f():
        a = A()
        b = B()
        b.a = a
        b.b = 1
    t = rtype(f, [])
    etrafo = ExceptionTransformer(t)
    graphs = etrafo.transform_completely()
    collect_analyzer = CollectAnalyzer(t)
    init_stores = find_initializing_stores(collect_analyzer, t.graphs[0],
                                           mkentrymap(t.graphs[0]))
    assert len(init_stores) == 1

def test_find_initializing_stores_across_blocks():

    class A(object):
        pass
    class B(object):
        pass
    def f(x):
        a1 = A()
        a2 = A()
        a = A()
        b = B()
        b.a = a
        if x:
            b.b = a1
            b.c = a2
        else:
            b.c = a1
            b.b = a2
    t = rtype(f, [int])
    etrafo = ExceptionTransformer(t)
    graphs = etrafo.transform_completely()
    collect_analyzer = CollectAnalyzer(t)
    init_stores = find_initializing_stores(collect_analyzer, t.graphs[0],
                                           mkentrymap(t.graphs[0]))
    assert len(init_stores) == 5

def test_find_clean_setarrayitems():
    S = lltype.GcStruct('S')
    A = lltype.GcArray(lltype.Ptr(S))

    def f():
        l = lltype.malloc(A, 3)
        l[0] = lltype.malloc(S)
        l[1] = lltype.malloc(S)
        l[2] = lltype.malloc(S)
        x = l[1]
        l[0] = x
        return len(l)

    t = rtype(f, [])
    etrafo = ExceptionTransformer(t)
    graph = etrafo.transform_completely()
    collect_analyzer = CollectAnalyzer(t)
    clean_setarrayitems = find_clean_setarrayitems(collect_analyzer,
                                                   t.graphs[0])
    assert len(clean_setarrayitems) == 1

def test_find_clean_setarrayitems_2():
    S = lltype.GcStruct('S')
    A = lltype.GcArray(lltype.Ptr(S))

    def f():
        l = lltype.malloc(A, 3)
        l[0] = lltype.malloc(S)
        l[1] = lltype.malloc(S)
        l[2] = lltype.malloc(S)
        x = l[1]
        l[2] = lltype.malloc(S) # <- this can possibly collect
        l[0] = x
        return len(l)

    t = rtype(f, [])
    etrafo = ExceptionTransformer(t)
    graph = etrafo.transform_completely()
    collect_analyzer = CollectAnalyzer(t)
    clean_setarrayitems = find_clean_setarrayitems(collect_analyzer,
                                                   t.graphs[0])
    assert len(clean_setarrayitems) == 0

def test_find_clean_setarrayitems_3():
    S = lltype.GcStruct('S')
    A = lltype.GcArray(lltype.Ptr(S))

    def f():
        l = lltype.malloc(A, 3)
        l[0] = lltype.malloc(S)
        l[1] = lltype.malloc(S)
        l[2] = lltype.malloc(S)
        l2 = lltype.malloc(A, 4)
        x = l[1]
        l2[0] = x # <- different list
        return len(l)

    t = rtype(f, [])
    etrafo = ExceptionTransformer(t)
    graph = etrafo.transform_completely()
    collect_analyzer = CollectAnalyzer(t)
    clean_setarrayitems = find_clean_setarrayitems(collect_analyzer,
                                                   t.graphs[0])
    assert len(clean_setarrayitems) == 0

def test_list_operations():

    class A(object):
        pass

    def f():
        l = [A(), A()]
        l.append(A())
        l[1] = l[0]
        return len(l)

    t = rtype(f, [])
    backend_optimizations(t, clever_malloc_removal=False, storesink=True)
    etrafo = ExceptionTransformer(t)
    graph = etrafo.transform_completely()
    collect_analyzer = CollectAnalyzer(t)
    clean_setarrayitems = find_clean_setarrayitems(collect_analyzer,
                                                   t.graphs[0])
    assert len(clean_setarrayitems) == 1
