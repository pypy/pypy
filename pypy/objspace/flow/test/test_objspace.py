import autopath
from pypy.tool import test

from pypy.objspace.flow.wrapper import *
from pypy.translator.controlflow import *

class TestFlowOjSpace(test.TestCase):
    def setUp(self):
        self.space = test.objspace('flow')

    def codetest(self, source, functionname, args_w):
        glob = {}
        exec source in glob
        func = glob[functionname]
        w_args = self.space.newtuple(args_w)
        w_kwds = self.space.newdict([])
        return self.space.build_flow(func, w_args, w_kwds)

    def test_nothing(self):
        x = self.codetest("def f():\n"
                          "    pass\n",
                          'f', [])
        self.assertEquals(x.functionname, 'f')
        self.assertEquals(x.startblock.branch.__class__, EndBranch)

    def test_ifthenelse(self):
        x = self.codetest("def f(i, j):\n"
                          "    if i < 0:\n"
                          "        i = j\n"
                          "    return g(i) + 1\n",
                          'f', [W_Variable()])
        

if __name__ == '__main__':
    test.main()
