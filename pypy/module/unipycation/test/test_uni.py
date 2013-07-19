import pytest

class AppTestHighLevelInterface(object):
    """ Tests the Highlevel uni.py API sugar """
    spaceconfig = dict(usemodules=('unipycation', ))

    def test_basic(self):
        import uni

        e = uni.Engine("f(666).")
        assert e.db.f(None) == (666, )

    def test_basic2(self):
        import uni

        e = uni.Engine("f(1, 2, 4, 8).")
        assert e.db.f(1, None, 4, None) == (2, 8)

    def test_tautology(self):
        import uni

        e = uni.Engine("f(1).")
        sol = e.db.f(1)
        assert sol == tuple()

    def test_contradiction(self):
        import uni

        e = uni.Engine("f(1).")
        sol = e.db.f(2)
        assert sol == None

    def test_many_solutions1(self):
        import uni
        e = uni.Engine("f(1). f(2). f(3).")
        e.db.f.many_solutions = True

        expect = 1
        for (x, ) in e.db.f(None):
            assert x == expect
            expect += 1

    def test_term_getattrs(self):
        import uni

        e = uni.Engine("f(1,2,3).")
        assert e.terms.f(1, 2, 3) == uni.Term("f", [1, 2, 3])

    def test_term_getattrs2(self):
        import uni

        e = uni.Engine("f(1,2,3).")

        t1 = e.terms.g(666, 667, 668)
        t =  e.terms.f(1, 2, t1)

        assert t == uni.Term("f", [1, 2, uni.Term("g", [666, 667, 668])])

    def test_term_getattrs_listconv(self):
        import uni

        e = uni.Engine("f(1,2,3).")
        t = e.terms.f([212, 313, 414])

        expect = uni.Term("f",[uni.Term(".", [212,
            uni.Term(".", [313, uni.Term(".", [ 414, "[]"])])])])
        assert t == expect

    # Test UndefinedGoal XXX

    def test_append(self):
        import uni

        e = uni.Engine("""
            app([], X, X).
            app([H | T1], T2, [H | T3]) :- app(T1, T2, T3).
        """)
        res = e.db.app([1, 2, 3, 4], [7, 8, 9], None)
        assert res == ([1, 2, 3, 4, 7, 8, 9], )

    # XXX this wont work, as lists are not yet converted
    @pytest.mark.skipif("True")
    def test_append_nondet(self):
        import uni

        e = uni.Engine("app([], X, X). app([H | T1], T2, [H | T3]).")
        e.db.app.many_solutions = True
        for x, y in e.db.app(None, None, [1, 2, 3, 4, 5]):
            assert x + y == [1, 2, 3, 4, 5]

    # XXX this wont work, as lists are not yet converted
    @pytest.mark.skipif("True")
    def test_reverse(self):
        import uni
        e = uni.Engine("""
            rev(X, Y) :- rev_helper(X, [], Y).
            rev_helper([], Acc, Acc).
            rev_helper([H | T], Acc, Res) :- rev_helper(T, [H | Acc], Res).
        """)
        assert e.db.rev([1, 2, 3, 4], None) == [4, 3, 2, 1]

