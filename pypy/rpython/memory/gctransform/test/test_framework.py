from pypy.objspace.flow.model import Constant, SpaceOperation
from pypy.annotation.model import SomeInteger
from pypy.rpython.memory.gc.marksweep import MarkSweepGC
from pypy.rpython.memory.gctransform.test.test_transform import rtype, \
    rtype_and_transform
from pypy.rpython.memory.gctransform.transform import GcHighLevelOp
from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer, \
    CollectAnalyzer, find_initializing_stores
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rtyper import LowLevelOpList
from pypy.translator.c.gc import FrameworkGcPolicy
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.unsimplify import varoftype
from pypy.translator.exceptiontransform import ExceptionTransformer
from pypy import conftest

import py

class FrameworkGcPolicy2(FrameworkGcPolicy):
    class transformerclass(FrameworkGCTransformer):
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

    from pypy.rpython.llinterp import LLInterpreter
    from pypy.translator.c.genc import CStandaloneBuilder
    from pypy.translator.c import gc
    from pypy.annotation.listdef import s_list_of_strings

    t = rtype(entrypoint, [s_list_of_strings])
    cbuild = CStandaloneBuilder(t, entrypoint, t.config,
                                gcpolicy=FrameworkGcPolicy2)
    db = cbuild.generate_graphs_for_llinterp()
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

def test_cancollect_stack_check():
    from pypy.rlib import rstack

    def with_check():
        rstack.stack_check()

    t = rtype(with_check, [])
    with_check_graph = graphof(t, with_check)

    assert not t.config.translation.stackless
    can_collect = CollectAnalyzer(t).analyze_direct_call(with_check_graph)
    assert not can_collect
    
    t.config.translation.stackless = True
    can_collect = CollectAnalyzer(t).analyze_direct_call(with_check_graph)
    assert can_collect

class WriteBarrierTransformer(FrameworkGCTransformer):
    initializing_stores = {}
    GC_PARAMS = {}
    class GCClass(MarkSweepGC):
        needs_write_barrier = True

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
    init_stores = find_initializing_stores(collect_analyzer, t.graphs[0])
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
    init_stores = find_initializing_stores(collect_analyzer, t.graphs[0])
    assert len(init_stores) == 5
