
import autopath
from pypy.tool import test

from pypy.translator.genpyrex import GenPyrex
from pypy.translator.controlflow import *


class TestCase(test.IntTestCase):
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
        result = genpyrex(fun)
        self.assertEquals(result, """
def f(x):
    result = x + 1
    return result
""")

    def test_if(self):
        """
        one test source:
        def f(i, j):
            if i < 0:
                i = j
            return i
        """
        i = Variable("i")
        j = Variable("j")

        endbranchelse = EndBranch(i)
        endbranchif = EndBranch(j)

        conditionres = Variable("conditionres")
        conditionop = SpaceOperation("lt", [i, Constant(0)], conditionres)
    
        conditionalbranch = ConditionalBranch(condition, endbranchif, endbranchelse)

        startblock = BasicBlock([i, j], [i, j, conditionres], 
                           [conditionop],
                           conditionalbranch)
        fun = FunctionGraph(startblock, "f")
        result = GenPyrex(fun).emitcode()
        self.assertEquals(result, """
def f(i, j):
    conditionres = i < 0
    if conditionres: cinline "goto label1;"
    return i
    cinline "label1:"
    return j
""")

if __name__ == '__main__':
    test.main()
