import py
try:
    from pypy.lib import grp
except ImportError:
    py.test.skip("No grp module on this platform")

def test_extra():
    py.test.raises(TypeError, grp.getgrnam, False)
    py.test.raises(TypeError, grp.getgrnam, None)
