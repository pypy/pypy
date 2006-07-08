from pypy.interpreter.astcompiler import ast#_temp as ast
from pypy.module.recparser.pyparser import source2ast
from pypy.interpreter.pyparser.test.test_astbuilder import FakeSpace

class BaseVisitor:
    def __getattr__(self, attr):
        if attr.startswith('visit'):
            return self.default
        else:
            raise AttributeError(attr)
    def default(self, node):
        return node
    def visitAdd(self, node):
        return ast.Const(3)

class TestMutate:

    def test_mutate_add(self):
        c1 = ast.Const(1)
        c2 = ast.Const(2)
        add = ast.Add(c1, c2)
        class Visitor(BaseVisitor):
            def visitAdd(self, node):
                return ast.Const(3)
        c3 = add.mutate(Visitor())
        assert isinstance(c3, ast.Const)

    def test_mutate_strange_cases(self):
        src = '''
if a:
    b
        '''
        ast = source2ast(FakeSpace(), src)
        ast.mutate(BaseVisitor())
        src = '''
try:
    b
except Exception:
    pass
        '''
        ast = source2ast(FakeSpace(), src)
        ast.mutate(BaseVisitor())
        src = '{1:2}'
        ast = source2ast(FakeSpace(), src)
        ast.mutate(BaseVisitor())
        src = '1 > 3'
        ast = source2ast(FakeSpace(), src)
        ast.mutate(BaseVisitor())
         

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

    def test_mutate_strange_cases(self):
        import parser
        class BaseVisitor:
            def __getattr__(self, attr):
                if attr.startswith('visit'):
                    return self.default
                else:
                    raise AttributeError(attr)
            def default(self, node):
                return node
        ast = parser.source2ast('if a: b')
        ast.mutate(BaseVisitor())
        
        src = '''
try:
    b
except Exception:
    pass
        '''
        ast = parser.source2ast(src)
        ast.mutate(BaseVisitor())

        src = '{1:2}'
        ast = parser.source2ast(src)
        ast.mutate(BaseVisitor())

        src = '1 > 3'
        ast = parser.source2ast(src)
        ast.mutate(BaseVisitor())
        
