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

    def reallyshow(self, x):
        import os
        from pypy.translator.test.make_dot import make_png
        make_png(x)
        #os.system('xv -nolimits /tmp/testgraph.png')
        os.system('gv /tmp/testgraph.ps')

    def show(self, x):
        pass   # or   self.reallyshow(x)

    def test_nothing(self):
        x = self.codetest("def nothing():\n"
                          "    pass\n",
                          'nothing')
        #self.assertEquals(x.functionname, 'f')
        self.assertEquals(x.startblock.branch.__class__, EndBranch)
        self.show(x)

    def test_simplebranch(self):
        x = self.codetest("def simplebranch(i, j):\n"
                          "    if i < 0:\n"
                          "        return i\n"
                          "    return j\n",
                          'simplebranch')
        self.show(x)

    def test_ifthenelse(self):
        x = self.codetest("def g(i):\n"
                          "    pass\n"
                          "def ifthenelse(i, j):\n"
                          "    if i < 0:\n"
                          "        i = j\n"
                          "    return g(i) + 1\n",
                          'ifthenelse')
        self.show(x)

    def test_print(self):
        x = self.codetest("def test_print(i):\n"
                          "    print i\n",
                          'test_print')
        self.show(x)

    def test_while(self):
        #import sys; print >> sys.stderr, "--- starting! ---"
        x = self.codetest("def test_while(i):\n"
                          "    while i > 0:\n"
                          "        i = i - 1\n"
                          "        #print i\n",
                          'test_while')
        #import sys; print >> sys.stderr, "--- done! ---"
        self.show(x)

    def test_union_easy(self):
        x = self.codetest("def union_easy(i):\n"
                          "    if i:\n"
                          "        pass\n"
                          "    else:\n"
                          "        i = 5\n"
                          "    return i\n",
                          'union_easy')
        self.show(x)

    def test_union_hard(self):
        x = self.codetest("def union_hard(i):\n"
                          "    if i:\n"
                          "        i = 5\n"
                          "    return i\n",
                          'union_hard')
        self.show(x)

    def test_while_union(self):
        x = self.codetest("def while_union(i):\n"
                          "    total = 0\n"
                          "    while i > 0:\n"
                          "        total += i\n"
                          "        i = i - 1\n"
                          "    return total\n",
                          'while_union')
        self.show(x)

    def test_simple_for(self):
        x = self.codetest("def simple_for(lst):\n"
                          "    total = 0\n"
                          "    for i in lst:\n"
                          "        total += i\n"
                          "    return total\n",
                          'simple_for')
        self.show(x)

    def test_nested_whiles(self):
        src = """
def nested_whiles(i, j):
    s = ''
    z = 5
    while z > 0:
        z = z - 1
        u = i
        while u < j:
            u = u + 1
            s = s + '.'
        s = s + '!'
    return s
"""
        x = self.codetest(src, 'nested_whiles')
        self.reallyshow(x)

if __name__ == '__main__':
    test.main()
