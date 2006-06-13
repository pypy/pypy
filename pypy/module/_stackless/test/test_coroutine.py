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
    
    def test_pickle_coroutine_frame(self):
        #skip('passes in interactive interpreter but not here :/')
        # this requires py.magic.greenlet!
        import pickle, sys, new
        mod = new.module('mod')
        try: 
            sys.modules['mod'] = mod
            exec '''
import sys, stackless

def f():
        global the_frame
        the_frame = sys._getframe()
        main_coro.switch()

co = stackless.coroutine()
main_coro = stackless.coroutine.getcurrent()
co.bind(f)
co.switch()
''' in mod.__dict__
            pckl = pickle.dumps(mod.the_frame)
            #co2 = pickle.loads(pckl)
        finally:
            del sys.modules['mod']
                
