import py


class AppTestAST:

    def setup_class(cls):
        cls.w_ast = cls.space.appexec([], """():
    import _ast
    return _ast""")

    def w_get_ast(self, source, mode="exec"):
        import _ast as ast
        mod = compile(source, "<test>", mode, ast.PyCF_ONLY_AST)
        assert isinstance(mod, ast.mod)
        return mod

    def test_module(self):
        ast = self.ast
        assert isinstance(ast.__version__, str)

    def test_build_ast(self):
        ast = self.ast
        mod = self.get_ast("x = 4")
        assert isinstance(mod, ast.Module)
        assert len(mod.body) == 1

    def test_simple_sums(self):
        ast = self.ast
        mod = self.get_ast("x = 4 + 5")
        expr = mod.body[0].value
        assert isinstance(expr, ast.BinOp)
        assert isinstance(expr.op, ast.Add)
        expr.op = ast.Sub()
        assert isinstance(expr.op, ast.Sub)
        co = compile(mod, "<example>", "exec")
        ns = {}
        exec co in ns
        assert ns["x"] == -1
        mod = self.get_ast("4 < 5 < 6", "eval")
        assert isinstance(mod.body, ast.Compare)
        assert len(mod.body.ops) == 2
        for op in mod.body.ops:
            assert isinstance(op, ast.Lt)
        mod.body.ops[0] = ast.Gt()
        co = compile(mod, "<string>", "eval")
        assert not eval(co)

    def test_string(self):
        mod = self.get_ast("'hi'", "eval")
        s = mod.body
        assert s.s == "hi"
        s.s = "pypy"
        s.s = 43
        assert eval(compile(mod, "<test>", "eval")) == 43

    def test_empty_initialization(self):
        ast = self.ast
        def com(node):
            return compile(node, "<test>", "exec")
        mod = ast.Module()
        raises(AttributeError, getattr, mod, "body")
        exc = raises(TypeError, com, mod).value
        assert str(exc) == "required field \"body\" missing from Module"
        expr = ast.Name()
        expr.id = "hi"
        expr.ctx = ast.Load()
        expr.lineno = 4
        exc = raises(TypeError, com, ast.Module([ast.Expr(expr)])).value
        assert (str(exc) == "required field \"lineno\" missing from stmt" or # cpython
                str(exc) == "required field \"lineno\" missing from Expr")   # pypy, better

    def test_int(self):
        ast = self.ast
        imp = ast.ImportFrom("", ["apples"], -1)
        assert imp.level == -1
        imp.level = 3
        assert imp.level == 3

    def test_identifier(self):
        ast = self.ast
        name = ast.Name("name_word", ast.Load())
        assert name.id == "name_word"
        name.id = "hi"
        assert name.id == "hi"

    def test_bool(self):
        ast = self.ast
        pr = ast.Print(None, [ast.Name("hi", ast.Load())], False)
        assert not pr.nl
        assert isinstance(pr.nl, bool)
        pr.nl = True
        assert pr.nl

    @py.test.mark.skipif("py.test.config.option.runappdirect")
    def test_object(self):
        ast = self.ast
        const = ast.Const(4)
        assert const.value == 4
        const.value = 5
        assert const.value == 5

    def test_optional(self):
        mod = self.get_ast("x(32)", "eval")
        call = mod.body
        assert call.starargs is None
        assert call.kwargs is None
        co = compile(mod, "<test>", "eval")
        ns = {"x" : lambda x: x}
        assert eval(co, ns) == 32

    def test_list_syncing(self):
        ast = self.ast
        mod = ast.Module([ast.Lt()])
        raises(TypeError, compile, mod, "<string>", "exec")
        mod = self.get_ast("x = y = 3")
        assign = mod.body[0]
        assert len(assign.targets) == 2
        assign.targets[1] = ast.Name("lemon", ast.Store(),
                                     lineno=0, col_offset=0)
        name = ast.Name("apple", ast.Store(),
                        lineno=0, col_offset=0)
        mod.body.append(ast.Assign([name], ast.Num(4, lineno=0, col_offset=0),
                                   lineno=0, col_offset=0))
        co = compile(mod, "<test>", "exec")
        ns = {}
        exec co in ns
        assert "y" not in ns
        assert ns["x"] == ns["lemon"] == 3
        assert ns["apple"] == 4

    def test_empty_module(self):
        compile(self.ast.Module([]), "<test>", "exec")

    def test_ast_types(self):
        ast = self.ast
        expr = ast.Expr()
        expr.value = ast.Lt()

    def test_abstract_ast_types(self):
        ast = self.ast
        ast.expr()
        ast.AST()
        class X(ast.AST):
            pass
        X()
        class Y(ast.expr):
            pass
        Y()
        exc = raises(TypeError, ast.AST, 2)
        assert exc.value.args[0] == "_ast.AST constructor takes 0 positional arguments"

    def test_constructor(self):
        ast = self.ast
        body = []
        mod = ast.Module(body)
        assert mod.body is body
        target = ast.Name("hi", ast.Store())
        expr = ast.Name("apples", ast.Load())
        otherwise = []
        fr = ast.For(target, expr, body, otherwise, lineno=0, col_offset=1)
        assert fr.target is target
        assert fr.iter is expr
        assert fr.orelse is otherwise
        assert fr.body is body
        assert fr.lineno == 0
        assert fr.col_offset == 1
        fr = ast.For(body=body, target=target, iter=expr, col_offset=1,
                     lineno=0, orelse=otherwise)
        assert fr.target is target
        assert fr.iter is expr
        assert fr.orelse is otherwise
        assert fr.body is body
        assert fr.lineno == 0
        assert fr.col_offset == 1
        exc = raises(TypeError, ast.Module, 1, 2).value
        msg = str(exc)
        assert msg == "Module constructor takes either 0 or 1 positional argument"
        ast.Module(nothing=23)

    def test_future(self):
        mod = self.get_ast("from __future__ import with_statement")
        compile(mod, "<test>", "exec")
        mod = self.get_ast(""""I am a docstring."\n
from __future__ import generators""")
        compile(mod, "<test>", "exec")
        mod = self.get_ast("from __future__ import with_statement; import y; " \
                               "from __future__ import nested_scopes")
        raises(SyntaxError, compile, mod, "<test>", "exec")
        mod = self.get_ast("from __future__ import division\nx = 1/2")
        co = compile(mod, "<test>", "exec")
        ns = {}
        exec co in ns
        assert ns["x"] == .5

    def test_field_attr_writable(self):
        import _ast as ast
        x = ast.Num()
        # We can assign to _fields
        x._fields = 666
        assert x._fields == 666

    def test_pickle(self):
        import pickle
        mod = self.get_ast("if y: x = 4")
        co = compile(mod, "<example>", "exec")

        s = pickle.dumps(mod)
        mod2 = pickle.loads(s)
        ns = {"y" : 1}
        co2 = compile(mod2, "<example>", "exec")
        exec co2 in ns
        assert ns["x"] == 4

    def test_classattrs(self):
        import ast
        x = ast.Num()
        assert x._fields == ('n',)
        exc = raises(AttributeError, getattr, x, 'n')
        assert exc.value.args[0] == "'Num' object has no attribute 'n'"

        x = ast.Num(42)
        assert x.n == 42
        exc = raises(AttributeError, getattr, x, 'lineno')
        assert exc.value.args[0] == "'Num' object has no attribute 'lineno'"

        y = ast.Num()
        x.lineno = y
        assert x.lineno == y

        exc = raises(AttributeError, getattr, x, 'foobar')
        assert exc.value.args[0] == "'Num' object has no attribute 'foobar'"

        x = ast.Num(lineno=2)
        assert x.lineno == 2

        x = ast.Num(42, lineno=0)
        assert x.lineno == 0
        assert x._fields == ('n',)
        assert x.n == 42

        raises(TypeError, ast.Num, 1, 2)
        raises(TypeError, ast.Num, 1, 2, lineno=0)

    def test_node_identity(self):
        import _ast as ast
        n1 = ast.Num(1)
        n3 = ast.Num(3)
        addop = ast.Add()
        x = ast.BinOp(n1, addop, n3)
        assert x.left == n1
        assert x.op == addop
        assert x.right == n3

    def test_functiondef(self):
        import _ast as ast
        fAst = ast.FunctionDef(
            name="foo",
            args=ast.arguments(
                args=[], vararg=None, kwarg=None, defaults=[],
                kwonlyargs=[], kw_defaults=[]),
            body=[], decorator_list=[], lineno=5, col_offset=0)
        exprAst = ast.Interactive(body=[fAst])
        compiled = compile(exprAst, "<foo>", "single")
        #
        d = {}
        eval(compiled, d, d)
        assert type(d['foo']) is type(lambda: 42)
        assert d['foo']() is None
