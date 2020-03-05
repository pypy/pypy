import pytest
from pypy.module._hpy_universal._vendored.test.test_hpydict import TestDict as _Test
from .support import HPyAppTest

class AppTestDict(HPyAppTest, _Test):
    spaceconfig = {'usemodules': ['_hpy_universal']}
