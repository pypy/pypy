from py.test import raises

def test___import_():
    import os
    mod = os.name
    raises(TypeError, __import__, ())
    assert __import__(mod).__name__ == os.name
    assert __import__(mod, None).__name__ == os.name
    assert __import__(mod, None, None).__name__ == os.name
    assert __import__(mod, None, None, None).__name__ == os.name
    raises(TypeError, __import__, (mod, None, None, None, None))
    # XXX this will have to be adjusted for Python 2.5 pretty soon-ish :-)