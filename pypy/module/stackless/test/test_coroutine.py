from pypy.conftest import gettestobjspace

class AppTest_Coroutine:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('stackless',))
        cls.space = space

    def test_one(self):
        import stackless
        print stackless.__file__
        co = stackless.Coroutine()
        print co
