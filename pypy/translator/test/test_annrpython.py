
import autopath
from pypy.tool import test
from pypy.tool.udir import udir

from pypy.translator.annrpython import Annotator
from pypy.objspace.flow.model import *

class AnnonateTestCase(test.IntTestCase):
    def setUp(self):
        self.space = test.objspace('flow')

    def make_ann(self, func):
        """ make a pyrex-generated cfunction from the given func """
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        name = func.func_name
        funcgraph = self.space.build_flow(func)
        funcgraph.source = inspect.getsource(func)
        return Annotator(funcgraph)

    def reallyshow(self, graph):
        import os
        from pypy.translator.test.make_dot import make_dot
        from pypy.tool.udir import udir
        dest = make_dot(graph, udir, 'ps')
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
        a = Annotator(fun)
        a.build_types([int])
        end_var = a.get_return_value()
        end_ann = a.get_variables_ann()[end_var]
        self.assertEquals(end_ann.get_type(end_var), int)

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
        
        a = Annotator(fun)
        a.build_types([int])
        end_var = a.get_return_value()
        end_ann = a.get_variables_ann()[end_var]
        self.assertEquals(end_ann.get_type(end_var), int)

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

        a = Annotator(fun)
        #import sys; print >> sys.stderr, a.build_annotations(input_ann)
        a.build_types([int])
        end_var = a.get_return_value()
        end_ann = a.get_variables_ann()[end_var]
        self.assertEquals(end_ann.get_type(end_var), int)

    def test_simplify_calls(self):
        a = self.make_ann(f_calls_g)
        a.build_types([int])
        a.simplify_calls()
        #self.reallyshow(a.flowgraph)

def g(n):
    return [0,1,2,n]

def f_calls_g(n):
    total = 0
    for i in g(n):
        total += i
    return total


if __name__ == '__main__':
    test.main()
