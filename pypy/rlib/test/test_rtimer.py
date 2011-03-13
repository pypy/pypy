import time

from pypy.rlib.rtimer import read_timestamp
from pypy.rpython.test.test_llinterp import interpret
from pypy.translator.c.test.test_genc import compile

def timer():
    t1 = read_timestamp()
    start = time.time()
    while time.time() - start < 0.1:
        # busy wait
        pass
    t2 = read_timestamp()
    return t2 - t1

def test_timer():
    diff = timer()
    # We're counting ticks, verify they look correct
    assert diff > 1000

def test_annotation():
    diff = interpret(timer, [])
    assert diff > 1000

def test_compile_c():
    function = compile(timer, [])
    diff = function()
    assert diff > 1000