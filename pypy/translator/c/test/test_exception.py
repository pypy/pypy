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
