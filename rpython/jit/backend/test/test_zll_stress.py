from rpython.jit.backend.test.test_random import check_random_function, Random
from rpython.jit.backend.test.test_ll_random import LLtypeOperationBuilder
from rpython.jit.backend.detect_cpu import getcpuclass
import platform

CPU = getcpuclass()

iterations = 1000
if platform.machine().startswith('arm'):
    iterations = 100


def test_stress():
    cpu = CPU(None, None)
    cpu.setup_once()
    r = Random()
    for i in range(iterations):
        check_random_function(cpu, LLtypeOperationBuilder, r, i, iterations)
