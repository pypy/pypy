from pypy.conftest import gettestobjspace, option
import py

# app-level testing of coroutine pickling


class AppTestBasic:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('_stackless',))

    def test_pickle_main(self):
        import _stackless, pickle
        main = _stackless.coroutine.getcurrent()
        s = pickle.dumps(main)
        c = pickle.loads(s)
        assert c is main


class AppTestPickle:

    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('_stackless',), CALL_METHOD=True)

    def test_pickle_coroutine_empty(self):
        # this test is limited to basic pickling.
        # real stacks can only tested with a stackless pypy build.
        import _stackless as stackless
        co = stackless.coroutine()
        import pickle
        pckl = pickle.dumps(co)
        co2 = pickle.loads(pckl)
        # the empty unpickled coroutine can still be used:
        result = []
        co2.bind(result.append, 42)
        co2.switch()
        assert result == [42]

    def test_pickle_coroutine_bound(self):
        import pickle
        import _stackless
        lst = [4]
        co = _stackless.coroutine()
        co.bind(lst.append, 2)
        pckl = pickle.dumps((co, lst))

        (co2, lst2) = pickle.loads(pckl)
        assert lst2 == [4]
        co2.switch()
        assert lst2 == [4, 2]


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

    def test_pickle_again(self):

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
    pckl = pickle.dumps(new_coro)
    newer_coro = pickle.loads(pckl)

    newer_coro.switch()

example()
assert output == [16, 8, 4, 2, 1]
''' in mod.__dict__
        finally:
            del sys.modules['mod']

    def test_kwargs(self):

        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
output = []
import _stackless
def f(coro, n, x, step=4):
    if n == 0:
        coro.switch()
        return
    f(coro, n-1, 2*x, step=1)
    output.append(x)

def example():
    main_coro = _stackless.coroutine.getcurrent()
    sub_coro = _stackless.coroutine()
    sub_coro.bind(f, main_coro, 5, 1, 1)
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

    def test_starstarargs(self):

        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
output = []
import _stackless
def f(coro, n, x, step=4):
    if n == 0:
        coro.switch()
        return
    f(coro, n-1, 2*x, **{'step': 1})
    output.append(x)

def example():
    main_coro = _stackless.coroutine.getcurrent()
    sub_coro = _stackless.coroutine()
    sub_coro.bind(f, main_coro, 5, 1, 1)
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

    def test_exception_after_unpickling(self):

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
        raise ValueError
    try:
        f(coro, n-1, 2*x)
    finally:
        output.append(x)

def example():
    main_coro = _stackless.coroutine.getcurrent()
    sub_coro = _stackless.coroutine()
    sub_coro.bind(f, main_coro, 5, 1)
    sub_coro.switch()

    import pickle
    pckl = pickle.dumps(sub_coro)
    new_coro = pickle.loads(pckl)

    try:
        sub_coro.switch()
    except ValueError:
        pass
    else:
        assert 0
    try:
        new_coro.switch()
    except ValueError:
        pass
    else:
        assert 0

example()
assert output == [16, 8, 4, 2, 1] * 2
''' in mod.__dict__
        finally:
            del sys.modules['mod']

    def test_loop(self):
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


    def test_solver(self):
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
import _stackless, pickle

class Fail(Exception):
    pass

class Success(Exception):
    pass

def first_solution(func):
    global next_answer
    co = _stackless.coroutine()
    co.bind(func)
    pending = [(co, None)]
    while pending:
        co, next_answer = pending.pop()
        try:
            co.switch()
        except Fail:
            pass
        except Success, e:
            return e.args[0]
        else:
            # zero_or_one() called, clone the coroutine
            # NB. this seems to be quite slow
            co2 = pickle.loads(pickle.dumps(co))
            pending.append((co2, 1))
            pending.append((co, 0))
    raise Fail("no solution")

pending = []
main = _stackless.coroutine.getcurrent()

def zero_or_one():
    main.switch()
    return next_answer

# ____________________________________________________________

invalid_prefixes = {
    (0, 0): True,
    (0, 1, 0): True,
    (0, 1, 1): True,
    (1, 0): True,
    (1, 1, 0, 0): True,
    }

def example():
    test = []
    for n in range(5):
        test.append(zero_or_one())
        if tuple(test) in invalid_prefixes:
            raise Fail
    raise Success(test)

res = first_solution(example)
assert res == [1, 1, 0, 1, 0]
''' in mod.__dict__
        finally:
            del sys.modules['mod']
