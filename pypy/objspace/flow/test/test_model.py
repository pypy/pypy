import autopath
from pypy.tool import testit

from pypy.objspace.flow.model import *

class TestModel(testit.TestCase):
    def setUp(self):
        self.space = testit.objspace('flow')

    def getflow(self, func):
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        #name = func.func_name
        return self.space.build_flow(func)

    #_____________________________________________
    def simplefunc(x):
        return x+1

    def test_simplefunc(self):
        graph = self.getflow(self.simplefunc)
        l = flatten(graph)
        print l
        self.assertEquals(len(l), 4)

    def test_class(self):
        graph = self.getflow(self.simplefunc)

        class MyVisitor:
            def __init__(self):
                self.blocks = []
                self.links = []

            def visit_FunctionGraph(self, graph):
                self.graph = graph
            def visit_Block(self, block):
                self.blocks.append(block)
            def visit_Link(self, link):
                self.links.append(link)

        v = MyVisitor()
        traverse(v, graph)
        self.assertEquals(len(v.blocks), 2)
        self.assertEquals(len(v.links), 1)
        self.assertEquals(v.graph, graph)
        self.assertEquals(v.links[0], graph.startblock.exits[0])

    def test_partial_class(self):
        graph = self.getflow(self.simplefunc)

        class MyVisitor:
            def __init__(self):
                self.blocks = []
                self.links = []

            def visit_FunctionGraph(self, graph):
                self.graph = graph
            def visit_Block(self, block):
                self.blocks.append(block)
            def visit(self, link):
                self.links.append(link)

        v = MyVisitor()
        traverse(v, graph)
        self.assertEquals(len(v.blocks), 2)
        self.assertEquals(len(v.links), 1)
        self.assertEquals(v.graph, graph)
        self.assertEquals(v.links[0], graph.startblock.exits[0])

    def loop(x):
        x = abs(x)
        while x:
            x = x - 1

    def test_loop(self):
        graph = self.getflow(self.simplefunc)
        l = flatten(graph)
        self.assertEquals(len(l), 4)


if __name__ == '__main__':
    testit.main()
