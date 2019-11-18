import pytest
from pypy.module.hpy_universal._vendored.test.test_basic import TestBasic as _TestBasic
from .support import HPyAppTest

class AppTestBasic(HPyAppTest, _TestBasic):
    spaceconfig = {'usemodules': ['hpy_universal']}
