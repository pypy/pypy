from pypy.interpreter.pyparser import pyparse
from pypy.interpreter.astcompiler.astbuilder import ast_from_node
from pypy.interpreter.astcompiler import ast, consts
from pypy.interpreter.astcompiler.unparse import unparse


class TestAstUnparser:
    def setup_class(cls):
        cls.parser = pyparse.PythonParser(cls.space)

    def get_ast(self, source, p_mode="exec", flags=None):
        if flags is None:
            flags = consts.CO_FUTURE_WITH_STATEMENT
        info = pyparse.CompileInfo("<test>", p_mode, flags)
        tree = self.parser.parse_source(source, info)
        ast_node = ast_from_node(self.space, tree, info, self.parser)
        return ast_node

    def get_first_expr(self, source, p_mode="exec", flags=None):
        mod = self.get_ast(source, p_mode, flags)
        assert len(mod.body) == 1
        expr = mod.body[0]
        assert isinstance(expr, ast.Expr)
        return expr.value

    def test_num(self):
        ast = self.get_first_expr("1")
        assert unparse(self.space, ast) == "1"
        ast = self.get_first_expr("1.63")
        assert unparse(self.space, ast) == "1.63"

    def test_str(self):
        ast = self.get_first_expr("u'a'")
        assert unparse(self.space, ast) == "'a'"

    def test_bytes(self):
        ast = self.get_first_expr("b'a'")
        assert unparse(self.space, ast) == "b'a'"

    def test_name(self):
        ast = self.get_first_expr('a')
        assert unparse(self.space, ast) == "a"

    def test_unaryop(self):
        ast = self.get_first_expr('+a')
        assert unparse(self.space, ast) == "+a"
        ast = self.get_first_expr('-a')
        assert unparse(self.space, ast) == "-a"
        ast = self.get_first_expr('~a')
        assert unparse(self.space, ast) == "~a"
        ast = self.get_first_expr('not a')
        assert unparse(self.space, ast) == "not a"

    def test_binaryop(self):
        ast = self.get_first_expr('b+a')
        assert unparse(self.space, ast) == "b + a"
        ast = self.get_first_expr('c*(b+a)')
        assert unparse(self.space, ast) == "c * (b + a)"
        ast = self.get_first_expr('c**(b+a)')
        assert unparse(self.space, ast) == "c ** (b + a)"
        ast = self.get_first_expr('2**2**3')
        assert unparse(self.space, ast) == "2 ** 2 ** 3"
        ast = self.get_first_expr('(2**2)**3')
        assert unparse(self.space, ast) == "(2 ** 2) ** 3"
        
        ast = self.get_first_expr('2 << 2 << 3')
        assert unparse(self.space, ast) == "2 << 2 << 3"
        ast = self.get_first_expr('2<<(2<<3)')
        assert unparse(self.space, ast) == "2 << (2 << 3)"

    def test_compare(self):
        ast = self.get_first_expr('b == 5 == c == d')
        assert unparse(self.space, ast) == 'b == 5 == c == d'

    def test_boolop(self):
        ast = self.get_first_expr('b and a and c or d')
        assert unparse(self.space, ast) == "b and a and c or d"

    def test_if(self):
        ast = self.get_first_expr('a if b else c')
        assert unparse(self.space, ast) == "a if b else c"

