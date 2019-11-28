import pytest
from pypy.module.hpy_universal._vendored.test.test_hpybytes import TestBytes as _Test
from .support import HPyAppTest

class AppTestBytes(HPyAppTest, _Test):
    spaceconfig = {'usemodules': ['hpy_universal']}
