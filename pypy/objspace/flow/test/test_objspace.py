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

    def test_print(self):
        x = self.codetest("def f(i):\n"
                          "    print i\n",
                          'f')

    def test_while(self):
        x = self.codetest("def f(i):\n"
                          "    while i > 0:\n"
                          "        i = i - 1\n"
                          "        print i\n",
                          'f')

    def test_union_easy(self):
        x = self.codetest("def f(i):\n"
                          "    if i:\n"
                          "        pass\n"
                          "    else:\n"
                          "        i = 5\n"
                          "    return i\n",
                          'f')

    def test_union_hard(self):
        x = self.codetest("def f(i):\n"
                          "    if i:\n"
                          "        i = 5\n"
                          "    return i\n",
                          'f')

    def dont_test_while_union(self):
        x = self.codetest("def f(i):\n"
                          "    total = 0\n"
                          "    while i > 0:\n"
                          "        total += i\n"
                          "        i = i - 1\n"
                          "    return total\n",
                          'f')

if __name__ == '__main__':
    test.main()
