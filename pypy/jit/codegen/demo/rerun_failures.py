from pypy.jit.codegen.demo import test_random
from pypy.jit.codegen.demo import conftest as demo_conftest

def rerun(seed, *args):
    prevseed = demo_conftest.option.randomseed
    try:
        demo_conftest.option.randomseed = seed
        test_random.test_random_function(*args)
    finally:
        demo_conftest.option.randomseed = prevseed

# ____________________________________________________________
# These are tests that failed at some point on intel.  Run
# them all with py.test rerun_failures.py.

def test_4327406():    rerun(4327406)
def test_9473():       rerun(9473)
def test_3888():       rerun(3888)
def test_2307():       rerun(2307)
def test_9792():       rerun(9792)
def test_37():         rerun(37)
def test_2871_1_100(): rerun(2871, 1, 100)
def test_6294():       rerun(6294)

# here's a ppcfew failure or two:

def test_39263():      rerun(39263)
def test_33851():      rerun(33851)
def test_20202():      rerun(20202)
