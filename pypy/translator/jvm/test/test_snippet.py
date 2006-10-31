from pypy.translator.test import snippet as s
from pypy.translator.jvm.test.runtest import JvmTest

snippets = [
    [s.if_then_else, (0, 42, 43), (1, 42, 43)],
    [s.simple_func, (42,)],
    [s.while_func, (0,), (13,)],
    [s.my_bool, (0,), (42,)],
    [s.my_gcd, (30, 18)],
    [s.is_perfect_number, (28,), (27,)],
    ]

class TestSnippets(JvmTest):

    def test_snippers(self):
        for item in snippets:
            func = item[0]
            for arglist in item[1:]:
                yield self.interpret, func, arglist
    
    def test_add(self):
        def fn(x, y):
            return x+y
        assert self.interpret(fn, [4,7]) == 11
