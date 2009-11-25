import py
from pypy.translator.translator import TranslationContext
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.llinterp import LLException

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

class BaseTestException(BaseRtypingTest):
    def test_exception_with_arg(self):
        def g(n):
            raise OSError(n, "?")
        def f(n):
            try:
                g(n)
            except OSError, e:
                return e.errno
        res = self.interpret(f, [42])
        assert res == 42

    def test_catch_incompatible_class(self):
        class MyError(Exception):
            pass
        def h(x):
            pass
        def f(n):
            try:
                assert n < 10
            except MyError, operr:
                h(operr)
        res = self.interpret(f, [7])
        assert res is None

    def test_raise_and_catch_other(self):
        class BytecodeCorruption(Exception):
            pass
        class OperationError(Exception):
            def __init__(self, a):
                self.a = a
        def f(next_instr):
            if next_instr < 7:
                raise OperationError(next_instr)
            try:
                raise BytecodeCorruption()
            except OperationError, operr:
                next_instr -= operr.a
        py.test.raises(LLException, self.interpret, f, [10])

    def test_raise_prebuilt_and_catch_other(self):
        class BytecodeCorruption(Exception):
            pass
        class OperationError(Exception):
            def __init__(self, a):
                self.a = a
        bcerr = BytecodeCorruption()
        def f(next_instr):
            if next_instr < 7:
                raise OperationError(next_instr)
            try:
                raise bcerr
            except OperationError, operr:
                next_instr -= operr.a
        py.test.raises(LLException, self.interpret, f, [10])

    def test_catch_KeyboardInterrupt(self):
        def g(n):
            return n
        def f(n):
            try:
                return g(n)
            except KeyboardInterrupt:
                return -1
        res = self.interpret(f, [11])
        assert res == 11


class TestLLtype(BaseTestException, LLRtypeMixin):
    pass

class TestOOtype(BaseTestException, OORtypeMixin):
    pass
