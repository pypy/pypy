import pypy.module.unipycation.engine as eng
import pytest

class AppTestEngine(object):
    spaceconfig = dict(usemodules=('unipycation',))

    def test_basic(self):
        import unipycation

        e = unipycation.Engine("likes(mac, jazz). likes(bob, jazz). likes(jim, funk).")
        assert isinstance(e, unipycation.Engine)

        res = e.query_single("likes(X, jazz).")
        assert res["X"] == "mac"

    def test_basic_2(self):
        import unipycation

        e = unipycation.Engine("f(1, a). f(2, b). f(3, c).")
        assert isinstance(e, unipycation.Engine)

        res = e.query_single("f(X, Y).")
        assert res["X"] == 1

    def test_basic_3(self):
        import unipycation

        e = unipycation.Engine("f(1.23456).")
        assert isinstance(e, unipycation.Engine)

        res = e.query_single("f(X).")
        assert res["X"] == 1.23456

    def test_anonymous(self):
        import unipycation

        e = unipycation.Engine("f(1, a). f(2, b). f(3, c).")
        assert isinstance(e, unipycation.Engine)

        res = e.query_single("f(_, Y).")
        assert res["Y"] == "a"

    def test_tautology(self):
        import unipycation

        e = unipycation.Engine("f(1).")
        assert isinstance(e, unipycation.Engine)

        res = e.query_single("f(_).")
        assert res == {}

    def test_false(self):
        import unipycation

        e = unipycation.Engine("f(1).")
        assert isinstance(e, unipycation.Engine)

        raises(StopIteration, e.query_single("f(2)."))

    def test_parse_query_incomplete(self):
        import unipycation
        e = unipycation.Engine("f(1).")

        raises(unipycation.ParseError, lambda: e.query_single("f(X)")) # note missing dot on query

    def test_parse_db_incomplete(self):
        import unipycation

        raises(unipycation.ParseError, lambda: unipycation.Engine("f(1)")) # missing dot on db

    def test_iterator(self):
        import unipycation

        e = unipycation.Engine("f(1). f(666).")
        it = e.query_iter("f(X).")

        results = [ r["X"] for r in it ]

        assert results == [1, 666]

    def test_iterator_no_result(self):
        import unipycation

        e = unipycation.Engine("f(666).")
        it = e.query_iter("f(1337).")

        results = [ r["X"] for r in it ]

        assert results == []

    def test_iterator_tautology(self):
        import unipycation

        e = unipycation.Engine("f(666).")
        it = e.query_iter("f(666).")

        results = [ r for r in it ]

        assert results == [{}]

    def test_iterator_infty(self):
        import unipycation

        e = unipycation.Engine("""
                f(0).
                f(X) :- f(X0), X is X0 + 1.
        """)
        it = e.query_iter("f(X).")

        first_ten = []
        for i in range(10):
            first_ten.append(it.next()["X"])

        assert first_ten == range(0, 10)

    def test_iterator_multigoal(self):
        import unipycation

        e = unipycation.Engine("f(666).")

        raises(unipycation.GoalError, lambda: e.query_iter("f(666). f(667)."))

    def test_iter_nonexisting_predicate(self):
        import unipycation

        e = unipycation.Engine("f(666).")
        it = e.query_iter("lalalala.")

        raises(unipycation.GoalError, lambda: it.next())

    def test_query_nonexisting_predicate(self):
        import unipycation

        e = unipycation.Engine("f(666). f(667). f(668).")

        raises(unipycation.GoalError, lambda: e.query_single("g(X)."))
