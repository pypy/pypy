import pytest

class AppTestHighLevelInterface(object):
    spaceconfig = dict(usemodules=('unipycation', ))

    def test_basic(self):
        import uni

        e = uni.Engine("f(666).")
        X = uni.Var()
        sol = e.db.f([X])

        assert sol == { X : 666 }

