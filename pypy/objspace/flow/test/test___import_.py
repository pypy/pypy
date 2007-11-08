from py.test import raises

def test___import_():
    import os
    mod = os.name
    raises(TypeError, __import__, ())
    x = __import__(mod)
    x = __import__(mod, None)
    x = __import__(mod, None, None)
    x = __import__(mod, None, None, None)
    raises(TypeError, __import__, (mod, None, None, None, None))
    # XXX this will have to be adjusted for Python 2.5 pretty soon-ish :-)