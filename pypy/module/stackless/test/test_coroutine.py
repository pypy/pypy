from pypy.conftest import gettestobjspace

# no real testing possible without compiling stackless pypy

class AppTest_Coroutine:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('stackless',))
        cls.space = space

    def test_one(self):
        import stackless
        print stackless.__file__
        co = stackless.coroutine()
        print co
