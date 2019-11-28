import pytest
from pypy.module.hpy_universal._vendored.test.test_bytesobject import TestBytesObject as _TestBytesobject
from .support import HPyAppTest

class AppTestBytesObject(HPyAppTest, _TestBytesObject):
    spaceconfig = {'usemodules': ['hpy_universal']}
