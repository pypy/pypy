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

    def check(self, expr, unparsed=None):
        if unparsed is None:
            unparsed = expr
        ast = self.get_first_expr(expr)
        assert unparse(self.space, ast) == unparsed
        # should be stable
        if expr != unparsed:
            ast = self.get_first_expr(unparsed)
            assert unparse(self.space, ast) == unparsed

    def test_num(self):
        self.check("1")
        self.check("1.64")

    def test_str(self):
        self.check("u'a'", "'a'")

    def test_bytes(self):
        self.check("b'a'")

    def test_name(self):
        self.check('a')

    def test_unaryop(self):
        self.check('+a')
        self.check('-a')
        self.check('~a')
        self.check('not a')

    def test_binaryop(self):
        self.check('b+a', "b + a")
        self.check('c*(b+a)', "c * (b + a)")
        self.check('c**(b+a)', "c ** (b + a)")
        self.check('2**2**3', "2 ** 2 ** 3")
        self.check('(2**2)**3', "(2 ** 2) ** 3")
        
        self.check('2 << 2 << 3')
        self.check('2<<(2<<3)', "2 << (2 << 3)")

    def test_compare(self):
        self.check('b == 5 == c == d')

    def test_boolop(self):
        self.check('b and a and c or d')

    def test_if(self):
        self.check('a if b else c')

    def test_list(self):
        self.check('[]')
        self.check('[1, 2, 3, 4]')

    def test_tuple(self):
        self.check('()')
        self.check('(a,)')
        self.check('([1, 2], a + 6, 3, 4)')

    def test_sets(self):
        self.check('{1}')
        self.check('{(1, 2), a + 6, 3, 4}')

    def test_dict(self):
        self.check('{}')
        self.check('{a: b, c: d}')
        self.check('{1: 2, **x}')

    def test_list_comprehension(self):
        self.check('[a for x in y if b if c]')

    def test_genexp(self):
        self.check('(a for x in y for z in b)')

    def test_set_comprehension(self):
        self.check('{a for (x,) in y for z in b}')

    def test_ellipsis(self):
        self.check('...')

    def test_index(self):
        self.check('a[1]')
        self.check('a[1:5]')
        self.check('a[1:5,7:12,:,5]')

    def test_yield(self):
        self.check('(yield)')
        self.check('(yield 4 + 6)')

    def test_yield_from(self):
        self.check('(yield from a)')

    def test_call(self):
        self.check('f()')
        self.check('f(a)')
        self.check('f(a, b, 1)')
        self.check('f(a, b, 1, a=4, b=78)')
        self.check('f(a, x=y, **b, **c)')
        self.check('f(*a)')
        self.check('f(x for y in z)')

    def test_lambda(self):
        self.check('lambda: 1')
        self.check('lambda a: 1')
        self.check('lambda a=1: 1')
        self.check('lambda b, c: 1')
        self.check('lambda *l: 1')
        self.check('lambda *, m, l=5: 1')
        self.check('lambda **foo: 1')

    def test_fstring(self):
        self.check('f"a{a + 2}b c{d}"')

