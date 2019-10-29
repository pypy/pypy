# import posix underneath
from os import environ

# for the test_random_stuff_can_unfreeze test
environ['PYPY_DEMO_MODULE_ERROR'] = '1'

class DemoError(Exception):
    pass
