import py
import sys
from pypy.rpython.rctypes.tool.compilemodule import compilemodule

def test_demo():
    mod = compilemodule('_demo')
    res = mod.measuretime(1000, long)
    assert type(res) is int
    py.test.raises(mod.DemoError, mod.measuretime, -5, long)

def test_readline():
    if sys.platform == "win32":
        py.test.skip("no readline on win32")
    
    mod = compilemodule('readline')
    assert hasattr(mod, 'readline')    # XXX test more
