import pytest

class AppTestHighLevelInterface(object):
    spaceconfig = dict(usemodules=('unipycation', ))

    def test_basic(self):
        import uni

        e = uni.Engine("f(666).")
        assert e.db.f(None) == 666

    def test_many_outvars(self):
        e = uni.Engine("""
            sqrt(X, Sol1, Sol2) :-
                Sol1 is sqrt(X), Sol2 is -Sol1.
        """)
        x, y = e.db.sqrt(4, None, None)
        assert x == 2
        assert y == -2

    def test_many_solutions(self):
        e = uni.Engine("""
            sqrt(X, Y) :-
                Sol1 is sqrt(X), Sol2 is -Sol1, (Y = Sol1; Y = Sol2).
        """)
        e.db.sqrt.many_solutions = True
        for x in e.db.sqrt(4, None):
            assert x ** 2 == 4

    def test_append(self):
        import uni

        e = uni.Engine("app([], X, X). app([H | T1], T2, [H | T3]).")
        assert e.db.app([1, 2, 3, 4], [7, 8, 9], None) == [1, 2, 3, 4, 7, 8, 9]

    def test_append_nondet(self):
        import uni

        e = uni.Engine("app([], X, X). app([H | T1], T2, [H | T3]).")
        e.db.app.many_solutions = True
        for x, y in e.db.app(None, None, [1, 2, 3, 4, 5]):
            assert x + y == [1, 2, 3, 4, 5]

    def test_reverse(self):
        import uni
        e = uni.Engine("""
            rev(X, Y) :- rev_helper(X, [], Y).
            rev_helper([], Acc, Acc).
            rev_helper([H | T], Acc, Res) :- rev_helper(T, [H | Acc], Res).
        """)
        assert e.db.rev([1, 2, 3, 4], None) == [4, 3, 2, 1]
