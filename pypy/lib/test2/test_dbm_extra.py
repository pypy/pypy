try:
    from pypy.lib import dbm
except ImportError:
    py.test.skip("No dbm module on this platform")

def test_extra():
    py.test.raises(TypeError, dbm.datum, 123)
    py.test.raises(TypeError, dbm.datum, False)
