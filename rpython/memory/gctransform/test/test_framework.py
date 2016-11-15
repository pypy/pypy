from rpython.annotator.listdef import s_list_of_strings
from rpython.annotator.model import SomeInteger
from rpython.flowspace.model import Constant, SpaceOperation, mkentrymap
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.memory.gc.semispace import SemiSpaceGC
from rpython.memory.gctransform.framework import (
    CollectAnalyzer, WriteBarrierCollector,
    find_initializing_stores, find_clean_setarrayitems)
from rpython.memory.gctransform.shadowstack import (
     ShadowStackFrameworkGCTransformer)
from rpython.memory.gctransform.test.test_transform import rtype
from rpython.memory.gctransform.transform import GcHighLevelOp
from rpython.rtyper.rtyper import LowLevelOpList
from rpython.translator.backendopt.all import backend_optimizations
from rpython.translator.c.gc import BasicFrameworkGcPolicy, StmFrameworkGcPolicy
from rpython.translator.exceptiontransform import ExceptionTransformer
from rpython.translator.translator import TranslationContext, graphof
from rpython.translator.unsimplify import varoftype

import py
import pytest

class FrameworkGcPolicy2(BasicFrameworkGcPolicy):
    class transformerclass(ShadowStackFrameworkGCTransformer):
        root_stack_depth = 100

def test_framework_simple(gc="minimark"):
    def g(x):
        return x + 1
    class A(object):
        pass
    def entrypoint(argv):
        a = A()
        a.b = g(1)
        return a.b

    from rpython.rtyper.llinterp import LLInterpreter
    from rpython.translator.c.genc import CStandaloneBuilder

    t = rtype(entrypoint, [s_list_of_strings])
    if gc == "stmgc":
        t.config.translation.stm = True
        gcpolicy = StmFrameworkGcPolicy
    else:
        gcpolicy = FrameworkGcPolicy2
    t.config.translation.gc = gc

    cbuild = CStandaloneBuilder(t, entrypoint, t.config,
                                gcpolicy=gcpolicy)
    cbuild.make_entrypoint_wrapper = False
    db = cbuild.build_database()
    entrypointptr = cbuild.getentrypointptr()
    entrygraph = entrypointptr._obj.graph

    llinterp = LLInterpreter(t.rtyper)

    # FIIIIISH
    setupgraph = db.gctransformer.frameworkgc_setup_ptr.value._obj.graph
    llinterp.eval_graph(setupgraph, [])

    res = llinterp.eval_entry_point(entrygraph, [])

    assert res == 2

@pytest.mark.xfail(reason="llinterp does not implement stm_allocate_tid")
def test_framework_simple_stm():
    test_framework_simple("stmgc")

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

def test_no_collect(gc="minimark"):
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
    if gc == "stmgc":
        t.config.translation.stm = True
        gcpolicy = StmFrameworkGcPolicy
    else:
        gcpolicy = FrameworkGcPolicy2
    t.config.translation.gc = gc
    cbuild = CStandaloneBuilder(t, entrypoint, t.config,
                                gcpolicy=gcpolicy)
    cbuild.make_entrypoint_wrapper = False
    db = cbuild.build_database()

def test_no_collect_stm():
    test_no_collect("stmgc")

def test_no_collect_detection(gc="minimark"):
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
    if gc == "stmgc":
        t.config.translation.stm = True
        gcpolicy = StmFrameworkGcPolicy
    else:
        gcpolicy = FrameworkGcPolicy2
    t.config.translation.gc = gc
    cbuild = CStandaloneBuilder(t, entrypoint, t.config,
                                gcpolicy=gcpolicy)
    cbuild.make_entrypoint_wrapper = False
    with py.test.raises(Exception) as f:
        cbuild.build_database()
    expected = "'no_collect' function can trigger collection: <function g at "
    assert str(f.value).startswith(expected)

def test_no_collect_detection_stm():
    test_no_collect_detection("stmgc")

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

def test_remove_duplicate_write_barrier(gc="minimark"):
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
    def g(argv):
        f(glob_a_1, 5)
        f(glob_a_2, 0)
        return 0
    t = rtype(g, [s_list_of_strings])
    if gc == "stmgc":
        t.config.translation.stm = True
        gcpolicy = StmFrameworkGcPolicy
    else:
        gcpolicy = FrameworkGcPolicy2
    t.config.translation.gc = gc
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=gcpolicy)
    cbuild.make_entrypoint_wrapper = False
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    if gc == "stmgc":
        assert summary(ff)['stm_write'] == 1
    else:
        assert summary(ff)['direct_call'] == 1    # only one remember_young_pointer

def test_remove_duplicate_write_barrier_stm():
    test_remove_duplicate_write_barrier("stmgc")

def test_remove_write_barrier_stm():
    from rpython.translator.c.genc import CStandaloneBuilder
    from rpython.flowspace.model import summary

    class A: pass
    glob = A()
    glob2 = A()
    def f(n, g, g2):
        i = 0
        llop.gc_writebarrier(lltype.Void, g2)
        g.a = n # WB
        while i < n:
            g.a = i
            g2.a = i
            i += 1
    def g(argv):
        if argv[1]:
            f(int(argv[1]), glob, glob2)
        else:
            f(int(argv[1]), glob2, glob)
        return 0

    t = rtype(g, [s_list_of_strings])
    t.config.translation.stm = True
    gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=gcpolicy)
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    assert summary(ff)['stm_write'] == 2

def test_remove_write_barrier_stm2():
    from rpython.translator.c.genc import CStandaloneBuilder
    from rpython.flowspace.model import summary
    from rpython.rlib.objectmodel import stm_ignored

    class A: pass
    glob = A()
    glob2 = A()
    def f(n, g, g2):
        i = 1
        while n:
            g.a = i # WB
            with stm_ignored:
                g2.a = i
    def g(argv):
        if argv[1]:
            f(int(argv[1]), glob, glob2)
        else:
            f(int(argv[1]), glob2, glob)
        return 0

    t = rtype(g, [s_list_of_strings])
    t.config.translation.stm = True
    gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=gcpolicy)
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    assert summary(ff)['stm_write'] == 1

def test_remove_write_barrier_stm3():
    from rpython.translator.c.genc import CStandaloneBuilder
    from rpython.flowspace.model import summary

    S = lltype.GcStruct('S')
    A = lltype.GcArray(lltype.Ptr(S))
    def f(l, l2, i):
        s = lltype.malloc(S)
        llop.gc_writebarrier(lltype.Void, l2)
        while i:
            l[i] = s # WB card
            l[i] = s # WB card
            l2[i] = s # no WB
    def g(argv):
        n = int(argv[1])
        l = lltype.malloc(A, n)
        l[0] = lltype.malloc(S)
        l[1] = lltype.malloc(S)
        l[2] = lltype.malloc(S)
        f(l, l, n)
        return 0
    t = rtype(g, [s_list_of_strings])
    t.config.translation.stm = True
    gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=gcpolicy)
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    assert summary(ff)['stm_write'] == 3


def test_remove_write_barrier_stm4():
    from rpython.translator.c.genc import CStandaloneBuilder
    from rpython.flowspace.model import summary

    rS = lltype.Struct('rS')
    S = lltype.GcStruct('S')
    rA = lltype.Array(lltype.Ptr(rS))
    A = lltype.GcArray(lltype.Ptr(S))
    Ar = lltype.GcArray(lltype.Ptr(rS))
    def f(ra, a, ar, i):
        s = lltype.malloc(S)
        rs = lltype.malloc(rS, flavor='raw')
        ra[0] = rs
        ra[1] = rs
        a[0] = s
        a[1] = s
        ar[0] = rs
        ar[1] = rs
    def g(argv):
        n = int(argv[1])
        ra = lltype.malloc(rA, n, flavor='raw')
        a = lltype.malloc(A, n)
        ar = lltype.malloc(Ar, n)
        f(ra, a, ar, n)
        return 0
    t = rtype(g, [s_list_of_strings])
    t.config.translation.stm = True
    gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=gcpolicy)
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    assert summary(ff)['stm_write'] == 4

def test_remove_write_barrier_stm5():
    from rpython.translator.c.genc import CStandaloneBuilder
    from rpython.flowspace.model import summary

    class B(object):
        def __del__(self):
            pass
    class A(object): pass
    def f():
        b = B()
        b.x = 1 # needs WB bc. of finalizer
        a = A()
        a.x = 1
    def g(argv):
        f()
        return 0
    t = rtype(g, [s_list_of_strings])
    t.config.translation.stm = True
    gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=gcpolicy)
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    assert summary(ff)['stm_write'] == 1

def test_remove_write_barrier_stm6():
    from rpython.translator.c.genc import CStandaloneBuilder
    from rpython.flowspace.model import summary
    #
    rSi = lltype.Struct('rSi', ('i', lltype.Signed))
    rSr = lltype.Struct('rSr', ('s', lltype.Ptr(rSi)))
    Si = lltype.GcStruct('Si', ('i', lltype.Signed))
    Ss = lltype.GcStruct('Ss', ('s', lltype.Ptr(Si)))
    Sr = lltype.GcStruct('Sr', ('r', lltype.Ptr(rSi)))
    def f(rsi, rsr, si, ss, sr):
        rsi.i = 0
        rsr.s = rsi
        si.i = 0
        ss.s = si
        sr.r = rsi
    def g(argv):
        rsi = lltype.malloc(rSi, flavor='raw')
        rsr = lltype.malloc(rSr, flavor='raw')
        si = lltype.malloc(Si, flavor='gc')
        ss = lltype.malloc(Ss, flavor='gc')
        sr = lltype.malloc(Sr, flavor='gc')
        f(rsi, rsr, si, ss, sr)
        return 0
    t = rtype(g, [s_list_of_strings])
    t.config.translation.stm = True
    gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=gcpolicy)
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    assert summary(ff)['stm_write'] == 3

def test_remove_write_barrier_stm7():
    from rpython.translator.c.genc import CStandaloneBuilder
    from rpython.flowspace.model import summary
    #
    rSi = lltype.Struct('rSi', ('i', lltype.Signed))
    rSr = lltype.Struct('rSr', ('s', rSi))
    Si = lltype.GcStruct('Si', ('i', lltype.Signed))
    Ss = lltype.GcStruct('Ss', ('s', Si))
    Sr = lltype.GcStruct('Sr', ('r', rSi))
    def f(rsi, rsr, si, ss, sr):
        rsi.i = 0
        rsr.s.i = 0
        si.i = 0
        ss.s.i = 0
        sr.r.i = 0
    def g(argv):
        rsi = lltype.malloc(rSi, flavor='raw')
        rsr = lltype.malloc(rSr, flavor='raw')
        si = lltype.malloc(Si, flavor='gc')
        ss = lltype.malloc(Ss, flavor='gc')
        sr = lltype.malloc(Sr, flavor='gc')
        f(rsi, rsr, si, ss, sr)
        return 0
    t = rtype(g, [s_list_of_strings])
    t.config.translation.stm = True
    gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=gcpolicy)
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    assert summary(ff)['stm_write'] == 3

def test_no_wb_for_varsize_mallocs_stm():
    # AFAIK removing card barriers is only safe on STM!
    from rpython.translator.c.genc import CStandaloneBuilder
    from rpython.flowspace.model import summary

    A = lltype.GcArray(lltype.Signed)
    def f(i):
        s = lltype.malloc(A, i+1)
        s[i] = 4 # no card WB
        s[i] = 4 # no card WB
        lltype.malloc(A, 1)
        s[i] = 4 # card WB
        llop.gc_writebarrier(lltype.Void, s) # WB
        s[i] = 4 # no card WB
    def g(argv):
        n = int(argv[1])
        f(n)
        return 0
    t = rtype(g, [s_list_of_strings])
    t.config.translation.stm = True
    gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=gcpolicy)
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    assert summary(ff)['stm_write'] == 2

def test_write_barrier_collector():
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
    t.config.translation.stm = True
    #gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    etrafo = ExceptionTransformer(t)
    graphs = etrafo.transform_completely()
    collect_analyzer = CollectAnalyzer(t)

    wbc = WriteBarrierCollector(t.graphs[0], collect_analyzer)
    wbc.collect()
    print wbc.clean_ops
    assert len(wbc.clean_ops) == 4

def test_write_barrier_collector_across_blocks():
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
    t.config.translation.stm = True
    #gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    etrafo = ExceptionTransformer(t)
    graphs = etrafo.transform_completely()
    collect_analyzer = CollectAnalyzer(t)

    wbc = WriteBarrierCollector(t.graphs[0], collect_analyzer)
    wbc.collect()
    print "\n".join(map(str,wbc.clean_ops))
    assert len(wbc.clean_ops) == 9

def test_write_barrier_collector_blocks_merging():
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
            a.c = a2 # WB
        b.c = a1
        a.c = a1 # WB
        a.b = a2
    t = rtype(f, [int])
    t.config.translation.stm = True
    #gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    etrafo = ExceptionTransformer(t)
    graphs = etrafo.transform_completely()
    collect_analyzer = CollectAnalyzer(t)

    wbc = WriteBarrierCollector(t.graphs[0], collect_analyzer)
    wbc.collect()
    print "\n".join(map(str,wbc.clean_ops))
    assert len(wbc.clean_ops) == 11

def test_write_barrier_collector_stm_inevitable_interaction():
    from rpython.translator.c.genc import CStandaloneBuilder
    from rpython.flowspace.model import summary
    from rpython.rlib import rstm
    #
    S = lltype.GcStruct('S', ('i', lltype.Signed))
    def f():
        s = lltype.malloc(S, flavor='gc')
        rstm.become_inevitable()
        s.i = 6 # become_inevitable canmalloc -> needs WB
    def g(argv):
        f()
        return 0
    t = rtype(g, [s_list_of_strings])
    t.config.translation.stm = True
    gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    cbuild = CStandaloneBuilder(t, g, t.config,
                                gcpolicy=gcpolicy)
    db = cbuild.build_database()

    ff = graphof(t, f)
    #ff.show()
    assert summary(ff)['stm_write'] == 1



def test_write_barrier_collector_loops():
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
        while x:
            b.b = a1
            a.c = a2
        b.c = a1
        a.c = a1
    t = rtype(f, [int])
    t.config.translation.stm = True
    #gcpolicy = StmFrameworkGcPolicy
    t.config.translation.gc = "stmgc"
    etrafo = ExceptionTransformer(t)
    graphs = etrafo.transform_completely()
    collect_analyzer = CollectAnalyzer(t)

    wbc = WriteBarrierCollector(t.graphs[0], collect_analyzer)
    wbc.collect()
    print "\n".join(map(str,wbc.clean_ops))
    assert len(wbc.clean_ops) == 7



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
