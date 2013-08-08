import pytest

class AppTestCoreEngine(object):
    spaceconfig = dict(usemodules=('unipycation', ))


    def test_basic(self):
        import unipycation
        def f(x):
            return x + 1

        e = unipycation.CoreEngine("f(X) :- python:f(666, X).", {"f": f})
        X = unipycation.Var()
        t = unipycation.Term('f', [X])
        sol = e.query_single(t, [X])

        assert sol[X] == 667

    def test_many_solutions(self):
        import unipycation
        def f(x):
            yield x + 1; yield x + 2; yield x + 3

        e = unipycation.CoreEngine("""
            f(L) :-
                findall(X, python:f(666, X), [A, B, C]),
                L is A + B + C.""",
            {"f": f})
        X = unipycation.Var()
        t = unipycation.Term('f', [X])
        sol = e.query_single(t, [X])

        assert sol[X] == 3 * 666 + 6

    def test_many_solutions_unify(self):
        import unipycation
        def f(x):
            yield x + 1; yield x + 2; yield x + 3

        e = unipycation.CoreEngine("""
            f(L) :-
                python:f(666, 668), L = 1.""",
            {"f": f})
        X = unipycation.Var()
        t = unipycation.Term('f', [X])
        sol = e.query_single(t, [X])

        assert sol[X] == 1

    def test_pass_python_object(self):
        import unipycation
        def returnx(obj):
            return obj.x

        class A(object):
            def f(self):
                return self.x + 1

        a = A()
        a.x = 16

        e = unipycation.CoreEngine("""
            f(L, X) :-
                python:f(L, X).
            method(L, X) :-
                L:f(X).
                """,
            {"f": returnx})
        X = unipycation.Var()
        t = unipycation.Term('f', [a, X])
        sol = e.query_single(t, [X])

        assert sol[X] == 16

        X = unipycation.Var()
        t = unipycation.Term('method', [a, X])
        sol = e.query_single(t, [X])

        assert sol[X] == 17


    def test_attribue_chain(self):
        import unipycation
        def returnx(obj):
            return obj.x

        class A(object):
            def f(self):
                return self.x + 1

        a = A()
        a.a = a
        a.x = 16

        e = unipycation.CoreEngine("""
            method(L, X) :-
                L:a:a:a:f(X).
                """,
            {"f": returnx})
        X = unipycation.Var()
        t = unipycation.Term('method', [a, X])
        sol = e.query_single(t, [X])

        assert sol[X] == 17

    def test_attribute_chain_python(self):
        import unipycation
        def returnx(obj):
            return obj.x

        class A(object):
            def f(self):
                return self.x + 1

        a = A()
        a.a = a
        a.x = 16

        e = unipycation.CoreEngine("""
            method(X) :-
                python:a:a:a:f(X).
                """,
            {"a": a})
        X = unipycation.Var()
        t = unipycation.Term('method', [X])
        sol = e.query_single(t, [X])

        assert sol[X] == 17


    def test_builtins_and_operator(self):
        import unipycation
        def returnx(obj):
            return obj.x

        class A(object):
            def f(self):
                return self.x + 1

        a = A()
        a.a = a
        a.x = 16

        e = unipycation.CoreEngine("""
            method(D) :-
                python:dict(D), python:setitem(D, a, 3, _).
                """,
            {"a": a})
        X = unipycation.Var()
        t = unipycation.Term('method', [X])
        sol = e.query_single(t, [X])

        assert sol[X] == {'a': 3}
