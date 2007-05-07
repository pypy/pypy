"""
Lazy functions in PyPy.
To run on top of the thunk object space with the following command-line:

    py.py -o thunk fibonacci2.py

This is a typical Functional Programming Languages demo, computing the
Fibonacci sequence as nested 2-tuples.
"""

import pprint

try:
    from __pypy__ import lazy
except ImportError:
    print __doc__
    raise SystemExit(2)


@lazy
def fibo(a, b):
    return (a, fibo(b, a + b))


fibonacci = fibo(1, 1)

pprint.pprint(fibonacci, depth=10)
