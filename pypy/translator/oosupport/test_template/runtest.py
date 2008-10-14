import sys
import py
from pypy.annotation.listdef import s_list_of_strings
from pypy.rlib.rarithmetic import r_ulonglong

def ident(x):
    return x

class BaseTestRunTest:

    def test_patch_os(self):
        import os
        from pypy.translator.oosupport.support import patch_os, unpatch_os, NT_OS
        original_O_CREAT = os.O_CREAT
        olddefs = patch_os()
        assert os.O_CREAT == NT_OS['O_CREAT']
        unpatch_os(olddefs)
        assert os.O_CREAT == original_O_CREAT

    def test_int(self):
        assert self.interpret(ident, [42]) == 42
    
    def test_bool(self):
        assert self.interpret(ident, [True]) == True
        assert self.interpret(ident, [False]) == False

    def test_float(self):
        x = 10/3.0
        res = self.interpret(ident, [x])
        assert self.float_eq(x, res)

    def test_char(self):
        assert self.interpret(ident, ['a']) == 'a'

    def test_list(self):
        def fn():
            return [1, 2, 3]
        assert self.interpret(fn, []) == [1, 2, 3]

    def test_tuple(self):
        def fn():
            return 1, 2
        assert self.interpret(fn, []) == (1, 2)

    def test_string(self):
        def fn():
            return 'foo'
        res = self.interpret(fn, [])
        assert self.ll_to_string(res) == 'foo'

    def test_ullong(self):
        assert self.interpret(ident, [r_ulonglong(sys.maxint+1)]) == sys.maxint+1

    def test_big_ullong(self):
        bigval = 9223372036854775807L
        assert self.interpret(ident, [r_ulonglong(bigval)]) == bigval

    def test_exception(self):
        def fn():
            raise ValueError
        self.interpret_raises(ValueError, fn, [])

    def test_exception_subclass(self):
        def fn():
            raise IndexError
        self.interpret_raises(LookupError, fn, [])

    def test_object_or_none(self):
        def fn(flag):
            if flag:
                return "hello";
            else:
                return None
        assert self.interpret(fn, [False]) is None
        
    def test_list_of_chars(self):
        def fn():
            return ['a', 'b', 'c']
        res = self.interpret(fn, [])
        res = self.ll_to_list(res)
        assert res == ['a', 'b', 'c']
    
