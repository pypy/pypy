
import autopath
from pypy.tool import test

from pypy.translator.genpyrex import GenPyrex
from pypy.translator.controlflow import *

from pypy.translator.test.buildpyxmodule import make_module_from_pyxstring

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
        result = GenPyrex(fun).emitcode()
        mod = make_module_from_pyxstring(result)
        self.assertEquals(mod.f(1), 2)

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
    
        conditionalbranch = ConditionalBranch(conditionres, endbranchif, endbranchelse)

        startblock = BasicBlock([i, j], [i, j, conditionres], 
                           [conditionop],
                           conditionalbranch)
        fun = FunctionGraph(startblock, "f")
        result = GenPyrex(fun).emitcode()
        mod = make_module_from_pyxstring(result)
        self.assertEquals(mod.f(-1, 42), 42)
        self.assertEquals(mod.f(3, 5), 3)

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
        result = GenPyrex(fun).emitcode()
        mod = make_module_from_pyxstring(result)
        self.assertEquals(mod.f(42), 0)
        self.assertEquals(mod.f(-3), -3)

if __name__ == '__main__':
    test.main()
