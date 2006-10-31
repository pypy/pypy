import py
from pypy import conftest

from pypy.rpython.test.test_llinterp import interpret 
from pypy.translator.translator import graphof
from pypy.jit.timeshifter.test.test_timeshift import hannotate
from pypy.jit.timeshifter.rtyper import HintRTyper
from pypy.jit.timeshifter.test.test_timeshift import P_NOVIRTUAL
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph
from pypy.rpython.objectmodel import hint

from pypy.lang.automata.dfa import *

def rundfa():
    a = getautomaton()
    assert recognize(a, "aaaaaaaaaab")
    assert recognize(a, "b")
    assert not recognize(a, "a")
    assert not recognize(a, "xyza")
    assert recognize(a, "aaaacb")

def test_dfa_simple():
    rundfa()

def test_dfa_interp():
    interpret(rundfa, [])

def test_dfa_compiledummy():
    def main(gets):
        a = getautomaton()
        dfatable = convertdfa(a)
        s = ["aaaaaaaaaab", "aaaa"][gets]
        return recognizetable(dfatable, s)
    
    interpret(main, [0])
    
# class TestWithPortal(object):
#     from pypy.jit.codegen.llgraph.rgenop import RGenOp

#     def setup_class(cls):
#         cls._cache = {}
#         cls._cache_order = []

#     def teardown_class(cls):
#         del cls._cache
#         del cls._cache_order

#     def timeshift_from_portal(self, main, portal, main_args,
#                               inline=None, policy=None,
#                               backendoptimize=False):

#         key = main, portal, inline, policy, backendoptimize
#         try:
#             maingraph, rtyper = self._cache[key]
#         except KeyError:
#             if len(self._cache_order) >= 3:
#                 del self._cache[self._cache_order.pop(0)]

#             hs, ha, rtyper = hannotate(main, main_args, portal=portal,
#                                        policy=policy, inline=inline,
#                                        backendoptimize=backendoptimize)

#             t = rtyper.annotator.translator
#             maingraph = graphof(t, main)
#             # make the timeshifted graphs
#             hrtyper = HintRTyper(ha, rtyper, self.RGenOp)
#             origportalgraph = graphof(t, portal)
#             hrtyper.specialize(origportalgraph=origportalgraph,
#                                view = conftest.option.view)

#             for graph in ha.translator.graphs:
#                 checkgraph(graph)
#                 t.graphs.append(graph)

#             if conftest.option.view:
#                 t.view()

#             self._cache[key] = maingraph, rtyper
#             self._cache_order.append(key)

#         llinterp = LLInterpreter(rtyper)
#         return llinterp.eval_graph(maingraph, main_args)

#     def test_dfa_compile(self):
#         def main(gets):
#             a = getautomaton()
#             dfatable = convertdfa(a)
#             s = ["aaaaaaaaaab", "aaaa"][gets]
#             return recognizetable(dfatable, s)

#         res = self.timeshift_from_portal(main, recognizetable, [0], policy=P_NOVIRTUAL)
#         assert res >= 0
