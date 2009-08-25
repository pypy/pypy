from pypy.jit.backend.test.test_random import check_random_function, Random
from pypy.jit.backend.test.test_ll_random import LLtypeOperationBuilder
from pypy.jit.backend.x86.runner import CPU386

def test_stress():
    cpu = CPU386(None, None)
    r = Random()
    for i in range(1000):
        check_random_function(cpu, LLtypeOperationBuilder, r, i, 1000)



