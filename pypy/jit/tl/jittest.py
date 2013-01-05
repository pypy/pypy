"""
This file is imported by pypy.translation.driver when running the
target --jittest.  Feel free to hack it as needed; it is imported
only after the '---> Checkpoint' fork.
"""

from pypy.conftest import option
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.annlowlevel import llstr
from pypy.jit.metainterp import warmspot
from pypy.rlib.jit import OPTIMIZER_FULL


ARGS = ["jittest", "100"]


def jittest(driver):
    graph = driver.translator.graphs[0]
    interp = LLInterpreter(driver.translator.rtyper, malloc_check=False)

    def returns_null(T, *args, **kwds):
        return lltype.nullptr(T)
    interp.heap.malloc_nonmovable = returns_null     # XXX

    get_policy = driver.extra['jitpolicy']
    jitpolicy = get_policy(driver)

    from pypy.jit.backend.llgraph.runner import LLGraphCPU
    apply_jit(jitpolicy, interp, graph, LLGraphCPU)


def apply_jit(policy, interp, graph, CPUClass):
    print 'warmspot.jittify_and_run() started...'
    option.view = True
    LIST = graph.getargs()[0].concretetype
    lst = LIST.TO.ll_newlist(len(ARGS))
    for i, arg in enumerate(ARGS):
        lst.ll_setitem_fast(i, llstr(arg))
    warmspot.jittify_and_run(interp, graph, [lst], policy=policy,
                             listops=True, CPUClass=CPUClass,
                             backendopt=True, inline=True,
                             optimizer=OPTIMIZER_FULL)
