import py
from pypy.lib import grp

def test_extra():
    py.test.raises(TypeError, grp.getgrnam, False)
    py.test.raises(TypeError, grp.getgrnam, None)
