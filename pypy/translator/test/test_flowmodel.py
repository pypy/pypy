
import autopath
from pypy.tool import test
from pypy.translator.flowmodel import *

class TestFlowModel(test.IntTestCase):
    def test_flatten(self):
        result = Variable("result")
        endbranch = EndBranch(result)
        block = BasicBlock([result], [result], 
                           [],
                           endbranch)
        fun = FunctionGraph(block, "f")

        nodelist = fun.flatten()
        self.assert_(endbranch in nodelist)
        self.assert_(block in nodelist)
        self.assert_(result not in nodelist)

    def test_flatten_more(self):
        result = Variable("result")
        endbranch = EndBranch(result)
        block2 = BasicBlock([result], [result], [], endbranch)
        branch = Branch([result], block2)
        block = BasicBlock([result], [result], [], branch)
        fun = FunctionGraph(block, "f")

        nodelist = fun.flatten()
        self.assert_(endbranch in nodelist)
        self.assert_(block in nodelist)
        self.assert_(block2 in nodelist)
        self.assert_(branch in nodelist)
        self.assert_(result not in nodelist)

if __name__ == '__main__':
    test.main()
