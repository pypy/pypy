import py
from pypy.rpython.rctypes.tool.compilemodule import compilemodule

def test_demo():
    mod = compilemodule('_demo')
    res = mod.measuretime(1000, long)
    assert type(res) is int
    py.test.raises(mod.DemoError, mod.measuretime, -5, long)
