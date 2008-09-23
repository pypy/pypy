
""" This test checks whether args wrapping behavior is correct
"""
import py
import sys

from ctypes import *

def test_wrap_args():
    if not hasattr(sys, 'pypy_translation_info'):
        py.test.skip("pypy white-box test")
    from _ctypes.function import CFuncPtr

    guess = CFuncPtr._guess_argtypes

    assert guess([13]) == [c_int]
    assert guess([0]) == [c_int]
    assert guess(['xca']) == [c_char_p]
    assert guess([None]) == [c_void_p]
    assert guess([c_int(3)]) == [c_int]
    assert guess([u'xca']) == [c_char_p]

    class Stuff:
        pass
    s = Stuff()
    s._as_parameter_ = None
    
    assert guess([s]) == [c_void_p]

    # not sure what else....
