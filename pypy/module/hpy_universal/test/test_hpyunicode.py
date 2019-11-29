import pytest
from pypy.module.hpy_universal._vendored.test.test_hpyunicode import TestUnicode as _Test
from .support import HPyAppTest

class AppTestUnicode(HPyAppTest, _Test):
    spaceconfig = {'usemodules': ['hpy_universal']}
