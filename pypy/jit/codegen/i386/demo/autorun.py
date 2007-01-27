import random
from pypy.jit.codegen.i386.demo import test_random
from pypy.jit.codegen.i386.demo import conftest as demo_conftest


def test_forever():
    while True:
        demo_conftest.option.randomseed = random.randrange(0, 100000)
        test_random.test_random_function()
