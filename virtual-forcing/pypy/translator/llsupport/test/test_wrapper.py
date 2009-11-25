import py
from pypy import conftest
from pypy.translator.translator import TranslationContext
from pypy.translator.llsupport.wrapper import new_wrapper
from pypy.rpython.rmodel import PyObjPtr
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem import lltype


class TestMakeWrapper:

    def getgraph(self, func, argtypes=None):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.gc = "ref"
        config.translation.simplifying = True
        t = TranslationContext(config=config)
        if argtypes is None:
            argtypes = []
        a = t.buildannotator()
        a.build_types(func, argtypes)
        a.simplify()
        t.buildrtyper().specialize()
        wrapperptr = new_wrapper(func, t)
        wrappergraph = wrapperptr._obj.graph
        F = lltype.typeOf(wrapperptr).TO
        assert F.ARGS == (PyObjPtr,) * len(wrappergraph.getargs())
        assert F.RESULT == PyObjPtr

        for inputarg in wrappergraph.getargs():
            assert inputarg.concretetype == PyObjPtr
        assert wrappergraph.getreturnvar().concretetype == PyObjPtr
        return t.graphs[0], wrappergraph, t

    def interpret(self, t, graph, *args):
        interp = LLInterpreter(t.rtyper)
        result = interp.eval_graph(graph, [lltype.pyobjectptr(arg)
                                               for arg in args])
        return result._obj.value

    def test_simple(self):
        def f(x):
            return x * 3
        graph, wrappergraph, t = self.getgraph(f, [int])
        res = self.interpret(t, wrappergraph, 3)
        assert res == 9

    def test_manyargs(self):
        def f(x, y, z):
            return x * y + z
        graph, wrappergraph, t = self.getgraph(f, [int, int, int])
        res = self.interpret(t, wrappergraph, 3, 4, 5)
        assert res == 3 * 4 + 5

    def test_returnnone(self):
        def f():
            pass
        graph, wrappergraph, t = self.getgraph(f)
        res = self.interpret(t, wrappergraph)
        assert res is None
