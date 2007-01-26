from pypy.jit.codegen.i386.demo.support import rundemo

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
