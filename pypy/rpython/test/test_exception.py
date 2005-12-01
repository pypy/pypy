from pypy.translator.translator import TranslationContext
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.test.test_llinterp import interpret


class MyException(Exception):
    pass

class MyStrangeException:   # no (Exception) here
    pass

def rtype(fn, argtypes=[]):
    t = TranslationContext()
    t.buildannotator().build_types(fn, argtypes)
    typer = t.buildrtyper()
    typer.specialize()
    #t.view()
    t.checkgraphs()
    return t

def test_simple():
    def g():
        raise MyException
    def dummyfn():
        try:
            return g()
        except MyException:
            pass

    rtype(dummyfn)



def test_exception_data():
    def f(n):
        raise OverflowError()

    t = rtype(f, [int])

    excdata = t.rtyper.getexceptiondata()
    getcdef = t.annotator.bookkeeper.getuniqueclassdef

    #t.view()
    ovferr_inst = excdata.fn_pyexcclass2exc(pyobjectptr(OverflowError))
    classdef = getcdef(OverflowError)
    assert ovferr_inst.typeptr == t.rtyper.class_reprs[classdef].getvtable()

    taberr_inst = excdata.fn_pyexcclass2exc(pyobjectptr(TabError))
    classdef = getcdef(StandardError) # most precise class seen
    assert taberr_inst.typeptr == t.rtyper.class_reprs[classdef].getvtable()

    myerr_inst = excdata.fn_pyexcclass2exc(pyobjectptr(MyException))
    assert myerr_inst.typeptr == t.rtyper.class_reprs[None].getvtable()

    strgerr_inst = excdata.fn_pyexcclass2exc(pyobjectptr(MyStrangeException))
    assert strgerr_inst.typeptr == t.rtyper.class_reprs[None].getvtable()


def test_exception_with_arg():
    def g(n):
        raise OSError(n, "?")
    def f(n):
        try:
            g(n)
        except OSError, e:
            return e.errno
    res = interpret(f, [42])
    assert res == 42
