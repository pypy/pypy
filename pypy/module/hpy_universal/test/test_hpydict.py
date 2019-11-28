import pytest
from pypy.module.hpy_universal._vendored.test.test_dictobject import TestDictObject as _TestDictobject
from .support import HPyAppTest

class AppTestDictObject(HPyAppTest, _TestDictObject):
    spaceconfig = {'usemodules': ['hpy_universal']}
