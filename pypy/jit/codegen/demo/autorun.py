import random
from pypy.jit.codegen.demo import test_random
from pypy.jit.codegen.demo import conftest as demo_conftest


# each iteration of test_many_times leaks memory, so we can't run
# it forever.  If you want that result, use a bash command like:
#
#     while py.test autorun.py --pdb; do echo "again"; done


def test_many_times():
    for i in range(80):
        demo_conftest.option.randomseed = random.randrange(0, 100000)
        test_random.test_random_function()
