
from pypy.lib import _exceptions as ex 

def test_environmenterror_repr():
    e = ex.EnvironmentError("hello")
    assert str(e) == "hello"
    e = ex.EnvironmentError(1, "hello")
    assert str(e) == "[Errno 1] hello"
    e = ex.EnvironmentError(1, "hello", "world")
    assert str(e) == "[Errno 1] hello: world"

