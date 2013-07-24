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

    def test_many_solutions2(self):
        import uni
        e = uni.Engine("f(1, 2). f(2, 3). f(3, 4).")
        e.db.f.many_solutions = True

        xe = 1; ye = 2
        for (x, y) in e.db.f(None, None):
            assert (x, y) == (xe, ye)
            xe += 1
            ye += 1

    def test_many_solutions3(self):
        import uni
        e = uni.Engine("f(card(5, d)). f(card(6, c)).")
        e.db.f.many_solutions = True

        sols = [ x for (x, ) in e.db.f(None) ]
        expect = [ e.terms.card(5, "d"), e.terms.card(6, "c") ]

        assert sols == expect

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

    def test_undefined_goal(self):
        import uni
        e = uni.Engine("f(1,2,3).")
        raises(uni.PrologError, lambda : e.db.g(666))

    def test_append(self):
        import uni

        e = uni.Engine("""
            app([], X, X).
            app([H | T1], T2, [H | T3]) :- app(T1, T2, T3).
        """)
        res = e.db.app([1, 2, 3, 4], [7, 8, 9], None)
        assert res == ([1, 2, 3, 4, 7, 8, 9], )


    def test_emptylist(self):
        import uni

        e = uni.Engine("f([]).")
        (res, ) = e.db.f(None)
        assert res == []

    def test_undefined_list_tail(self):
        import uni
        e = uni.Engine("app([], X, X). app([H | T1], T2, [H | T3]).")
        e.db.app.many_solutions = True

        def should_fail(e):
            # the second solution will have a list like [1|_G0]
            for (x, y) in e.db.app(None, None, [1, 2, 3, 4, 5]): pass

        raises(uni.InstantiationError, lambda : should_fail(e))

    def test_append_nondet(self):
        import uni

        e = uni.Engine("""
            app([], X, X).
            app([H | T1], T2, [H | T3]) :- app(T1, T2, T3).
        """)
        e.db.app.many_solutions = True

        for (x, y) in e.db.app(None, None, [1, 2, 3, 4, 5]):
            assert(type(x) == list)
            assert(type(y) == list)
            assert x + y == [1, 2, 3, 4, 5]

    def test_reverse(self):
        import uni
        e = uni.Engine("""
            rev(X, Y) :- rev_helper(X, [], Y).
            rev_helper([], Acc, Acc).
            rev_helper([H | T], Acc, Res) :- rev_helper(T, [H | Acc], Res).
        """)
        assert e.db.rev([1, 2, 3, 4], None) == ([4, 3, 2, 1], )

    def test_unbound(self):
        import uni

        e = uni.Engine("f(X) :- X = g(_).")
        sol = e.db.f(None)
        assert len(sol[0].args) == 1
        assert type(sol[0].args[0]) == uni.Var

    # (Pdb) p exc
    # Generic1(error, [Generic2(existence_error, [Atom('procedure'), Generic2(/, [Atom('select'), Number(3)])])])
    # This does not belong here XXX
    def test_select(self):
        import uni

        e = uni.Engine("f(X) :- select(1, [1,2,3], X).")
        (res, ) = e.db.f(None)
        assert res == [2, 3]

    def test_pass_up_prolog_error_string(self):
        import uni

        e = uni.Engine("f(X) :- willsmith(1, [1,2,3], X).")
        info = raises(uni.PrologError, e.db.f, None)
        assert str(info.value) == "Undefined procedure: willsmith/3"
