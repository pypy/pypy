from __future__ import absolute_import
import py
try:
    from lib_pypy import grp
except ImportError:
    py.test.skip("No grp module on this platform")

def test_extra():
    py.test.raises(TypeError, grp.getgrnam, False)
    py.test.raises(TypeError, grp.getgrnam, None)
