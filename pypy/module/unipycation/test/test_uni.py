import pytest
import tempfile

class AppTestHighLevelInterface(object):
    """ Tests the Highlevel uni.py API sugar """
    spaceconfig = dict(usemodules=('unipycation', ))

    def setup_class(cls):
        space = cls.space
        (fd, fname) = tempfile.mkstemp(prefix="unipycation-")
        cls.w_fd = space.wrap(fd)
        cls.w_fname = space.wrap(fname)

    def test_basic(self):
        import uni

        e = uni.Engine("f(666).")
        assert e.db.f(None) == (666, )

    def test_basic2(self):
        import uni

        e = uni.Engine("f(1, 2, 4, 8).")
        assert e.db.f(1, None, 4, None) == (2, 8)

    def test_from_file(self):
        import uni
        import os
        fd = self.fd
        fname = self.fname

        os.write(fd, "f(1,2,3).")
        os.close(fd)

        e = uni.Engine.from_file(fname)
        os.unlink(fname)

        sol = e.db.f(None, None, None)
        assert sol == (1, 2, 3)

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

    def test_iter1(self):
        import uni
        e = uni.Engine("f(1). f(2). f(3).")

        expect = 1
        for (x, ) in e.db.f.iter(None):
            assert x == expect
            expect += 1

    def test_iter2(self):
        import uni
        e = uni.Engine("f(1, 2). f(2, 3). f(3, 4).")

        xe = 1; ye = 2
        for (x, y) in e.db.f.iter(None, None):
            assert (x, y) == (xe, ye)
            xe += 1
            ye += 1

    def test_iter3(self):
        import uni
        e = uni.Engine("f(card(5, d)). f(card(6, c)).")

        sols = [ x for (x, ) in e.db.f.iter(None) ]
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
        info = raises(uni.PrologError, lambda : e.db.g(666))

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

        def should_fail(e):
            # the second solution will have a list like [1|_G0]
            for (x, y) in e.db.app.iter(None, None, [1, 2, 3, 4, 5]): pass

        raises(uni.InstantiationError, lambda : should_fail(e))

    def test_weird_list(self):
        import uni
        e = uni.Engine("f('.'(a, b)).")
        result, = e.db.f(None)
        assert result == uni.Term('.', ["a", "b"])

    def test_append_nondet(self):
        import uni

        e = uni.Engine("""
            app([], X, X).
            app([H | T1], T2, [H | T3]) :- app(T1, T2, T3).
        """)

        for (x, y) in e.db.app.iter(None, None, [1, 2, 3, 4, 5]):
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

    def test_pass_up_prolog_error(self):
        import uni

        e = uni.Engine("f(X) :- willsmith(1, [1,2,3], X).")
        info = raises(uni.PrologError, e.db.f, None)
        assert str(info.value.term) == "error(existence_error(procedure, willsmith/3))"
        # check error string
        assert str(info.value) == "Undefined procedure: willsmith/3"

    def test_call_python(self):
        import uni

        def f(x):
            return x + 1

        e = uni.Engine("f(X) :- python:f(15, X).", locals())
        x, = e.db.f(None)
        assert x == 16

    def test_paper_cls_example(self):
        import uni

        e = uni.Engine("""
        baseclass(A, A).
        baseclass(A, B) :-
            python:getattr(A, '__base__', Base),
            baseclass(Base, B).

        hasmethod(A, Method) :-
            A:'__dict__':iterkeys(Method).

        baseclass_defining_method(A, Method, Base) :-
            baseclass(A, Base),
            hasmethod(Base, Method).

        """)

            #python:getattr(A, '__dict__', Dict),
            #contains(Dict, Method).

        class A(object):
            def f(self):
                pass

        class B(A):
            def g(self):
                pass

        class C(A):
            def f(self):
                pass

        assert e.db.baseclass_defining_method(B, 'f', None) == (A, )

    def test_list_in_term(self):
        import uni

        e = uni.Engine("f(g([c(0, 0)])).")
        (g, ) = e.db.f(None)
        assert isinstance(g, uni.Term)
        assert g.name == "g"
        assert len(g) == 1
        assert g[0] == [uni.Term('c', [0, 0])]
        assert isinstance(g.args[0], list)
