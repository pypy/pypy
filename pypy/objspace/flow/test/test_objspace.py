import autopath
from pypy.tool import test

from pypy.objspace.flow.wrapper import *
from pypy.translator.flowmodel import *

class TestFlowOjSpace(test.TestCase):
    def setUp(self):
        self.space = test.objspace('flow')

    def codetest(self, func):
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        #name = func.func_name
        graph = self.space.build_flow(func)
        graph.source = inspect.getsource(func)
        return graph

    def reallyshow(self, x):
        import os
        from pypy.translator.test.make_dot import make_dot
        from pypy.tool.udir import udir
        dest = make_dot(x, udir, 'ps')
        os.system('gv %s' % str(dest))

    def show(self, x):
        pass   # or   self.reallyshow(x)

    #__________________________________________________________
    def nothing():
        pass

    def test_nothing(self):
        x = self.codetest(self.nothing)
        self.assertEquals(x.startblock.branch.__class__, EndBranch)
        self.show(x)

    #__________________________________________________________
    def simplebranch(i, j):
        if i < 0:
            return i
        return j

    def test_simplebranch(self):
        x = self.codetest(self.simplebranch)
        self.show(x)

    #__________________________________________________________
    def ifthenelse(i, j):
        if i < 0:
            i = j
        return g(i) + 1
    
    def test_ifthenelse(self):
        x = self.codetest(self.simplebranch)
        self.show(x)

    #__________________________________________________________
    def print_(i):
        print i
    
    def test_print(self):
        x = self.codetest(self.print_)
        self.show(x)

    #__________________________________________________________
    def while_(i):
        while i > 0:
            i = i - 1

    def test_while(self):
        x = self.codetest(self.while_)
        self.show(x)

    #__________________________________________________________
    def union_easy(i):
        if i:
            pass
        else:
            i = 5
        return i

    def test_union_easy(self):
        x = self.codetest(self.union_easy)
        self.show(x)

    #__________________________________________________________
    def union_hard(i):
        if i:
            i = 5
        return i
    
    def test_union_hard(self):
        x = self.codetest(self.union_hard)
        self.show(x)

    #__________________________________________________________
    def while_union(i):
        total = 0
        while i > 0:
            total += i
            i = i - 1
        return total
    
    def test_while_union(self):
        x = self.codetest(self.while_union)
        self.show(x)

    #__________________________________________________________
    def simple_for(lst):
        total = 0
        for i in lst:
            total += i
        return total
    
    def test_simple_for(self):
        x = self.codetest(self.simple_for)
        self.show(x)

    #__________________________________________________________
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

    def test_nested_whiles(self):
        x = self.codetest(self.nested_whiles)
        self.show(x)

if __name__ == '__main__':
    test.main()
