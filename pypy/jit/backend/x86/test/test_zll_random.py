from pypy.jit.backend.test.test_random import check_random_function, Random
from pypy.jit.backend.test.test_ll_random import LLtypeOperationBuilder
from pypy.jit.backend.detect_cpu import getcpuclass

CPU = getcpuclass()

def test_stress():
    cpu = CPU(None, None)
    cpu.setup_once()
    r = Random()
    for i in range(1000):
        check_random_function(cpu, LLtypeOperationBuilder, r, i, 1000)
