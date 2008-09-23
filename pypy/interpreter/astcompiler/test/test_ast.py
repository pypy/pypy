from pypy.interpreter.astcompiler import ast#_temp as ast
from pypy.interpreter.pyparser.test.test_astbuilder import source2ast

class BaseVisitor(ast.ASTVisitor):
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
        ast = source2ast(src, 'exec')
        ast.mutate(BaseVisitor())
        src = '''
try:
    b
except Exception:
    pass
        '''
        ast = source2ast(src, 'exec')
        ast.mutate(BaseVisitor())
        src = '{1:2}'
        ast = source2ast(src, 'exec')
        ast.mutate(BaseVisitor())
        src = '1 > 3'
        ast = source2ast(src, 'exec')
        ast.mutate(BaseVisitor())

    def test_mutate_elision(self):
        class ConstRemover(BaseVisitor):
            def visitConst(self, const):
                return None
        listast = source2ast("[1, 2]", 'exec')
        listast = listast.mutate(ConstRemover())
        listnode = listast.node.nodes[0].expr
        assert isinstance(listnode, ast.List)
        assert len(listnode.nodes) == 0

class AppTestMutate:
    def setup_class(cls):
        cls.w_BaseVisitor = cls.space.appexec([], '''():
        class BaseVisitor:
            def __getattr__(self, attr):
                if attr.startswith('visit'):
                    return self.default
                else:
                    raise AttributeError(attr)
            def default(self, node):
                return node
        return BaseVisitor''')
    
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
        ast = parser.source2ast('if a: b')
        ast.mutate(self.BaseVisitor())
        
        src = '''
try:
    b
except Exception:
    pass
        '''
        ast = parser.source2ast(src)
        ast.mutate(self.BaseVisitor())

        src = '{1:2}'
        ast = parser.source2ast(src)
        ast.mutate(self.BaseVisitor())

        src = '1 > 3'
        ast = parser.source2ast(src)
        ast.mutate(self.BaseVisitor())

    def test_mutate_tuple(self):
        from parser import source2ast, ASTConst, ASTTuple
        class TupleChanger(self.BaseVisitor):
            def visitConst(self, const):
                return ASTConst(1)
        tup = ASTTuple([ASTConst(2)])
        tup = tup.mutate(TupleChanger())
        assert tup.nodes[0].value == 1

    def test_mutate_elision(self):
        from parser import source2ast, ASTConst, ASTList
        class ConstRemover(self.BaseVisitor):
            def visitConst(self, const):
                return None
        listast = source2ast("[1, 2]")
        listast = listast.mutate(ConstRemover())
        listnode = listast.node.nodes[0].expr
        assert isinstance(listnode, ASTList)
        assert len(listnode.nodes) == 0
