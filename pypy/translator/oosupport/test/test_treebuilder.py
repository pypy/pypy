import py
from pypy.rpython.llinterp import LLInterpreter
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.oosupport.treebuilder import build_trees, SubOperation
from pypy.conftest import option
from pypy.rpython.test.test_rlist import BaseTestRlist
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin
from pypy.rpython.test.test_llinterp import get_interpreter

def translate(func, argtypes):
    t = TranslationContext()
    t.buildannotator().build_types(func, argtypes)
    t.buildrtyper(type_system='ootype').specialize()
    return t

def check_trees(func, argtypes):
    t = translate(func, argtypes)
    if option.view:
        t.view()
    graph = graphof(t, func)
    build_trees(graph)
    if option.view:
        t.view()
    interp = LLInterpreter(t.rtyper)
    def eval_func(*args):
        return interp.eval_graph(graph, args)
    return graph, eval_func

def test_simple():
    def fn(x):
        x = x+1
        x = x+1
        return x
    graph, eval_func = check_trees(fn, [int])
    block = graph.startblock
    assert len(block.operations) == 1
    assert isinstance(block.operations[0].args[0], SubOperation)
    assert eval_func(0) == 2

def test_function_call():
    py.test.skip('fixme!')
    def g(x):
        return x+1
    def fn(x):
        a = g(x)
        b = g(x+1)
        return a + b
    graph, eval_func = check_trees(fn, [int])
    block = graph.startblock
    assert len(block.operations) == 1
    assert isinstance(block.operations[0].args[0], SubOperation)
    assert isinstance(block.operations[0].args[1], SubOperation)
    assert eval_func(1) == 5

def test_count_exit_links():
    def g(x):
        pass
    def fn(x):
        res = x+1
        g(res)
        return res
    graph, eval_func = check_trees(fn, [int])
    block = graph.startblock
    assert len(block.operations) == 2
    v0 = block.operations[0].result
    assert block.exits[0].args == [v0]
    assert eval_func(0) == 1

def test_mutable_values():
    def fn():
        lst = []
        length = len(lst)
        lst.append(42)
        return length + 1
    graph, eval_func = check_trees(fn, [])
    block = graph.startblock
    assert not isinstance(block.operations[-1].args[0], SubOperation)
    assert eval_func() == 1

class BuildTreeRtypingTest(BaseRtypingTest, OORtypeMixin):
    def interpret(self, fn, args):
        interp, graph = get_interpreter(fn, args, view=False, viewbefore=False, type_system=self.type_system)
        if option.view:
            interp.typer.annotator.translator.view()
        build_trees(graph)
        if option.view:
            interp.typer.annotator.translator.view()
        return interp.eval_graph(graph, args)

class TestBuildTreeList(BuildTreeRtypingTest, BaseTestRlist):
    pass
