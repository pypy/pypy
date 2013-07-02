import pypy.module.unipycation.engine as eng
import pytest

class AppTestEngine(object):
    spaceconfig = dict(usemodules=('unipycation', ))

    def test_basic(self):
        import unipycation

        e = unipycation.Engine("likes(mac, jazz). likes(bob, jazz). likes(jim, funk).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("likes(X, jazz).").next()
        assert res["X"] == "mac"

    def test_basic_2(self):
        import unipycation

        e = unipycation.Engine("f(1, a). f(2, b). f(3, c).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(X, Y).").next()
        assert res["X"] == 1

    def test_basic_3(self):
        import unipycation

        e = unipycation.Engine("f(1.23456).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(X).").next()
        assert res["X"] == 1.23456

    def test_anonymous(self):
        import unipycation

        e = unipycation.Engine("f(1, a). f(2, b). f(3, c).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(_, Y).").next()
        assert res["Y"] == "a"

    def test_tautology(self):
        import unipycation

        e = unipycation.Engine("f(1).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(_).").next()
        assert res == {}

    # XXX XXX XXX
    #def test_false(self):
    #    import unipycation
    #
    #    e = unipycation.Engine("f(1).")
    #    assert isinstance(e, unipycation.Engine)
    #
    #    sols = e.query("f(2).")
    #    first = res.next() # XXX Boom!, but why?
    #    assert first == None

    def test_parse_query_incomplete(self):
        import unipycation
        e = unipycation.Engine("f(1).")

        try: # XXX handle properly
            res = e.query("f(X)") # note missing .
        except unipycation.ParseError:
            return # expected outcome

        assert False # Should be unreachable

    def test_parse_db_incomplete(self):
        import unipycation

        try: # XXX handle properly
            e = unipycation.Engine("f(1)") # missing dot
        except unipycation.ParseError:
            return # expected outcome

        assert False # Should be unreachable

    def test_iterator(self):
        import unipycation

        e = unipycation.Engine("f(1). f(666).")
        it = e.query("f(X).")

        results = [ r["X"] for r in it ]

        assert results == [1, 666]

    def test_iterator_no_result(self):
        import unipycation

        e = unipycation.Engine("f(666).")
        it = e.query("f(1337).")

        results = [ r["X"] for r in it ]

        assert results == []

    def test_iterator_tautology(self):
        import unipycation

        e = unipycation.Engine("f(666).")
        it = e.query("f(666).")

        results = [ r for r in it ]

        assert results == [{}]

    def test_iterator_infty(self):
        import unipycation

        e = unipycation.Engine("""
                f(0).
                f(X) :- f(X0), X is X0 + 1.
        """)
        it = e.query("f(X).")

        first_ten = []
        for i in range(10):
            first_ten.append(it.next()["X"])

        assert first_ten == range(0, 10)

    def test_iterator_multigoal(self):
        import unipycation

        e = unipycation.Engine("f(666).")

        try: # XXX handle properly
            it = e.query("f(666). f(667).")
        except unipycation.GoalError:
            return # expected

        assert False

    def test_nonexisting_predicate(self):
        import unipycation

        e = unipycation.Engine("f(666).")

        it = e.query("lalalala.")
        print(72 * "-")
        print(it)

        try: # XXX handle properly
            for i in it: pass
        except unipycation.GoalError:
            return # expected, the goal was undefined

        assert False
