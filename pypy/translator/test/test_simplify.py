import autopath
from pypy.tool import test
from pypy.tool.udir import udir
from pypy.translator.genpyrex import GenPyrex
from pypy.translator.flowmodel import *
from pypy.translator.test.buildpyxmodule import make_module_from_pyxstring
from pypy.translator.simplify import eliminate_empty_blocks

make_dot = 1

if make_dot: 
    from pypy.translator.test.make_dot import make_dot
else:
    def make_dot(*args): pass

class SimplifyTestCase(test.IntTestCase):
    def setUp(self):
        self.space = test.objspace('flow')

    def make_graph(self, func):
        """ make a pyrex-generated cfunction from the given func """
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        name = func.func_name
        funcgraph = self.space.build_flow(func)
        funcgraph.source = inspect.getsource(func)
        result = GenPyrex(funcgraph).emitcode()
        return funcgraph 

    def xxxmake_cfunc(self, func):
        """ make a pyrex-generated cfunction from the given func """
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        name = func.func_name
        funcgraph = self.space.build_flow(func)
        funcgraph.source = inspect.getsource(func)
        result = GenPyrex(funcgraph).emitcode()
        make_dot(funcgraph, udir, 'ps')
        mod = make_module_from_pyxstring(name, udir, result)
        return getattr(mod, name)

    def make_cfunc_from_graph (self, graph):
        name = graph.functionname
        result = GenPyrex(graph).emitcode()
        make_dot(graph, udir, 'ps')
        mod = make_module_from_pyxstring(name, udir, result)
        return getattr(mod, name)

    #____________________________________________________
    def simple_while(i):
        j = 0
        while j < i:
            j = j + 1
        return j

    def test_simple_func_identical_results(self):
        graph = self.make_graph(self.simple_while)
        f0 = self.make_cfunc_from_graph(graph)
        newgraph = eliminate_empty_blocks(graph)
        newgraph.functionname = 'simple_while_optimized'
        f1 = self.make_cfunc_from_graph(newgraph)
        self.assertEquals(f0(3), f1(3))
        self.assertEquals(f1(3), self.simple_while.im_func(3))

class TestFlowModelSimplification(test.IntTestCase):
    def test_eliminate_empty_block_simple(self):
        result = Variable("result")
        endbranch = EndBranch(result)
        op = SpaceOperation('',[],[])
        block2 = BasicBlock([result], [result], [op], endbranch)
        branch2 = Branch([result], block2)
        block1 = BasicBlock([result], [result], [], branch2)
        branch1 = Branch([result], block1)
        startblock = BasicBlock([result], [result], [], branch1)
        fun = FunctionGraph(startblock, "f")

        eliminate_empty_blocks(fun)
        nodelist = fun.flatten()

        self.assert_(startblock in nodelist)
        self.assert_(block1 not in nodelist)

    def test_eliminate_empty_block_renaming(self):
        result = Variable("result")
        x = Variable("x")
        y = Variable("y")
        zero = Constant(0)
        endbranch = EndBranch(result)
        op = SpaceOperation('',[],[])

        block2 = BasicBlock([result], [], [op], endbranch)

        branch2 = Branch([y,zero], block2)

        block1 = BasicBlock([x], [], [], branch2)

        branch1 = Branch([x], block1)

        startblock = BasicBlock([x], [], [], branch1)
        fun = FunctionGraph(startblock, "f")
        make_dot(fun, udir, 'ps')
        eliminate_empty_blocks(fun)
        fun.functionname = 'f_optimized'
        make_dot(fun, udir, 'ps')
        nodelist = fun.flatten()

        self.assert_(startblock in nodelist)
        self.assert_(block1 not in nodelist)
        self.assert_(block1 not in nodelist)
        self.assertEquals(startblock.branch.args[0], x)
        self.assertEquals(startblock.branch.args[1], zero)


if __name__ == '__main__':
    test.main()
