import pytest

class AppTestHighLevelInterface(object):
    spaceconfig = dict(usemodules=('unipycation', ))

    def test_basic(self):
        import uni

        e = uni.Engine2("f(666).")
        assert e.db.f(None) == (666, )

    def test_basic2(self):
        import uni

        e = uni.Engine2("f(1, 2, 4, 8).")
        assert e.db.f(1, None, 4, None) == (2, 8)

    def test_tautology(self):
        import uni

        e = uni.Engine2("f(1).")
        sol = e.db.f(1)
        assert sol == tuple()

    def test_contradiction(self):
        import uni

        e = uni.Engine2("f(1).")
        sol = e.db.f(2)
        assert sol == None

    def test_many_solutions1(self):
        import uni
        e = uni.Engine2("f(1). f(2). f(3).")
        e.db.f.many_solutions = True

        expect = 1
        for (x, ) in e.db.f(None):
            assert x == expect
            expect += 1

    # Test UndefinedGoal XXX

    # XXX this wont work, as lists are not yet converted
    @pytest.mark.skipif("True")
    def test_append(self):
        import uni

        e = uni.Engine2("app([], X, X). app([H | T1], T2, [H | T3]).")
        assert e.db.app([1, 2, 3, 4], [7, 8, 9], None) == [1, 2, 3, 4, 7, 8, 9]

    # XXX this wont work, as lists are not yet converted
    @pytest.mark.skipif("True")
    def test_append_nondet(self):
        import uni

        e = uni.Engine2("app([], X, X). app([H | T1], T2, [H | T3]).")
        e.db.app.many_solutions = True
        for x, y in e.db.app(None, None, [1, 2, 3, 4, 5]):
            assert x + y == [1, 2, 3, 4, 5]

    # XXX this wont work, as lists are not yet converted
    @pytest.mark.skipif("True")
    def test_reverse(self):
        import uni
        e = uni.Engine2("""
            rev(X, Y) :- rev_helper(X, [], Y).
            rev_helper([], Acc, Acc).
            rev_helper([H | T], Acc, Res) :- rev_helper(T, [H | Acc], Res).
        """)
        assert e.db.rev([1, 2, 3, 4], None) == [4, 3, 2, 1]

