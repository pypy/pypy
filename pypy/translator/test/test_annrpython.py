
import autopath
from pypy.tool import testit
from pypy.tool.udir import udir

from pypy.translator.annrpython import RPythonAnnotator, annmodel
from pypy.translator.translator import Translator
from pypy.objspace.flow.model import *

from pypy.translator.test import snippet

class AnnonateTestCase(testit.IntTestCase):
    def setUp(self):
        self.space = testit.objspace('flow')

    def make_fun(self, func):
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        name = func.func_name
        funcgraph = self.space.build_flow(func)
        funcgraph.source = inspect.getsource(func)
        return funcgraph

    def reallyshow(self, graph):
        import os
        from pypy.translator.tool.make_dot import make_dot
        dest = make_dot('b', graph)
        os.system('gv %s' % str(dest))

    def test_simple_func(self):
        """
        one test source:
        def f(x):
            return x+1
        """
        x = Variable("x")
        result = Variable("result")
        op = SpaceOperation("add", [x, Constant(1)], result)
        block = Block([x])
        fun = FunctionGraph("f", block)
        block.operations.append(op)
        block.closeblock(Link([result], fun.returnblock))
        a = RPythonAnnotator()
        a.build_types(fun, [int])
        self.assertEquals(a.gettype(fun.getreturnvar()), int)

    def test_while(self):
        """
        one test source:
        def f(i):
            while i > 0:
                i = i - 1
            return i
        """
        i = Variable("i")
        conditionres = Variable("conditionres")
        conditionop = SpaceOperation("gt", [i, Constant(0)], conditionres)
        decop = SpaceOperation("add", [i, Constant(-1)], i)
        headerblock = Block([i])
        whileblock = Block([i])

        fun = FunctionGraph("f", headerblock)
        headerblock.operations.append(conditionop)
        headerblock.exitswitch = conditionres
        headerblock.closeblock(Link([i], fun.returnblock, False),
                               Link([i], whileblock, True))
        whileblock.operations.append(decop)
        whileblock.closeblock(Link([i], headerblock))

        a = RPythonAnnotator()
        a.build_types(fun, [int])
        self.assertEquals(a.gettype(fun.getreturnvar()), int)

    def test_while_sum(self):
        """
        one test source:
        def f(i):
            sum = 0
            while i > 0:
                sum = sum + i
                i = i - 1
            return sum
        """
        i = Variable("i")
        sum = Variable("sum")

        conditionres = Variable("conditionres")
        conditionop = SpaceOperation("gt", [i, Constant(0)], conditionres)
        decop = SpaceOperation("add", [i, Constant(-1)], i)
        addop = SpaceOperation("add", [i, sum], sum)
        startblock = Block([i])
        headerblock = Block([i, sum])
        whileblock = Block([i, sum])

        fun = FunctionGraph("f", startblock)
        startblock.closeblock(Link([i, Constant(0)], headerblock))
        headerblock.operations.append(conditionop)
        headerblock.exitswitch = conditionres
        headerblock.closeblock(Link([sum], fun.returnblock, False),
                               Link([i, sum], whileblock, True))
        whileblock.operations.append(addop)
        whileblock.operations.append(decop)
        whileblock.closeblock(Link([i, sum], headerblock))

        a = RPythonAnnotator()
        a.build_types(fun, [int])
        self.assertEquals(a.gettype(fun.getreturnvar()), int)

    #def test_simplify_calls(self):
    #    fun = self.make_fun(f_calls_g)
    #    a = RPythonAnnotator()
    #    a.build_types(fun, [int])
    #    a.simplify_calls()
    #    #self.reallyshow(fun)
    # XXX write test_transform.py

    def test_lists(self):
        fun = self.make_fun(snippet.poor_man_rev_range)
        a = RPythonAnnotator()
        a.build_types(fun, [int])
        # result should be a list of integers
        self.assertEquals(a.gettype(fun.getreturnvar()), list)
        end_cell = a.binding(fun.getreturnvar())
        self.assertEquals(end_cell.s_item.knowntype, int)

    def test_factorial(self):
        translator = Translator(snippet.factorial)
        graph = translator.getflowgraph()
        a = RPythonAnnotator(translator)
        a.build_types(graph, [int])
        # result should be an integer
        self.assertEquals(a.gettype(graph.getreturnvar()), int)

    def test_build_instance(self):
        translator = Translator(snippet.build_instance)
        graph = translator.getflowgraph()
        a = RPythonAnnotator(translator)
        a.build_types(graph, [])
        # result should be a snippet.C instance
        self.assertEquals(a.gettype(graph.getreturnvar()), snippet.C)

    def test_set_attr(self):
        translator = Translator(snippet.set_attr)
        graph = translator.getflowgraph()
        a = RPythonAnnotator(translator)
        a.build_types(graph, [])
        # result should be an integer
        self.assertEquals(a.gettype(graph.getreturnvar()), int)

    def test_inheritance1(self):
        translator = Translator(snippet.inheritance1)
        graph = translator.getflowgraph()
        a = RPythonAnnotator(translator)
        a.build_types(graph, [])
        # result should be exactly:
        self.assertEquals(a.binding(graph.getreturnvar()),
                          annmodel.SomeTuple([
                              annmodel.SomeTuple([]),
                              annmodel.SomeInteger()
                              ]))

    def test_inheritance2(self):
        translator = Translator(snippet.inheritance2)
        graph = translator.getflowgraph()
        a = RPythonAnnotator(translator)
        a.build_types(graph, [])
        # result should be exactly:
        self.assertEquals(a.binding(graph.getreturnvar()),
                          annmodel.SomeTuple([
                              annmodel.SomeInteger(),
                              annmodel.SomeObject()
                              ]))


def g(n):
    return [0,1,2,n]

def f_calls_g(n):
    total = 0
    for i in g(n):
        total += i
    return total


if __name__ == '__main__':
    testit.main()
