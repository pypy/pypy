import autopath
from pypy.tool import test

from pypy.objspace.flow.wrapper import *
from pypy.translator.controlflow import *

class TestFlowOjSpace(test.TestCase):
    def setUp(self):
        self.space = test.objspace('flow')

    def codetest(self, source, functionname):
        glob = {}
        exec source in glob
        func = glob[functionname]
        return self.space.build_flow(func)

    def test_nothing(self):
        x = self.codetest("def f():\n"
                          "    pass\n",
                          'f')
        self.assertEquals(x.functionname, 'f')
        self.assertEquals(x.startblock.branch.__class__, EndBranch)

    def test_simplebranch(self):
        x = self.codetest("def f(i, j):\n"
                          "    if i < 0:\n"
                          "        return i\n"
                          "    return j\n",
                          'f')

    def test_ifthenelse(self):
        x = self.codetest("def g(i):\n"
                          "    pass\n"
                          "def f(i, j):\n"
                          "    if i < 0:\n"
                          "        i = j\n"
                          "    return g(i) + 1\n",
                          'f')
        

if __name__ == '__main__':
    test.main()
