import pytest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.hpy_universal._vendored.test.test_cpy_compat import TestCPythonCompatibility as _TestCPythonCompatibility
from .support import HPyAppTest

class HPyCPyextAppTest(AppTestCpythonExtensionBase, HPyAppTest):
    """
    Base class for hpy tests which also need cpyext
    """
    # mmap is needed because it is imported by LeakCheckingTest.setup_class
    spaceconfig = {'usemodules': ['hpy_universal', 'cpyext', 'mmap']}

    @staticmethod
    def setup_class(cls):
        AppTestCpythonExtensionBase.setup_class(cls)
        HPyAppTest.setup_class(cls)

    def setup_method(self, meth):
        AppTestCpythonExtensionBase.setup_method(self, meth)
        HPyAppTest.setup_method(self, meth)


class AppTestCPythonCompatibility(HPyCPyextAppTest, _TestCPythonCompatibility):
    pass
