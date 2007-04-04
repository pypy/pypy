from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.snippets import BaseTestSnippets

class Foo:
    pass

class TestSnippets(BaseTestSnippets, JvmTest):

    def test_equals_func(self):
        def equals(x, y):
            return x == y
        def unequals(x, y):
            return x != y
        def base_func(op):
            res = 0
            a = Foo()
            b = Foo()
            if op: func = equals
            else:  func = unequals
            if func(a,b): res += 1
            if func(a,a): res += 10
            if func(b,b): res += 100
            return res
        assert self.interpret(base_func, [True])  == 110
        assert self.interpret(base_func, [False]) == 001

