from pypy.objspace.fake.checkmodule import checkmodule

import pytest

pytest.skip("too dificult to mock the fake objspace interfaces", allow_module_level=True)


def test_posix_translates():
    checkmodule('posix')
