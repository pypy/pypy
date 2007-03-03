
""" Various tests around interpreter in a subprocess
"""

import py

try:
    from pypeers.greensock2 import autogreenlet, wait, sleep, ConnexionClosed
    from pypeers.pipe.fd import FDInput
except ImportError:
    py.test.skip("greensock wasn't found")
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
    l = []

    def f():
        l.append(i.interact("import time;time.sleep(1)\n"))
    def g():
        l.append(i2.interact("a\n"))

    g_f = autogreenlet(f)
    g_g = autogreenlet(g)
    wait()
    assert len(l) == 2
    assert l[1].startswith(">>")
