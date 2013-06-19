import pypy.module.unipycation.engine as eng
#from prolog.interpreter.continuation import Engine

class AppTestEngine(object):
    spaceconfig = dict(usemodules=('unipycation',))

    def test_basic(self):
        import unipycation

        e = unipycation.Engine("likes(mac, jazz). likes(bob, jazz). likes(jim, funk).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("likes(X, jazz).")

        print(res)
        assert res["X"] in ["mac", "bob"]

    def test_basic_2(self):
        import unipycation

        e = unipycation.Engine("f(1, a). f(2, b). f(3, c).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(X, Y).")

        print(res)
        assert res["X"] in [1, 2, 3]

    def test_anonymous(self):
        import unipycation

        e = unipycation.Engine("f(1, a). f(2, b). f(3, c).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(_, Y).")

        print(res)
        assert res["Y"] in ["a", "b", "c"]

    def test_anonymous_tautology(self):
        import unipycation

        e = unipycation.Engine("f(1).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(_)")

        print(res)
        assert False # We have no way of detecting trivially true/false XXX
