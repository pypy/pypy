
""" Various tests around interpreter in a subprocess
"""

import py

from py.__.green.greensock2 import allof
from py.__.green.pipe.fd import FDInput
from pypy.translator.js.examples.console.session import Interpreter

def test_greensock_reader_timeouter():
    i = Interpreter("python", timeout=3)
    while not i.interact().endswith(">>> "):
        pass
    assert i.interact() is None
    assert i.interact("a\n") is not None

def test_two_interpreters():
    i = Interpreter("python", timeout=3)
    i2 = Interpreter("python", timeout=3)
    while not i.interact().endswith(">>> "):
        pass
    while not i2.interact().endswith(">>> "):
        pass

    def f():
        return i.interact("import time;time.sleep(1)\n")
    def g():
        return i2.interact("a\n")

    one, two = allof(g, f)
    assert two.startswith(">>")
    assert one.startswith("Traceback")

def test_multiline_command():
    i = Interpreter("python", timeout=3)
    while not i.interact().endswith(">>> "):
        pass
    val = i.interact("def f(x):\n y = x + 3\n return y\n\nf(8)\n")
    while val is not None:
        assert 'Traceback' not in val
        assert 'Syntax' not in val
        print val
        val = i.interact()

