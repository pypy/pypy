import pytest
from pypy.module._hpy_universal._vendored.test.test_basic import TestBasic as _TestBasic
from .support import HPyAppTest

class AppTestBasic(HPyAppTest, _TestBasic):
    spaceconfig = {'usemodules': ['_hpy_universal']}

    def test_exception_occurred(self):
        import pytest
        pytest.skip('fixme')
