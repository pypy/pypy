import pytest
from pypy.module._hpy_universal._vendored.test import test_object as _t
from .support import HPyAppTest

class AppTestObject(HPyAppTest, _t.TestObject):
    spaceconfig = {'usemodules': ['_hpy_universal']}
