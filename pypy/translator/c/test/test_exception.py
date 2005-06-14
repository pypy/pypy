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
