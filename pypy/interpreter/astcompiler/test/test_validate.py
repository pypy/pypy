import os
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.astcompiler import ast
from pypy.interpreter.astcompiler import validate

class TestASTValidator:
    def mod(self, mod, msg=None, mode="exec", exc=validate.ValidationError):
        space = self.space
        if isinstance(exc, W_Root):
            w_exc = exc
            exc = OperationError
        else:
            w_exc = None
        with raises(exc) as cm:
            validate.validate_ast(space, mod)
        if w_exc is not None:
            w_value = cm.value.get_w_value(space)
            assert cm.value.match(space, w_exc)
            exc_msg = str(cm.value)
        else:
            exc_msg = str(cm.value)
        if msg is not None:
            assert msg in exc_msg

    def expr(self, node, msg=None, exc=validate.ValidationError):
        mod = ast.Module([ast.Expr(node, 0, 0)])
        self.mod(mod, msg, exc=exc)

    def stmt(self, stmt, msg=None):
        mod = ast.Module([stmt])
        self.mod(mod, msg)

    def test_module(self):
        m = ast.Interactive([ast.Expr(ast.Name("x", ast.Store, 0, 0), 0, 0)])
        self.mod(m, "must have Load context", "single")
        m = ast.Expression(ast.Name("x", ast.Store, 0, 0))
        self.mod(m, "must have Load context", "eval")

    def _check_arguments(self, fac, check):
        def arguments(args=None, vararg=None, kwonlyargs=None,
                      kw_defaults=None, kwarg=None, defaults=None):
            if args is None:
                args = []
            if kwonlyargs is None:
                kwonlyargs = []
            if defaults is None:
                defaults = []
            if kw_defaults is None:
                kw_defaults = []
            args = ast.arguments(args, vararg, kwonlyargs,
                                 kw_defaults, kwarg, defaults)
            return fac(args)
        args = [ast.arg("x", ast.Name("x", ast.Store, 0, 0))]
        check(arguments(args=args), "must have Load context")
        check(arguments(kwonlyargs=args), "must have Load context")
        check(arguments(defaults=[ast.Num(self.space.wrap(3), 0, 0)]),
                       "more positional defaults than args")
        check(arguments(kw_defaults=[ast.Num(self.space.wrap(4), 0, 0)]),
                       "length of kwonlyargs is not the same as kw_defaults")
        args = [ast.arg("x", ast.Name("x", ast.Load, 0, 0))]
        check(arguments(args=args, defaults=[ast.Name("x", ast.Store, 0, 0)]),
                       "must have Load context")
        args = [ast.arg("a", ast.Name("x", ast.Load, 0, 0)),
                ast.arg("b", ast.Name("y", ast.Load, 0, 0))]
        check(arguments(kwonlyargs=args,
                          kw_defaults=[None, ast.Name("x", ast.Store, 0, 0)]),
                          "must have Load context")

    def test_funcdef(self):
        a = ast.arguments([], None, [], [], None, [])
        f = ast.FunctionDef("x", a, [], [], None, 0, 0)
        self.stmt(f, "empty body on FunctionDef")
        f = ast.FunctionDef("x", a, [ast.Pass(0, 0)], [ast.Name("x", ast.Store, 0, 0)],
                            None, 0, 0)
        self.stmt(f, "must have Load context")
        f = ast.FunctionDef("x", a, [ast.Pass(0, 0)], [],
                            ast.Name("x", ast.Store, 0, 0), 0, 0)
        self.stmt(f, "must have Load context")
        def fac(args):
            return ast.FunctionDef("x", args, [ast.Pass(0, 0)], [], None, 0, 0)
        self._check_arguments(fac, self.stmt)

    def test_classdef(self):
        def cls(bases=None, keywords=None, body=None, decorator_list=None):
            if bases is None:
                bases = []
            if keywords is None:
                keywords = []
            if body is None:
                body = [ast.Pass(0, 0)]
            if decorator_list is None:
                decorator_list = []
            return ast.ClassDef("myclass", bases, keywords,
                                body, decorator_list, 0, 0)
        self.stmt(cls(bases=[ast.Name("x", ast.Store, 0, 0)]),
                  "must have Load context")
        self.stmt(cls(keywords=[ast.keyword("x", ast.Name("x", ast.Store, 0, 0))]),
                  "must have Load context")
        self.stmt(cls(body=[]), "empty body on ClassDef")
        self.stmt(cls(body=[None]), "None disallowed")
        self.stmt(cls(decorator_list=[ast.Name("x", ast.Store, 0, 0)]),
                  "must have Load context")

    def test_delete(self):
        self.stmt(ast.Delete([], 0, 0), "empty targets on Delete")
        self.stmt(ast.Delete([None], 0, 0), "None disallowed")
        self.stmt(ast.Delete([ast.Name("x", ast.Load, 0, 0)], 0, 0),
                  "must have Del context")

    def test_assign(self):
        self.stmt(ast.Assign([], ast.Num(self.space.wrap(3), 0, 0), 0, 0), "empty targets on Assign")
        self.stmt(ast.Assign([None], ast.Num(self.space.wrap(3), 0, 0), 0, 0), "None disallowed")
        self.stmt(ast.Assign([ast.Name("x", ast.Load, 0, 0)], ast.Num(self.space.wrap(3), 0, 0), 0, 0),
                  "must have Store context")
        self.stmt(ast.Assign([ast.Name("x", ast.Store, 0, 0)],
                                ast.Name("y", ast.Store, 0, 0), 0, 0),
                  "must have Load context")

    def test_augassign(self):
        aug = ast.AugAssign(ast.Name("x", ast.Load, 0, 0), ast.Add,
                            ast.Name("y", ast.Load, 0, 0), 0, 0)
        self.stmt(aug, "must have Store context")
        aug = ast.AugAssign(ast.Name("x", ast.Store, 0, 0), ast.Add,
                            ast.Name("y", ast.Store, 0, 0), 0, 0)
        self.stmt(aug, "must have Load context")

    def test_for(self):
        x = ast.Name("x", ast.Store, 0, 0)
        y = ast.Name("y", ast.Load, 0, 0)
        p = ast.Pass(0, 0)
        self.stmt(ast.For(x, y, [], [], 0, 0), "empty body on For")
        self.stmt(ast.For(ast.Name("x", ast.Load, 0, 0), y, [p], [], 0, 0),
                  "must have Store context")
        self.stmt(ast.For(x, ast.Name("y", ast.Store, 0, 0), [p], [], 0, 0),
                  "must have Load context")
        e = ast.Expr(ast.Name("x", ast.Store, 0, 0), 0, 0)
        self.stmt(ast.For(x, y, [e], [], 0, 0), "must have Load context")
        self.stmt(ast.For(x, y, [p], [e], 0, 0), "must have Load context")

    def test_while(self):
        self.stmt(ast.While(ast.Num(self.space.wrap(3), 0, 0), [], [], 0, 0), "empty body on While")
        self.stmt(ast.While(ast.Name("x", ast.Store, 0, 0), [ast.Pass(0, 0)], [], 0, 0),
                  "must have Load context")
        self.stmt(ast.While(ast.Num(self.space.wrap(3), 0, 0), [ast.Pass(0, 0)],
                             [ast.Expr(ast.Name("x", ast.Store, 0, 0), 0, 0)], 0, 0),
                             "must have Load context")

    def test_if(self):
        self.stmt(ast.If(ast.Num(self.space.wrap(3), 0, 0), [], [], 0, 0), "empty body on If")
        i = ast.If(ast.Name("x", ast.Store, 0, 0), [ast.Pass(0, 0)], [], 0, 0)
        self.stmt(i, "must have Load context")
        i = ast.If(ast.Num(self.space.wrap(3), 0, 0), [ast.Expr(ast.Name("x", ast.Store, 0, 0), 0, 0)], [], 0, 0)
        self.stmt(i, "must have Load context")
        i = ast.If(ast.Num(self.space.wrap(3), 0, 0), [ast.Pass(0, 0)],
                   [ast.Expr(ast.Name("x", ast.Store, 0, 0), 0, 0)], 0, 0)
        self.stmt(i, "must have Load context")

    def test_with(self):
        p = ast.Pass(0, 0)
        self.stmt(ast.With([], [p], 0, 0), "empty items on With")
        i = ast.withitem(ast.Num(self.space.wrap(3), 0, 0), None)
        self.stmt(ast.With([i], [], 0, 0), "empty body on With")
        i = ast.withitem(ast.Name("x", ast.Store, 0, 0), None)
        self.stmt(ast.With([i], [p], 0, 0), "must have Load context")
        i = ast.withitem(ast.Num(self.space.wrap(3), 0, 0), ast.Name("x", ast.Load, 0, 0))
        self.stmt(ast.With([i], [p], 0, 0), "must have Store context")

    def test_raise(self):
        r = ast.Raise(None, ast.Num(self.space.wrap(3), 0, 0), 0, 0)
        self.stmt(r, "Raise with cause but no exception")
        r = ast.Raise(ast.Name("x", ast.Store, 0, 0), None, 0, 0)
        self.stmt(r, "must have Load context")
        r = ast.Raise(ast.Num(self.space.wrap(4), 0, 0), ast.Name("x", ast.Store, 0, 0), 0, 0)
        self.stmt(r, "must have Load context")

    def test_try(self):
        p = ast.Pass(0, 0)
        t = ast.Try([], [], [], [p], 0, 0)
        self.stmt(t, "empty body on Try")
        t = ast.Try([ast.Expr(ast.Name("x", ast.Store, 0, 0), 0, 0)], [], [], [p], 0, 0)
        self.stmt(t, "must have Load context")
        t = ast.Try([p], [], [], [], 0, 0)
        self.stmt(t, "Try has neither except handlers nor finalbody")
        t = ast.Try([p], [], [p], [p], 0, 0)
        self.stmt(t, "Try has orelse but no except handlers")
        t = ast.Try([p], [ast.ExceptHandler(None, "x", [], 0, 0)], [], [], 0, 0)
        self.stmt(t, "empty body on ExceptHandler")
        e = [ast.ExceptHandler(ast.Name("x", ast.Store, 0, 0), "y", [p], 0, 0)]
        self.stmt(ast.Try([p], e, [], [], 0, 0), "must have Load context")
        e = [ast.ExceptHandler(None, "x", [p], 0, 0)]
        t = ast.Try([p], e, [ast.Expr(ast.Name("x", ast.Store, 0, 0), 0, 0)], [p], 0, 0)
        self.stmt(t, "must have Load context")
        t = ast.Try([p], e, [p], [ast.Expr(ast.Name("x", ast.Store, 0, 0), 0, 0)], 0, 0)
        self.stmt(t, "must have Load context")

    def test_assert(self):
        self.stmt(ast.Assert(ast.Name("x", ast.Store, 0, 0), None, 0, 0),
                  "must have Load context")
        assrt = ast.Assert(ast.Name("x", ast.Load, 0, 0),
                           ast.Name("y", ast.Store, 0, 0), 0, 0)
        self.stmt(assrt, "must have Load context")

    def test_import(self):
        self.stmt(ast.Import([], 0, 0), "empty names on Import")

    def test_importfrom(self):
        imp = ast.ImportFrom(None, [ast.alias("x", None)], -42, 0, 0)
        self.stmt(imp, "level less than -1")
        self.stmt(ast.ImportFrom(None, [], 0, 0, 0), "empty names on ImportFrom")

    def test_global(self):
        self.stmt(ast.Global([], 0, 0), "empty names on Global")

    def test_nonlocal(self):
        self.stmt(ast.Nonlocal([], 0, 0), "empty names on Nonlocal")

    def test_expr(self):
        e = ast.Expr(ast.Name("x", ast.Store, 0, 0), 0, 0)
        self.stmt(e, "must have Load context")

    def test_boolop(self):
        b = ast.BoolOp(ast.And, [], 0, 0)
        self.expr(b, "less than 2 values")
        b = ast.BoolOp(ast.And, None, 0, 0)
        self.expr(b, "less than 2 values")
        b = ast.BoolOp(ast.And, [ast.Num(self.space.wrap(3), 0, 0)], 0, 0)
        self.expr(b, "less than 2 values")
        b = ast.BoolOp(ast.And, [ast.Num(self.space.wrap(4), 0, 0), None], 0, 0)
        self.expr(b, "None disallowed")
        b = ast.BoolOp(ast.And, [ast.Num(self.space.wrap(4), 0, 0), ast.Name("x", ast.Store, 0, 0)], 0, 0)
        self.expr(b, "must have Load context")

    def test_unaryop(self):
        u = ast.UnaryOp(ast.Not, ast.Name("x", ast.Store, 0, 0), 0, 0)
        self.expr(u, "must have Load context")

    def test_lambda(self):
        a = ast.arguments([], None, [], [], None, [])
        self.expr(ast.Lambda(a, ast.Name("x", ast.Store, 0, 0), 0, 0),
                  "must have Load context")
        def fac(args):
            return ast.Lambda(args, ast.Name("x", ast.Load, 0, 0), 0, 0)
        self._check_arguments(fac, self.expr)

    def test_ifexp(self):
        l = ast.Name("x", ast.Load, 0, 0)
        s = ast.Name("y", ast.Store, 0, 0)
        for args in (s, l, l), (l, s, l), (l, l, s):
            self.expr(ast.IfExp(*(args + (0, 0))), "must have Load context")

    def test_dict(self):
        d = ast.Dict([], [ast.Name("x", ast.Load, 0, 0)], 0, 0)
        self.expr(d, "same number of keys as values")
        d = ast.Dict([None], [ast.Name("x", ast.Load, 0, 0)], 0, 0)
        self.expr(d, "None disallowed")
        d = ast.Dict([ast.Name("x", ast.Load, 0, 0)], [None], 0, 0)
        self.expr(d, "None disallowed")

    def test_set(self):
        self.expr(ast.Set([None], 0, 0), "None disallowed")
        s = ast.Set([ast.Name("x", ast.Store, 0, 0)], 0, 0)
        self.expr(s, "must have Load context")

    def _check_comprehension(self, fac):
        self.expr(fac([]), "comprehension with no generators")
        g = ast.comprehension(ast.Name("x", ast.Load, 0, 0),
                              ast.Name("x", ast.Load, 0, 0), [])
        self.expr(fac([g]), "must have Store context")
        g = ast.comprehension(ast.Name("x", ast.Store, 0, 0),
                              ast.Name("x", ast.Store, 0, 0), [])
        self.expr(fac([g]), "must have Load context")
        x = ast.Name("x", ast.Store, 0, 0)
        y = ast.Name("y", ast.Load, 0, 0)
        g = ast.comprehension(x, y, [None])
        self.expr(fac([g]), "None disallowed")
        g = ast.comprehension(x, y, [ast.Name("x", ast.Store, 0, 0)])
        self.expr(fac([g]), "must have Load context")

    def _simple_comp(self, fac):
        g = ast.comprehension(ast.Name("x", ast.Store, 0, 0),
                              ast.Name("x", ast.Load, 0, 0), [])
        self.expr(fac(ast.Name("x", ast.Store, 0, 0), [g], 0, 0),
                  "must have Load context")
        def wrap(gens):
            return fac(ast.Name("x", ast.Store, 0, 0), gens, 0, 0)
        self._check_comprehension(wrap)

    def test_listcomp(self):
        self._simple_comp(ast.ListComp)

    def test_setcomp(self):
        self._simple_comp(ast.SetComp)

    def test_generatorexp(self):
        self._simple_comp(ast.GeneratorExp)

    def test_dictcomp(self):
        g = ast.comprehension(ast.Name("y", ast.Store, 0, 0),
                              ast.Name("p", ast.Load, 0, 0), [])
        c = ast.DictComp(ast.Name("x", ast.Store, 0, 0),
                         ast.Name("y", ast.Load, 0, 0), [g], 0, 0)
        self.expr(c, "must have Load context")
        c = ast.DictComp(ast.Name("x", ast.Load, 0, 0),
                         ast.Name("y", ast.Store, 0, 0), [g], 0, 0)
        self.expr(c, "must have Load context")
        def factory(comps):
            k = ast.Name("x", ast.Load, 0, 0)
            v = ast.Name("y", ast.Load, 0, 0)
            return ast.DictComp(k, v, comps, 0, 0)
        self._check_comprehension(factory)

    def test_yield(self):
        self.expr(ast.Yield(ast.Name("x", ast.Store, 0, 0), 0, 0), "must have Load")
        self.expr(ast.YieldFrom(ast.Name("x", ast.Store, 0, 0), 0, 0), "must have Load")

    def test_compare(self):
        left = ast.Name("x", ast.Load, 0, 0)
        comp = ast.Compare(left, [ast.In], [], 0, 0)
        self.expr(comp, "no comparators")
        comp = ast.Compare(left, [ast.In], [ast.Num(self.space.wrap(4), 0, 0), ast.Num(self.space.wrap(5), 0, 0)], 0, 0)
        self.expr(comp, "different number of comparators and operands")
        comp = ast.Compare(ast.Num(self.space.wrap("blah"), 0, 0), [ast.In], [left], 0, 0)
        self.expr(comp, "non-numeric", exc=self.space.w_TypeError)
        comp = ast.Compare(left, [ast.In], [ast.Num(self.space.wrap("blah"), 0, 0)], 0, 0)
        self.expr(comp, "non-numeric", exc=self.space.w_TypeError)

    def test_call(self):
        func = ast.Name("x", ast.Load, 0, 0)
        args = [ast.Name("y", ast.Load, 0, 0)]
        keywords = [ast.keyword("w", ast.Name("z", ast.Load, 0, 0))]
        call = ast.Call(ast.Name("x", ast.Store, 0, 0), args, keywords, 0, 0)
        self.expr(call, "must have Load context")
        call = ast.Call(func, [None], keywords, 0, 0)
        self.expr(call, "None disallowed")
        bad_keywords = [ast.keyword("w", ast.Name("z", ast.Store, 0, 0))]
        call = ast.Call(func, args, bad_keywords, 0, 0)
        self.expr(call, "must have Load context")

    def test_num(self):
        space = self.space
        w_objs = space.appexec([], """():
        class subint(int):
            pass
        class subfloat(float):
            pass
        class subcomplex(complex):
            pass
        return ("0", "hello", subint(), subfloat(), subcomplex())
        """)
        for w_obj in space.unpackiterable(w_objs):
            self.expr(ast.Num(w_obj, 0, 0), "non-numeric", exc=self.space.w_TypeError)

    def test_attribute(self):
        attr = ast.Attribute(ast.Name("x", ast.Store, 0, 0), "y", ast.Load, 0, 0)
        self.expr(attr, "must have Load context")

    def test_subscript(self):
        sub = ast.Subscript(ast.Name("x", ast.Store, 0, 0), ast.Index(ast.Num(self.space.wrap(3), 0, 0)),
                            ast.Load, 0, 0)
        self.expr(sub, "must have Load context")
        x = ast.Name("x", ast.Load, 0, 0)
        sub = ast.Subscript(x, ast.Index(ast.Name("y", ast.Store, 0, 0)),
                            ast.Load, 0, 0)
        self.expr(sub, "must have Load context")
        s = ast.Name("x", ast.Store, 0, 0)
        for args in (s, None, None), (None, s, None), (None, None, s):
            sl = ast.Slice(*args)
            self.expr(ast.Subscript(x, sl, ast.Load, 0, 0),
                      "must have Load context")
        sl = ast.ExtSlice([])
        self.expr(ast.Subscript(x, sl, ast.Load, 0, 0), "empty dims on ExtSlice")
        sl = ast.ExtSlice([ast.Index(s)])
        self.expr(ast.Subscript(x, sl, ast.Load, 0, 0), "must have Load context")

    def test_starred(self):
        left = ast.List([ast.Starred(ast.Name("x", ast.Load, 0, 0), ast.Store, 0, 0)],
                        ast.Store, 0, 0)
        assign = ast.Assign([left], ast.Num(self.space.wrap(4), 0, 0), 0, 0)
        self.stmt(assign, "must have Store context")

    def _sequence(self, fac):
        self.expr(fac([None], ast.Load, 0, 0), "None disallowed")
        self.expr(fac([ast.Name("x", ast.Store, 0, 0)], ast.Load, 0, 0),
                  "must have Load context")

    def test_list(self):
        self._sequence(ast.List)

    def test_tuple(self):
        self._sequence(ast.Tuple)

    def test_nameconstant(self):
        node = ast.NameConstant("True", 0, 0)
        self.expr(node, "singleton must be True, False, or None")

    def test_stdlib_validates(self):
        stdlib = os.path.join(os.path.dirname(ast.__file__), '../../../lib-python/3')
        if 1:    # enable manually for a complete test
            tests = [fn for fn in os.listdir(stdlib) if fn.endswith('.py')]
            tests += ['test/'+fn for fn in os.listdir(stdlib+'/test')
                                 if fn.endswith('.py')
                                    and not fn.startswith('bad')]
            tests.sort()
        else:
            tests = ["os.py", "test/test_grammar.py", "test/test_unpack_ex.py"]
        #
        for module in tests:
            fn = os.path.join(stdlib, module)
            print 'compiling', fn
            with open(fn, "r") as fp:
                source = fp.read()
            ec = self.space.getexecutioncontext()
            ast_node = ec.compiler.compile_to_ast(source, fn, "exec", 0)
            ec.compiler.validate_ast(ast_node)
