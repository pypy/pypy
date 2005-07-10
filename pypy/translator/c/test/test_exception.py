import py
from pypy.translator.translator import Translator


class MyException(Exception):
    pass

def test_myexception():
    def g():
        raise MyException
    def f():
        try:
            g()
        except MyException:
            return 5
        else:
            return 2

    t = Translator(f)
    t.annotate([]).simplify()
    t.specialize()
    #t.view()
    f1 = t.ccompile()
    assert f1() == 5

def test_raise_outside_testfn():
    def testfn(n):
        if n < 0:
            raise ValueError("hello")
        else:
            raise MyException("world")

    t = Translator(testfn)
    t.annotate([int]).simplify()
    t.specialize()
    f1 = t.ccompile()
    assert py.test.raises(ValueError, f1, -1)
    try:
        f1(1)
    except Exception, e:
        assert str(e) == 'MyException'   # which is genc's best effort
    else:
        py.test.fail("f1(1) did not raise anything")

def test_assert():
    def testfn(n):
        assert n >= 0

    # big confusion with py.test's AssertionError handling here...
    # some hacks to try to disable it for the current test.
    saved = no_magic()
    try:
        t = Translator(testfn)
        t.annotate([int]).simplify()
        t.specialize()
        f1 = t.ccompile()
        res = f1(0)
        assert res is None, repr(res)
        res = f1(42)
        assert res is None, repr(res)
        py.test.raises(AssertionError, f1, -2)
    finally:
        restore_magic(saved)


def no_magic():
    import __builtin__
    try:
        py.magic.revert(__builtin__, 'AssertionError')
        return True
    except ValueError:
        return False

def restore_magic(saved):
    if saved:
        py.magic.invoke(assertion=True)
