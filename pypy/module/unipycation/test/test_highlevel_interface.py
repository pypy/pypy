import pytest

class AppTestHighLevelInterface(object):
    spaceconfig = dict(usemodules=('unipycation', ))

    def test_basic(self):
        import uni

        e = uni.Engine("f(666).")
        e.db.f.argument_spec[0] = uni.result_converter()
        assert e.db.f() == 666

    def test_many_outvars(self):
        e = uni.Engine("""
            sqrt(X, Sol1, Sol2) :-
                Sol1 is sqrt(X), Sol2 is -Sol1.
        """)
        e.db.sqrt.argument_spec[1] = uni.result_converter()
        e.db.sqrt.argument_spec[2] = uni.result_converter()
        x, y = e.db.sqrt(4)
        assert x == 2
        assert y == -2

    def test_many_solutions(self):
        e = uni.Engine("""
            sqrt(X, Y) :-
                Sol1 is sqrt(X), Sol2 is -Sol1, (Y = Sol1; Y = Sol2).
        """)
        e.db.sqrt.argument_spec[1] = uni.result_converter()
        e.db.sqrt.many_solutions = True
        for x in e.db.sqrt(4):
            assert x ** 2 == 4

    def test_append(self):
        import uni

        e = uni.Engine("app([], X, X). app([H | T1], T2, [H | T3]).")
        e.db.app.argument_spec[2] = uni.result_converter()
        assert e.db.app([1, 2, 3, 4], [7, 8, 9]) == [1, 2, 3, 4, 7, 8, 9]

    def test_reverse(self):
        import uni
        e = uni.Engine("""
            rev(X, Y) :- rev_helper(X, [], Y).
            rev_helper([], Acc, Acc).
            rev_helper([H | T], Acc, Res) :- rev_helper(T, [H | Acc], Res).
        """)
        e.db.rev.argument_spec[1] = uni.result_converter()
        assert e.db.rev([1, 2, 3, 4]) == [4, 3, 2, 1]
