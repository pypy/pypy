
import autopath
from pypy.tool import test

from pypy.translator.genpyrex import genpyrex

class BasicBlock:
    def __init__(self, input_args, locals, operations, branch):
        self.input_args = input_args
        self.locals = locals
        self.operations = operations
        self.branch = branch

class Variable:
    def __init__(self, pseudoname):
        self.pseudoname = pseudoname

class Constant:
    def __init__(self, value):
        self.value = value

class SpaceOperation:
    def __init__(self, opname, args, result, branch):
        self.opname = opname
        self.args = args # list of variables
        self.result = result # <Variable/Constant instance>
        self.branch = branch # branch

class Branch:
    def __init__(self, args, target):
        self.args = args     # list of variables
        self.target = target # basic block instance

class ConditionalBranch:
    def __init__(self, condition, ifbranch, elsebranch):
	self.condition = condition
	self.ifbranch = ifbranch
	self.elsebranch = elsebranch

class EndBranch:
    def __init__(self, returnvalue):
        self.returnvalue = returnvalue

class FunctionGraph:
    def __init__(self, startblock, functionname):
	self.startblock = startblock
	self.functionname = functionname

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
        result = genpyrex(fun)
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
