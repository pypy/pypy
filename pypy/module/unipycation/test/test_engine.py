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
