
import autopath
from pypy.tool.udir import udir

from pypy.translator.genpyrex import GenPyrex
from pypy.objspace.flow.model import *

from pypy.translator.tool.buildpyxmodule import make_module_from_pyxstring
#from pypy.translator.test.make_dot import make_ps

# XXX this tries to make compiling faster for full-scale testing
from pypy.translator.tool import buildpyxmodule
buildpyxmodule.enable_fast_compilation()


class TestSourceGenTestCase:
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
        result = GenPyrex(fun).emitcode()
        mod = make_module_from_pyxstring('test_source1', udir, result)
        assert mod.f(1) == 2

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

        conditionres = Variable("conditionres")
        conditionop = SpaceOperation("lt", [i, Constant(0)], conditionres)
        startblock = Block([i, j])
        
        fun = FunctionGraph("f", startblock)
        startblock.operations.append(conditionop)
        startblock.exitswitch = conditionres
        startblock.closeblock(Link([i], fun.returnblock, False),
                              Link([j], fun.returnblock, True))
        
        result = GenPyrex(fun).emitcode()
        mod = make_module_from_pyxstring('test_source2', udir, result)
        assert mod.f(-1, 42) == 42
        assert mod.f(3, 5) == 3

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

        result = GenPyrex(fun).emitcode()
        mod = make_module_from_pyxstring('test_source4', udir, result)
        assert mod.f(3) == 6
        assert mod.f(-3) == 0
