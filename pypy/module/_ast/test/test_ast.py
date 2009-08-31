import py


class AppTestAST:

    def setup_class(cls):
        cls.w_ast = cls.space.appexec([], """():
    import _ast
    return _ast""")
        cls.w_get_ast = cls.space.appexec([], """():
    def get_ast(source, mode="exec"):
        import _ast as ast
        mod = compile(source, "<test>", mode, ast.PyCF_AST_ONLY)
        assert isinstance(mod, ast.mod)
        return mod
    return get_ast""")

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
        co = compile(mod, "<string>", "exec")
        assert not eval(co)

    def test_string(self):
        mod = self.get_ast("'hi'", "eval")
        s = mod.body
        assert s.s == "hi"
        s.s = "pypy"
        raises(TypeError, setattr, s, "s", 43)
        assert eval(compile(mod, "<test>", "eval")) == "pypy"

    def test_empty_initialization(self):
        ast = self.ast
        def com(node):
            return compile(node, "<test>", "exec")
        mod = ast.Module()
        raises(AttributeError, getattr, mod, "body")
        exc = raises(TypeError, com, mod).value
        assert str(exc) == "required attribute 'body' missing from Module"
        expr = ast.Name()
        expr.id = "hi"
        expr.ctx = ast.Load()
        expr.lineno = 4
        exc = raises(TypeError, com, ast.Module([ast.Expr(expr, 0, 0)])).value
        assert str(exc) == "required attribute 'col_offset' missing from Name"

    def test_int(self):
        ast = self.ast
        imp = ast.ImportFrom("", ["apples"], -1, 0, 0)
        assert imp.level == -1
        imp.level = 3
        assert imp.level == 3

    def test_identifier(self):
        ast = self.ast
        name = ast.Name("name_word", ast.Load(), 0, 0)
        assert name.id == "name_word"
        name.id = "hi"
        assert name.id == "hi"
        raises(TypeError, setattr, name, "id", 32)

    def test_bool(self):
        ast = self.ast
        pr = ast.Print(None, [ast.Name("hi", ast.Load(), 0, 0)], False, 0, 0)
        assert not pr.nl
        assert isinstance(pr.nl, bool)
        pr.nl = True
        assert pr.nl

    def test_object(self):
        ast = self.ast
        const = ast.Const(4, 0, 0)
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
        assign.targets[1] = ast.Name("lemon", ast.Store(), 0, 0)
        name = ast.Name("apple", ast.Store(), 0, 0)
        mod.body.append(ast.Assign([name], ast.Num(4, 0, 0), 0, 0))
        co = compile(mod, "<test>", "exec")
        ns = {}
        exec co in ns
        assert "y" not in ns
        assert ns["x"] == ns["lemon"] == 3
        assert ns["apple"] == 4

    def test_ast_types(self):
        ast = self.ast
        expr = ast.Expr()
        raises(TypeError, setattr, expr, "value", ast.Lt())

    def test_abstract_ast_types(self):
        ast = self.ast
        raises(TypeError, ast.expr)
        raises(TypeError, ast.AST)
        raises(TypeError, type, "X", (ast.AST,), {})
        raises(TypeError, type, "Y", (ast.expr,), {})

    def test_constructor(self):
        ast = self.ast
        body = []
        mod = ast.Module(body)
        assert mod.body is body
        target = ast.Name("hi", ast.Store(), 0, 0)
        expr = ast.Name("apples", ast.Load(), 0, 0)
        otherwise = []
        fr = ast.For(target, expr, body, otherwise, 0, 1)
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
        assert msg == "Module constructor takes 0 or 1 positional arguments"
        raises(AttributeError, ast.Module, nothing=23)

    def test_future(self):
        mod = self.get_ast("from __future__ import with_statement")
        compile(mod, "<test>", "exec")
        mod = self.get_ast(""""I'm a docstring."\n
from __future__ import generators""")
        compile(mod, "<test>", "exec")
        mod = self.get_ast("from __future__ import with_statement; import y; " \
                               "from __future__ import nested_scopes")
        raises(SyntaxError, compile, mod, "<test>", "exec")
