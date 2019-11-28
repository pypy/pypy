import pytest
from pypy.module.hpy_universal._vendored.test.test_unicodeobject import TestUnicodeObject as _TestUnicodeobject
from .support import HPyAppTest

class AppTestUnicodeObject(HPyAppTest, _TestUnicodeObject):
    spaceconfig = {'usemodules': ['hpy_universal']}
