import pytest
from pypy.module._hpy_universal._vendored.test import test_number as _t
from .support import HPyAppTest

class AppTestNumber(HPyAppTest, _t.TestNumber):
    spaceconfig = {'usemodules': ['_hpy_universal']}
