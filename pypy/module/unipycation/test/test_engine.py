import pypy.module.unipycation.engine as eng
import pytest

class AppTestEngine(object):
    spaceconfig = dict(usemodules=('unipycation', ))

    def test_basic(self):
        import unipycation

        e = unipycation.Engine("likes(mac, jazz). likes(bob, jazz). likes(jim, funk).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("likes(X, jazz).")
        assert res["X"] == "mac"

    def test_basic_2(self):
        import unipycation

        e = unipycation.Engine("f(1, a). f(2, b). f(3, c).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(X, Y).")
        assert res["X"] == 1

    def test_basic_3(self):
        import unipycation

        e = unipycation.Engine("f(1.23456).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(X).")
        assert res["X"] == 1.23456

    def test_anonymous(self):
        import unipycation

        e = unipycation.Engine("f(1, a). f(2, b). f(3, c).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(_, Y).")
        assert res["Y"] == "a"

    def test_tautology(self):
        import unipycation

        e = unipycation.Engine("f(1).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(_).")
        assert res == {}

    def test_false(self):
        import unipycation

        e = unipycation.Engine("f(1).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(2).")
        assert res == None

    def test_parse_query_incomplete(self):
        import unipycation
        e = unipycation.Engine("f(1).")

        try:
            res = e.query("f(X)") # note missing .
        except unipycation.ParseError:
            return # expected outcome

        assert False # Should be unreachable

    def test_parse_db_incomplete(self):
        import unipycation

        try:
            e = unipycation.Engine("f(1)") # missing dot
        except unipycation.ParseError:
            return # expected outcome

        assert False # Should be unreachable

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

        try:
            it = e.query_iter("f(666). f(667).")
        except unipycation.GoalError:
            return # expected

        assert False

    def test_nonexisting_predicate(self):
        import unipycation

        e = unipycation.Engine("f(666).")

        it = e.query_iter("lalalala.")
        print(72 * "-")
        print(it)

        try:
            for i in it: pass
        except unipycation.GoalError:
            return # expected, the goal was undefined

        assert False
