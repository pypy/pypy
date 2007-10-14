from pypy.objspace.flow.model import Constant, SpaceOperation
from pypy.annotation.model import SomeInteger
from pypy.rpython.memory.gc.base import GCBase
from pypy.rpython.memory.gctransform.test.test_transform import rtype
from pypy.rpython.memory.gctransform.transform import GcHighLevelOp
from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer, CollectAnalyzer
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rtyper import LowLevelOpList
from pypy.translator.c.gc import FrameworkGcPolicy
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.unsimplify import varoftype
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


class WriteBarrierTransformer(FrameworkGCTransformer):
    GC_PARAMS = {}
    class GC_CLASS(GCBase):
        def write_barrier(self, addr, addr_to, addr_struct):
            addr_to.address[0] = addr

def test_write_barrier_support():
    py.test.skip("no write barrier support yet!")
    t = TranslationContext()
    t.buildannotator().build_types(lambda x:x, [SomeInteger()])
    t.buildrtyper().specialize()
    llops = LowLevelOpList()
    PTR_TYPE = lltype.Ptr(lltype.GcStruct('S', ('x', lltype.Signed)))
    spaceop = SpaceOperation(
        "setfield",
        [varoftype(PTR_TYPE), Constant('x', lltype.Void)],
        varoftype(lltype.Void))
    transformer = WriteBarrierTransformer(t)
    hop = GcHighLevelOp(transformer, spaceop, llops)
    hop.dispatch()
    found = False
    for op in llops:
        if op.opname == 'direct_call':
            found = True
            break
    assert found
