"""
Tests for the mixedmodule interface.  The following tests run on top
of CPython, without using the PyPy interpreter.
"""

from pypy.interpreter.mixedmodule import testmodule


def setup_module(mod):
    mod.readline = testmodule("readline")

def test_names():
    assert readline.__name__ == 'readline'
    assert hasattr(readline, 'readline')
