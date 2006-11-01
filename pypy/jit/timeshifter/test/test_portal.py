from pypy import conftest
from pypy.translator.translator import graphof
from pypy.jit.timeshifter.test.test_timeshift import hannotate
from pypy.jit.timeshifter.hrtyper import HintRTyper
from pypy.jit.timeshifter.test.test_timeshift import P_NOVIRTUAL
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph, summary
from pypy.rlib.objectmodel import hint

from pypy.rlib.objectmodel import hint

import py.test

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
            maingraph, readportalgraph, rtyper = self._cache[key]
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

            readportalgraph = hrtyper.readportalgraph
            self._cache[key] = maingraph, readportalgraph, rtyper
            self._cache_order.append(key)

        self.readportalgraph = readportalgraph
        self.main_args = main_args
        self.rtyper = rtyper
        llinterp = LLInterpreter(rtyper)
        res = llinterp.eval_graph(maingraph, main_args)
        return res

    def check_insns(self, expected=None, **counts):
        # XXX only works if the portal is the same as the main
        llinterp = LLInterpreter(self.rtyper)
        residual_graph = llinterp.eval_graph(self.readportalgraph,
                                             self.main_args)._obj.graph
        self.insns = summary(residual_graph)
        if expected is not None:
            assert self.insns == expected
        for opname, count in counts.items():
            assert self.insns.get(opname, 0) == count
            
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
        self.check_insns(int_floordiv=1, int_mul=0)

        res = self.timeshift_from_portal(ll_function, ll_function, [4],
                                         policy=P_NOVIRTUAL)
        assert res == 68
        self.check_insns(int_floordiv=1, int_mul=0)

    def test_dfa_compile(self):
        py.test.skip("we've gone yellow")
        from pypy.lang.automata.dfa import getautomaton, convertdfa, recognizetable
        def main(gets):
            a = getautomaton()
            dfatable, final_states = convertdfa(a)
            s = ["aaaaaaaaaab", "aaaa"][gets]
            return recognizetable(dfatable, s, final_states)

        res = self.timeshift_from_portal(main, recognizetable, [0], policy=P_NOVIRTUAL)
        assert res

        res = self.timeshift_from_portal(main, recognizetable, [1], policy=P_NOVIRTUAL)
        assert not res

    def test_method_call_promote(self):
        class Base(object):
            pass
        class Int(Base):
            def __init__(self, n):
                self.n = n
            def double(self):
                return Int(self.n * 2)
            def get(self):
                return self.n
        class Str(Base):
            def __init__(self, s):
                self.s = s
            def double(self):
                return Str(self.s + self.s)
            def get(self):
                return ord(self.s[4])

        def ll_make(n):
            if n > 0:
                return Int(n)
            else:
                return Str('123')

        def ll_function(n):
            hint(None, global_merge_point=True)
            o = ll_make(n)
            hint(o.__class__, promote=True)
            return o.double().get()

        res = self.timeshift_from_portal(ll_function, ll_function, [5], policy=P_NOVIRTUAL)
        assert res == 10
        self.check_insns(indirect_call=0)

        res = self.timeshift_from_portal(ll_function, ll_function, [0], policy=P_NOVIRTUAL)
        assert res == ord('2')
        self.check_insns(indirect_call=0)
