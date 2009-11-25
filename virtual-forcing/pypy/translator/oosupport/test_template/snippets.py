from pypy.translator.test import snippet as s
from pypy.rlib.rarithmetic import r_longlong

# -----------------------------------------------------------------

def fibo(n):
    """Compute the (n+1)th Fibonacci's number"""
    a, b = 1, 1
    i = 0
    while i<n:
        a, b = b, a+b
        i += 1

    return a

# -----------------------------------------------------------------

class SimplestObject(object):
    pass

# -----------------------------------------------------------------

snippets = [
    [s.if_then_else, (0, 42, 43), (1, 42, 43)],
    [s.simple_func, (42,)],
    [s.while_func, (0,), (13,)],
    [fibo, (0,), (1,), (10,)],
    [s.my_bool, (0,), (42,)],
    [s.my_gcd, (30, 18)],
    [s.is_perfect_number, (28,), (27,)],
    ]

class BaseTestSnippets(object):

    def test_snippers(self):
        for item in snippets:
            func = item[0]
            for arglist in item[1:]:
                yield self.interpret, func, arglist
    
    def test_add(self):
        def fn(x, y):
            return x+y
        assert self.interpret(fn, [4,7]) == 11

    def test_llshl(self):
        def fn(a, b):
            return a << b
        assert self.interpret(fn, [r_longlong(1), 52]) == (1<<52)
        assert self.interpret(fn, [r_longlong(1), r_longlong(52)]) == (1<<52)

    def test_manipulate(self):
        def fn(x,y):
            obj = SimplestObject()
            obj.x = x + y
            return obj.x
        assert self.interpret(fn, [1,3]) == 4

    def test_link(self):
        def fn():
            plus = False
            for c in 'a':
                if c == 'b':
                    plus = True
                elif c == 'c':
                    binary = True
            return plus
        res = self.interpret(fn, [])
        expected = fn()
        assert res == expected

    def test_branch(self):
        def fn(i, j):
            if i < j:
                return "foo"
            else:
                return "bar"
        assert self.interpret(fn, [1, 2]) == "foo"
        assert self.interpret(fn, [2, 1]) == "bar"
