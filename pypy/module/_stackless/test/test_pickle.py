from pypy.conftest import gettestobjspace, skip_on_missing_buildoption
import py

# app-level testing of coroutine pickling

def setup_module(mod):
    skip_on_missing_buildoption(stackless=True)

class TestPickle:

    def test_simple_ish(self):

        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
output = []
import _stackless
def f(coro, n, x):
    if n == 0:
        coro.switch()
        return
    f(coro, n-1, 2*x)
    output.append(x)

def example():
    main_coro = _stackless.coroutine.getcurrent()
    sub_coro = _stackless.coroutine()
    sub_coro.bind(f, main_coro, 5, 1)
    sub_coro.switch()

    import pickle
    pckl = pickle.dumps(sub_coro)
    new_coro = pickle.loads(pckl)

    new_coro.switch()

example()
assert output == [16, 8, 4, 2, 1]
''' in mod.__dict__
        finally:
            del sys.modules['mod']
