import py
from pypy.jit.codegen.demo.support import rundemo

# try running this with the following py.test options:
#
#   --view       shows the input llgraph and the output machine code
#
#   --seed=N     force a given random seed, for reproducible results.
#                if not given, multiple runs build the machine code
#                in different order, explicitly to stress the backend
#                in different ways.
#
#   --benchmark  benchmark the result code


def test_factorial():
    def fact(n):
        result = 1
        while n > 1:
            result *= n
            n -= 1
        return result
    rundemo(fact, 10)

def test_pseudofactorial():
    def pseudofact(n):
        result = 1
        while n > 1:
            if n & 1:
                result *= n
            n -= 1
        return result
    rundemo(pseudofact, 10)

def test_f1():
    def f1(n):
        "Arbitrary test function."
        i = 0
        x = 1
        while i<n:
            j = 0
            while j<=i:
                j = j + 1
                x = x + (i&j)
            i = i + 1
        return x
    #rundemo(f1, 2117)
    rundemo(f1, 217)
