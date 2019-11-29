import pytest
from pypy.module.hpy_universal._vendored.test.test_hpylist import TestList as _Test
from .support import HPyAppTest

class AppTestList(HPyAppTest, _Test):
    spaceconfig = {'usemodules': ['hpy_universal']}
