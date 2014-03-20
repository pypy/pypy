import py


class AppTestAST:
    spaceconfig = {
        "usemodules": ['struct', 'binascii'],
    }

    def setup_class(cls):
        cls.w_ast = cls.space.getbuiltinmodule('_ast')

    def w_get_ast(self, source, mode="exec"):
        ast = self.ast
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
        assert eval(compile(mod, "<test>", "eval")) == "pypy"
        s.s = 43
        raises(TypeError, compile, mod, "<test>", "eval")

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

    def test_issue1680_nonseq(self):

        # Test deleting an attribute manually
         
        _ast = self.ast
        mod = self.get_ast("self.attr")
        assert isinstance(mod, _ast.Module)
        assert len(mod.body) == 1
        assert isinstance(mod.body[0], _ast.Expr)
        assert isinstance(mod.body[0].value, _ast.Attribute)
        assert isinstance(mod.body[0].value.value, _ast.Name)
        attr = mod.body[0].value
        assert hasattr(attr, 'value')
        delattr(attr, 'value')
        assert not hasattr(attr, 'value')

        # Test using a node transformer to delete an attribute

        tree = self.get_ast("self.attr2")

        import ast
        class RemoveSelf( ast.NodeTransformer ):
          """NodeTransformer class to remove all references to 'self' in the ast"""
          def visit_Name( self, node ):
            if node.id == 'self':
              return None
            return node

        assert hasattr(tree.body[0].value, 'value')
        #print ast.dump( tree )
        new_tree = RemoveSelf().visit( tree )
        #print ast.dump( new_tree )
        assert not hasattr(new_tree.body[0].value, 'value')

        # Setting an attribute manually, then deleting it

        mod = self.get_ast("class MyClass(object): pass")
        import ast
        assert isinstance(mod.body[0], _ast.ClassDef)
        mod.body[0].name = 42
        delattr(mod.body[0], 'name')
        assert not hasattr(mod.body[0], 'name')

    def test_issue1680_seq(self):

        # Test deleting an attribute manually
         
        _ast = self.ast
        mod = self.get_ast("self.attr")
        assert isinstance(mod, _ast.Module)
        assert len(mod.body) == 1
        assert isinstance(mod.body[0], _ast.Expr)
        assert isinstance(mod.body[0].value, _ast.Attribute)
        assert isinstance(mod.body[0].value.value, _ast.Name)
        assert hasattr(mod, 'body')
        delattr(mod, 'body')
        assert not hasattr(mod, 'body')

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
        import ast
        fAst = ast.FunctionDef(
            name="foo",
            args=ast.arguments(
                args=[], vararg=None, kwarg=None, defaults=[],
                kwonlyargs=[], kw_defaults=[]),
            body=[ast.Expr(ast.Str('docstring'))],
            decorator_list=[], lineno=5, col_offset=0)
        exprAst = ast.Interactive(body=[fAst])
        ast.fix_missing_locations(exprAst)
        compiled = compile(exprAst, "<foo>", "single")
        #
        d = {}
        eval(compiled, d, d)
        assert type(d['foo']) is type(lambda: 42)
        assert d['foo']() is None

    def test_missing_name(self):
        import _ast as ast
        n = ast.FunctionDef(name=None)
        n.name = "foo"
        n.name = "foo"
        n.name = "foo"
        assert n.name == "foo"

    def test_issue793(self):
        import _ast as ast
        body = ast.Module([
            ast.TryExcept([ast.Pass(lineno=2, col_offset=4)],
                [ast.ExceptHandler(ast.Name('Exception', ast.Load(),
                                            lineno=3, col_offset=0),
                                   None, [], lineno=4, col_offset=0)],
                [], lineno=1, col_offset=0)
        ])
        exec compile(body, '<string>', 'exec')

    def test_empty_set(self):
        import ast
        m = ast.Module(body=[ast.Expr(value=ast.Set(elts=[]))])
        ast.fix_missing_locations(m)
        compile(m, "<test>", "exec")

    def test_invalid_sum(self):
        import _ast as ast
        pos = dict(lineno=2, col_offset=3)
        m = ast.Module([ast.Expr(ast.expr(**pos), **pos)])
        exc = raises(TypeError, compile, m, "<test>", "exec")

    def test_invalid_identitifer(self):
        import ast
        m = ast.Module([ast.Expr(ast.Name(u"x", ast.Load()))])
        ast.fix_missing_locations(m)
        exc = raises(TypeError, compile, m, "<test>", "exec")

    def test_invalid_string(self):
        import ast
        m = ast.Module([ast.Expr(ast.Str(43))])
        ast.fix_missing_locations(m)
        exc = raises(TypeError, compile, m, "<test>", "exec")

    def test_hacked_lineno(self):
        import _ast
        stmt = '''if 1:
            try:
                foo
            except Exception as error:
                bar
            except Baz as error:
                bar
            '''
        mod = compile(stmt, "<test>", "exec", _ast.PyCF_ONLY_AST)
        # These lineno are invalid, but should not crash the interpreter.
        mod.body[0].body[0].handlers[0].lineno = 7
        mod.body[0].body[0].handlers[1].lineno = 6
        code = compile(mod, "<test>", "exec")
        
    def test_dict_astNode(self):
        import ast
        num_node = ast.Num(n=2, lineno=2, col_offset=3)
        dict_res = num_node.__dict__
        assert dict_res == {'n':2, 'lineno':2, 'col_offset':3}

    def test_issue1673_Num_notfullinit(self):
        import ast
        import copy
        num_node = ast.Num(n=2,lineno=2)
        assert num_node.n == 2
        assert num_node.lineno == 2
        num_node2 = copy.deepcopy(num_node)

    def test_issue1673_Num_fullinit(self):
        import ast
        import copy 
        num_node = ast.Num(n=2,lineno=2,col_offset=3)
        num_node2 = copy.deepcopy(num_node)
        assert num_node.n == num_node2.n
        assert num_node.lineno == num_node2.lineno
        assert num_node.col_offset == num_node2.col_offset
            
    def test_issue1673_Str(self):
        import ast
        import copy
        str_node = ast.Str(n=2,lineno=2)
        assert str_node.n == 2
        assert str_node.lineno == 2
        str_node2 = copy.deepcopy(str_node)

