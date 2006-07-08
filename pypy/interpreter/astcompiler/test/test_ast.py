from pypy.interpreter.astcompiler import ast#_temp as ast

class TestMutate:

    def test_mutate_add(self):
        c1 = ast.Const(1)
        c2 = ast.Const(2)
        add = ast.Add(c1, c2)
        class Visitor:
            def __getattr__(self, attr):
                if attr.startswith('visit'):
                    return self.default
                else:
                    raise AttributeError(attr)
            def default(self, node):
                return node
            def visitAdd(self, node):
                return ast.Const(3)
        c3 = add.mutate(Visitor())
        assert isinstance(c3, ast.Const)

class AppTestMutate:
    def test_mutate_add(self):
        import parser
        c1 = parser.ASTConst(1)
        c2 = parser.ASTConst(2)
        add = parser.ASTAdd(c1, c2)
        class Visitor:
            def __getattr__(self, attr):
                if attr.startswith('visit'):
                    return self.default
                else:
                    raise AttributeError(attr)
            def default(self, node):
                return node
            def visitAdd(self, node):
                return parser.ASTConst(3)
        c3 = add.mutate(Visitor())
        assert isinstance(c3, parser.ASTConst)
