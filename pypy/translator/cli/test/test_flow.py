from pypy.translator.test import snippet as s
from pypy.translator.cli.test.runtest import check

def fibo(n):
    """Compute the (n+1)th Fibonacci's number"""
    a, b = 1, 1
    i = 0
    while i<n:
        a, b = b, a+b
        i += 1

    return a

snippets = [
    [s.if_then_else, [int, int, int], (0, 42, 43), (1, 42, 43)],
    [s.simple_func, [int], (42,)],
    [s.while_func, [int], (0,), (13,)],
    [fibo, [int], (0,), (1,), (10,)],
    [s.my_bool, [int], (0,), (42,)],
    [s.my_gcd, [int, int], (30, 18)],
    [s.is_perfect_number, [int], (28,), (27,)],
    ]



def test_snippets():
    for item in snippets:
        func = item[0]
        ann = item[1]
        arglists = item[2:]
        for arglist in arglists:
            yield check, func, ann, arglist
