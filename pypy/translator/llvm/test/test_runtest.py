import py
from pypy.translator.oosupport.test_template.runtest import BaseTestRunTest
from pypy.translator.llvm.test.runtest import *

class TestRunTest(BaseTestRunTest, LLVMTest):
    def test_none(self):
        def fn(x):
            y = 1 + x
            return None
        assert self.interpret(fn,[1]) == None

    def test_list_of_strings(self):
        def fn():
            return ['abc', 'def']
        assert self.interpret(fn, []) == ['abc', 'def']

    def test_list_of_bools(self):
        def fn():
            return [True, True, False]
        assert self.interpret(fn, []) == [True, True, False]

    def test_tuple_of_list_of_stringss(self):
        def fn():
            return ['abc', 'def'],  ['abc', 'def']
        assert self.interpret(fn, []) == (['abc', 'def'],  ['abc', 'def'])
