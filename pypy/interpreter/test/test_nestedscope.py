

class AppTestNestedScope:

    def test_nested_scope(self):
        x = 42
        def f(): return x
        assert f() == 42

    def test_nested_scope2(self):
        x = 42
        y = 3
        def f(): return x
        assert f() == 42

    def test_nested_scope3(self):
        x = 42
        def f():
            def g():
                return x
            return g
        assert f()() == 42

    def test_nested_scope4(self):
        def f():
            x = 3
            def g():
                return x
            a = g()
            x = 4
            b = g()
            return (a, b)
        assert f() == (3, 4)

    def test_nested_scope_locals(self):
        def f():
            x = 3
            def g():
                i = x
                return locals()
            return g()
        d = f()
        assert d == {'i':3, 'x':3}

    def test_deeply_nested_scope_locals(self):
        def f():
            x = 3
            def g():
                def h():
                    i = x
                    return locals()
                return locals(), h()
            return g()
        outer_locals, inner_locals = f()
        assert inner_locals == {'i':3, 'x':3}
        keys = outer_locals.keys()
        keys.sort()
        assert keys == ['h', 'x']

    def test_lambda_in_genexpr(self):
        assert eval('map(apply, (lambda: t for t in range(10)))') == range(10)

    def test_cell_contents(self):
        def f(x):
            def f(y):
                return x + y
            return f

        g = f(10)
        assert g.func_closure[0].cell_contents == 10

    def test_empty_cell_contents(self):

        def f():
            def f(y):
                  return x + y
            return f
            x = 1

        g = f()
        raises(ValueError, "g.func_closure[0].cell_contents")

    def test_compare_cells(self):
        def f(n):
            if n:
                x = 42
            def f(y):
                  return x + y
            return f

        g0 = f(0).func_closure[0]
        g1 = f(1).func_closure[0]
        assert cmp(g0, g1) == -1

    def test_leaking_class_locals(self):
        def f(x):
            class X:
                x = 12
                def f(self):
                    return x
                locals()
            return X
        assert f(1).x == 12

    def test_nested_scope_locals_mutating_cellvars(self):
        def f():
            x = 12
            def m():
                locals()
                x
                locals()
                return x
            return m
        assert f()() == 12
