import py
from pypy.translator.llvm.test.runtest import *

def test_richards():
    from pypy.translator.goal.richards import entry_point
    entry_point = compile_function(entry_point, [int])

    result, start, end = entry_point(1000)
    assert result
    assert end - start > 0 and end - start < 5.0

def test_rpystone():
    #py.test.skip("clock doesnt work")

    # XXX monkey patch hack XXX
    from time import time
    import pypy.translator.test.rpystone
    pypy.translator.test.rpystone.clock = time
    # XXX monkey patch hack XXX
    
    from pypy.translator.test.rpystone import pystones as entry_point
    entry_point = compile_function(entry_point, [int])
    t, pystones = entry_point(50000)
    assert 0 < t < 5
    assert 100000 < pystones < 100000000
