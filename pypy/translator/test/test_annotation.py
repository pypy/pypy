
import autopath
from pypy.tool import test
from pypy.tool.udir import udir

from pypy.translator.annotation import Annotator, set_type, get_type
from pypy.translator.flowmodel import *

class TestCase(test.IntTestCase):
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
        endbranch = EndBranch(result)
        block = BasicBlock([x], [x], 
                           [op],
                           endbranch)
        fun = FunctionGraph(block, "f")
        a = Annotator(fun)
        input_ann = []
        set_type(fun.get_args()[0], int, input_ann)
        a.build_annotations(input_ann)
        end_var, end_ann = a.end_annotations()
        self.assertEquals(get_type(end_var, end_ann), int)

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

        conditionbranch = ConditionalBranch()
        headerbranch = Branch()
        whileblock = BasicBlock([i], [i], [decop], headerbranch)
        whilebranch = Branch([i], whileblock)
        endbranch = EndBranch(i)
        conditionbranch.set(conditionres, whilebranch, endbranch)

        headerblock = BasicBlock([i], [i, conditionres],
                                 [conditionop], conditionbranch)

        headerbranch.set([i], headerblock)

        startblock = BasicBlock([i], [i], 
                                [], headerbranch)

        fun = FunctionGraph(startblock, "f")
        
        a = Annotator(fun)
        input_ann = []
        set_type(fun.get_args()[0], int, input_ann)
        a.build_annotations(input_ann)
        end_var, end_ann = a.end_annotations()
        self.assertEquals(get_type(end_var, end_ann), int)

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

        conditionbranch = ConditionalBranch()
        headerbranch = Branch()
        headerbranch2 = Branch()
        whileblock = BasicBlock([i, sum], [i, sum], [addop, decop], headerbranch2)
        whilebranch = Branch([i, sum], whileblock)
        
        endbranch = EndBranch(sum)
        conditionbranch.set(conditionres, whilebranch, endbranch)

        headerblock = BasicBlock([i, sum], [i, conditionres],
                                 [conditionop], conditionbranch)

        headerbranch.set([i, Constant(0)], headerblock)
        headerbranch2.set([i, sum], headerblock)
        startblock = BasicBlock([i], [i, sum], 
                                [], headerbranch)

        fun = FunctionGraph(startblock, "f")

        a = Annotator(fun)
        input_ann = []
        set_type(fun.get_args()[0], int, input_ann)
        import sys; print >> sys.stderr, a.build_annotations(input_ann)
        end_var, end_ann = a.end_annotations()
        self.assertEquals(get_type(end_var, end_ann), int)

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
