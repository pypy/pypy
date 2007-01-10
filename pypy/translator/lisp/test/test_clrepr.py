import py
from pypy.translator.cl.clrepr import clrepr

def test_const():
    assert clrepr(True) == 't'
    assert clrepr(False) == 'nil'
    assert clrepr(42) == '42'
    assert clrepr(1.5) == '1.5'
    assert clrepr(None) == 'nil'
    assert clrepr('a') == '#\\a'
    assert clrepr('answer') == '"answer"'
