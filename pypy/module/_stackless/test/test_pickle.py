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

    def test_closure(self):
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
output = []
import _stackless
def example():
    main_coro = _stackless.coroutine.getcurrent()
    sub_coro = _stackless.coroutine()
    y = 3
    def f(coro, n, x):
        if n == 0:
            coro.switch()
            return
        f(coro, n-1, 2*x)
        output.append(x+y)

    sub_coro.bind(f, main_coro, 5, 1)
    sub_coro.switch()

    import pickle
    pckl = pickle.dumps(sub_coro)
    new_coro = pickle.loads(pckl)

    new_coro.switch()

example()
assert output == [19, 11, 7, 5, 4]
''' in mod.__dict__
        finally:
            del sys.modules['mod']

    def test_exception(self):
        skip("saving of exceptions is not working")
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
output = []
import _stackless
def f(coro):
    try:
        raise ValueError
    except:
        coro.switch()
        import sys
        t, v, tb = sys.exc_info()
        output.append(t)

def example():
    main_coro = _stackless.coroutine.getcurrent()
    sub_coro = _stackless.coroutine()

    sub_coro.bind(f, main_coro)
    sub_coro.switch()

    import pickle
    pckl = pickle.dumps(sub_coro)
    new_coro = pickle.loads(pckl)

    new_coro.switch()

example()
assert output == [ValueError]
''' in mod.__dict__
        finally:
            del sys.modules['mod']

    def test_loop(self):
        #skip("happily segfaulting")
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
output = []
import _stackless
def f(coro):
    for x in (1,2,3):
        coro.switch()
        output.append(x)

def example():
    main_coro = _stackless.coroutine.getcurrent()
    sub_coro = _stackless.coroutine()

    sub_coro.bind(f, main_coro)
    sub_coro.switch()

    import pickle
    pckl = pickle.dumps(sub_coro)
    new_coro = pickle.loads(pckl)

    new_coro.switch()
    new_coro.switch()
    new_coro.switch()

example()
assert output == [1, 2, 3]
''' in mod.__dict__
        finally:
            del sys.modules['mod']

    def test_valstack(self):
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
output = []
import _stackless
def f(coro):
    r = 1+g(coro)+3
    output.append(r)

def g(coro):
    coro.switch()
    return 2

def example():
    main_coro = _stackless.coroutine.getcurrent()
    sub_coro = _stackless.coroutine()

    sub_coro.bind(f, main_coro)
    sub_coro.switch()

    import pickle
    pckl = pickle.dumps(sub_coro)
    new_coro = pickle.loads(pckl)

    new_coro.switch()


example()
assert output == [6]
''' in mod.__dict__
        finally:
            del sys.modules['mod']


    def test_exec_and_locals(self):
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
output = []
import _stackless

def f(coro):
    x = None
    exec "x = 9"
    coro.switch()
    output.append(x)

def example():
    main_coro = _stackless.coroutine.getcurrent()
    sub_coro = _stackless.coroutine()
    sub_coro.bind(f, main_coro)
    sub_coro.switch()

    import pickle
    pckl = pickle.dumps(sub_coro)
    new_coro = pickle.loads(pckl)

    new_coro.switch()

example()
assert output == [9]
''' in mod.__dict__
        finally:
            del sys.modules['mod']
