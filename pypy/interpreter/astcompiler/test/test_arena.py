from rpython.translator.c.test.test_genc import compile
from rpython.rtyper.test.test_llinterp import interpret
from pypy.interpreter.astcompiler import ast
from pypy.interpreter.astcompiler import astarena
from rpython.rtyper.test.tool import BaseRtypingTest


class TestArena(BaseRtypingTest):
    def test_empty_module(self):
        def run():
            arena = astarena.Arena()
            node = ast.Module(arena, [
                ast.Name(arena, 'x', ast.Load, 1, 1)])
            return len(node.body)
        assert run() == 1
        assert interpret(run, []) == 1
        fn = compile(run, [])
        assert fn() == 1

    def test_compile(self):
        from pypy.interpreter.pyparser import pyparse
        from pypy.interpreter.astcompiler import astbuilder
        from pypy.objspace.fake.objspace import FakeObjSpace
        space = FakeObjSpace()
        def run(expr):
            p = pyparse.PythonParser(space)
            info = pyparse.CompileInfo("<test>", 'exec')
            arena = astarena.Arena()
            cst = p.parse_source(expr, info)
            ast = astbuilder.ast_from_node(space, arena, cst, info)
        run("x=2")
        # res = interpret(run, [self.string_to_ll("x=2")])
        fn = compile(run, [str])
        fn("x=2")
        
