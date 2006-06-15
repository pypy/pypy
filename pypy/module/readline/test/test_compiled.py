"""
Test the compilation of the readline mixedmodule to a CPython extension
module.
"""

from pypy.interpreter.mixedmodule import compilemodule


def setup_module(mod):
    mod.readline = compilemodule("readline")

def test_names():
    assert readline.__name__ == 'readline'
    assert hasattr(readline, 'readline')
