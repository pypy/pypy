import autopath

from pypy.objspace.flow.model import *

objspacename = 'flow'

class TestModel:
    def getflow(self, func):
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        # disable implicit exceptions to keep the graphs simple and checkable
        self.space.handle_implicit_exceptions = lambda exceptions: None
        try:
            return self.space.build_flow(func)
        finally:
            del self.space.handle_implicit_exceptions

    #_____________________________________________
    def simplefunc(x):
        return x+1

    def test_simplefunc(self):
        graph = self.getflow(self.simplefunc)
        assert all_operations(graph) == {'add': 1}

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
        #assert len(v.blocks) == 2
        #assert len(v.links) == 1
        assert v.graph == graph
        assert v.links[0] == graph.startblock.exits[0]

##    def test_partial_class(self):
##        graph = self.getflow(self.simplefunc)

##        class MyVisitor:
##            def __init__(self):
##                self.blocks = []
##                self.links = []

##            def visit_FunctionGraph(self, graph):
##                self.graph = graph
##            def visit_Block(self, block):
##                self.blocks.append(block)
##            def visit(self, link):
##                self.links.append(link)

##        v = MyVisitor()
##        traverse(v, graph)
##        assert len(v.blocks) == 2
##        assert len(v.links) == 1
##        assert v.graph == graph
##        assert v.links[0] == graph.startblock.exits[0]

    def loop(x):
        x = abs(x)
        while x:
            x = x - 1

    def test_loop(self):
        graph = self.getflow(self.loop)
        assert all_operations(graph) == {'abs': 1,
                                         'is_true': 1,
                                         'sub': 1}


def all_operations(graph):
    result = {}
    def visit(node):
        if isinstance(node, Block):
            for op in node.operations:
                result.setdefault(op.opname, 0)
                result[op.opname] += 1
    traverse(visit, graph)
    return result
