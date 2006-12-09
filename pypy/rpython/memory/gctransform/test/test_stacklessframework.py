from pypy.rpython.memory.gctransform.test.test_transform import rtype
from pypy.rpython.memory.gctransform.stacklessframework import \
     StacklessFrameworkGCTransformer
from pypy.rpython.lltypesystem import lltype
from pypy.translator.c.gc import StacklessFrameworkGcPolicy
from pypy.translator.translator import TranslationContext, graphof
from pypy import conftest

import py

class StacklessFrameworkGcPolicy2(StacklessFrameworkGcPolicy):
    transformerclass = StacklessFrameworkGCTransformer

def test_stackless_simple():
    def g(x):
        return x + 1
    class A(object):
        pass
    def entrypoint(argv):
        a = A()
        a.b = g(1)
        return a.b

    from pypy.rpython.llinterp import LLInterpreter
    from pypy.translator.c.genc import CStandaloneBuilder
    from pypy.translator.c import gc
    from pypy.annotation.listdef import s_list_of_strings

    t = rtype(entrypoint, [s_list_of_strings])
    cbuild = CStandaloneBuilder(t, entrypoint, t.config,
                                gcpolicy=StacklessFrameworkGcPolicy2)
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

    assert res == 2
