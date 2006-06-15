import py
from pypy.interpreter.mixedmodule import testmodule

def test_demo():
    demo = testmodule("_demo")
    res = demo.measuretime(100, int)
    assert type(res) is int
    py.test.raises(demo.DemoError, 'demo.measuretime(-1, int)')
