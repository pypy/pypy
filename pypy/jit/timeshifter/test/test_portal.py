from pypy import conftest
from pypy.translator.translator import graphof
from pypy.jit.timeshifter.test.test_timeshift import hannotate
from pypy.jit.timeshifter.rtyper import HintRTyper
from pypy.jit.timeshifter.test.test_timeshift import P_NOVIRTUAL
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph
from pypy.rpython.objectmodel import hint

from pypy.rpython.objectmodel import hint


class TestPortal(object):
    from pypy.jit.codegen.llgraph.rgenop import RGenOp

    def setup_class(cls):
        cls._cache = {}
        cls._cache_order = []

    def teardown_class(cls):
        del cls._cache
        del cls._cache_order

    def timeshift_from_portal(self, main, portal, main_args,
                              inline=None, policy=None,
                              backendoptimize=False):

        key = main, portal, inline, policy, backendoptimize
        try:
            maingraph, rtyper = self._cache[key]
        except KeyError:
            if len(self._cache_order) >= 3:
                del self._cache[self._cache_order.pop(0)]

            hs, ha, rtyper = hannotate(main, main_args, portal=portal,
                                       policy=policy, inline=inline,
                                       backendoptimize=backendoptimize)

            t = rtyper.annotator.translator
            maingraph = graphof(t, main)
            # make the timeshifted graphs
            hrtyper = HintRTyper(ha, rtyper, self.RGenOp)
            origportalgraph = graphof(t, portal)
            hrtyper.specialize(origportalgraph=origportalgraph,
                               view = conftest.option.view)

            for graph in ha.translator.graphs:
                checkgraph(graph)
                t.graphs.append(graph)

            if conftest.option.view:
                t.view()

            self._cache[key] = maingraph, rtyper
            self._cache_order.append(key)

        llinterp = LLInterpreter(rtyper)
        return llinterp.eval_graph(maingraph, main_args)

    def test_simple(self):

        def main(code, x):
            return evaluate(code, x)

        def evaluate(y, x):
            hint(y, concrete=True)
            z = y+x
            return z

        res = self.timeshift_from_portal(main, evaluate, [3, 2])
        assert res == 5

        res = self.timeshift_from_portal(main, evaluate, [3, 5])
        assert res == 8

        res = self.timeshift_from_portal(main, evaluate, [4, 7])
        assert res == 11
    
    def test_main_as_portal(self):
        def main(x):
            return x

        res = self.timeshift_from_portal(main, main, [42])
        assert res == 42

    def test_multiple_portal_calls(self):
        def ll_function(n):
            hint(None, global_merge_point=True)
            k = n
            if k > 5:
                k //= 2
            k = hint(k, promote=True)
            k *= 17
            return hint(k, variable=True)

        res = self.timeshift_from_portal(ll_function, ll_function, [4],
                                         policy=P_NOVIRTUAL)
        assert res == 68
        #self.check_insns(int_floordiv=1, int_mul=0)

        res = self.timeshift_from_portal(ll_function, ll_function, [4],
                                         policy=P_NOVIRTUAL)
        assert res == 68
        #self.check_insns(int_floordiv=1, int_mul=0)
