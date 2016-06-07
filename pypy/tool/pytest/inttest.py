# Collects and executes interpreter-level tests.
#
# Most pypy tests are of this kind.

import py
from pypy.conftest import PyPyClassCollector


marker = py.test.mark.interplevel


class IntTestFunction(py.test.collect.Function):
    def __init__(self, *args, **kwargs):
        super(IntTestFunction, self).__init__(*args, **kwargs)
        self._request.applymarker(marker)


class IntInstanceCollector(py.test.collect.Instance):
    Function = IntTestFunction


class IntClassCollector(PyPyClassCollector):
    Instance = IntInstanceCollector
