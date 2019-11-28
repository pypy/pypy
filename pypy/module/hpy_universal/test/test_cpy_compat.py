import pytest
from pypy.module.hpy_universal._vendored.test.test_cpy_compat import TestCPythonCompatibility as _TestCPythonCompatibility
from .support import HPyAppTest

class AppTestUnicodeObject(HPyAppTest, _TestCPythonCompatibility):
    spaceconfig = {'usemodules': ['hpy_universal']}

    def setup_method(self, meth):
        pytest.skip('IMPLEMENT ME')
