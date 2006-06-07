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
        # not much we can do here without compiling.
        # well, we can pickle, at least:

    def test_pickle_coroutine(self):
        # this test is limited to basic pickling.
        # real stacks can only tested with a stackless pypy build.
        import stackless
        co = stackless.coroutine()
        import pickle
        pckl = pickle.dumps(co)
        co2 = pickle.loads(pckl)
        