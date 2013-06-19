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

    def test_tautology(self):
        import unipycation

        print(72 * "-")
        e = unipycation.Engine("f(1).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(_)")

        print(res)
        assert res == {}


    def test_false(self):
        import unipycation

        print(72 * "-")
        e = unipycation.Engine("f(1).")
        assert isinstance(e, unipycation.Engine)

        res = e.query("f(2)")

        print(res)
        assert res == None
