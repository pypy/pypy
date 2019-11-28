import pytest
from pypy.module.hpy_universal._vendored.test.test_listobject import TestListObject as _TestListobject
from .support import HPyAppTest

class AppTestListObject(HPyAppTest, _TestListObject):
    spaceconfig = {'usemodules': ['hpy_universal']}
