import py
from pypy.rpython.llinterp import LLInterpreter
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.oosupport.treebuilder import build_trees, SubOperation
from pypy.conftest import option
from pypy.rpython.test.test_rlist import BaseTestRlist
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.backendopt.checkvirtual import check_virtual_methods

def translate(func, argtypes, backendopt=False):
    t = TranslationContext()
    t.buildannotator().build_types(func, argtypes)
    t.buildrtyper(type_system='ootype').specialize()
    
    if backendopt: backend_optimizations(t, merge_if_blocks=True)
    return t

def check_trees(func, argtypes, backendopt=False):
    t = translate(func, argtypes, backendopt=backendopt)
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

def test_count_exitswitch():
    def g(x):
        pass
    def fn(i):
        kind = i & 3 # 2 bits
        str = "%x" % (kind,)
        if kind == 0:   # 00 bits
            res = "0"
        elif kind == 1: # 01 bits
            res = "1"
        elif kind == 3: # 11 bits
            res = "3"
        else:           # 10 bits
            res = "-1"
        return res, str
    graph, eval_func = check_trees(fn, [int], backendopt=True)
    block = graph.startblock
    assert len(block.operations) == 5
    v0 = block.operations[0].result
    assert block.exitswitch == v0
    for x in range(4):
        t = eval_func(x)
        assert t._items['item0']._str == fn(x)[0]
        assert t._items['item1']._str == fn(x)[1]
    #assert eval_func(0)._str == "0"
    #assert eval_func(1)._str == "1"
    #assert eval_func(2)._str == "-1"
    #assert eval_func(3)._str == "3"

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
