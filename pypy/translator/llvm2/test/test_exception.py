from pypy.translator.llvm2.genllvm import compile_function
from pypy.translator.test.snippet import try_raise_choose

class TestException(Exception):
    pass

class MyException(Exception):
    def __init__(self, n):
        self.n = n

def test_simple1():
    def raise_(i):
        if i:
            raise TestException()
        else:
            return 3
    def fn(i):
        try:
            a = raise_(i) + 11
            b = raise_(i) + 12
            c = raise_(i) + 13
            return a+b+c
        except TestException: 
            return 7
    f = compile_function(fn, [int])
    assert f(0) == fn(0)
    assert f(1) == fn(1)

def test_simple2():
    def fn(n):
        lst = range(10)
        try:
            lst[n]
        except:
            return 2
        return 4
    f = compile_function(fn, [int])
    assert f(-1) == fn(-1)
    assert f( 0) == fn( 0)
    assert f(10) == fn(10)

def test_pass_exc():
    def fn(n):
        lst = range(10)
        try:
            lst[n]
        except:
            pass
        return 4
    f = compile_function(fn, [int])
    assert f(-1) == fn(-1)
    assert f( 0) == fn( 0)
    assert f(10) == fn(10)

def test_divzero():
    def fn(n):
        try:
            n/0
        except:
            return 2
        return 4
    f = compile_function(fn, [int])
    assert f(0) == fn(0)
    
def test_reraise1():
    def fn(n):
        lst = range(10)
        try:
            lst[n]
        except:
            raise
        return 4
    f = compile_function(fn, [int])
    assert f(-1) == fn(-1)
    assert f( 0) == fn( 0)
    assert f(10) == fn(10)

def test_reraise2():
    def fn(n):
        lst = range(10)
        try:
            lst[n]
        except e:
            raise e
        return 4
    f = compile_function(fn, [int])
    assert f(-1) == fn(-1)
    assert f( 0) == fn( 0)
    assert f(10) == fn(10)

def test_simple_exception():
    def fn(n):
        lst = range(10)
        try:
            lst[n]
        except IndexError:
            return 2
        return 4
    f = compile_function(fn, [int])
    for i in range(10):
        assert f(i) == fn(i)
    for i in range(10, 20):
        assert f(i) == fn(i)

def test_two_exceptions():
    def fn(n):
        lst = range(10)
        try:
            lst[n]
        except IndexError:
            return 2
        except KeyError:
            return 3
        return 4
    f = compile_function(fn, [int])
    for i in range(10):
        assert f(i) == fn(i)
    for i in range(10, 20):
        assert f(i) == fn(i)

def test_catch_base_exception():
    def fn(n):
        lst = range(10)
        try:
            lst[n]
        except LookupError:
            return 2
        return 4
    f = compile_function(fn, [int])
    for i in range(10):
        assert f(i) == fn(i)
    for i in range(10, 20):
        assert f(i) == fn(i)


def test_catches():
    def raises(i):
        if i == 3:
            raise MyException, 12
        if i == 4:
            raise IndexError
        if i > 5:
            raise MyException(i)
        return 1
    def fn(i):
        try:
            return raises(i)
        except MyException, e:
            return e.n
    f = compile_function(fn, [int])
    assert f(1) == fn(1)
    assert f(2) == fn(2)
    assert f(3) == fn(3)
    py.test.raises(RuntimeError, "f(4)")
    assert f(5) == fn(5)
    assert f(6) == fn(6)
    assert f(13) == fn(13)

def test_try_raise_choose():
    f = compile_function(try_raise_choose, [int])
    for i in [-1, 0, 1, 2]:
        assert f(i) == i
