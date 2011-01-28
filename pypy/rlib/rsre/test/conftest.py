# import the option --viewloops from the JIT

def pytest_addoption(parser):
    from pypy.jit.conftest import pytest_addoption
    pytest_addoption(parser)
