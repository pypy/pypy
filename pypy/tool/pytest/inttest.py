# Collects and executes interpreter-level tests.
#
# Most pypy tests are of this kind.

import py
from pypy.conftest import PyPyClassCollector


class IntTestFunction(py.test.collect.Function):
    pass


class IntInstanceCollector(py.test.collect.Instance):
    Function = IntTestFunction


class IntClassCollector(PyPyClassCollector):
    Instance = IntInstanceCollector
