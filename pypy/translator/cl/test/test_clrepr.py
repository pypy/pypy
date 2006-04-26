from pypy.translator.cl.clrepr import repr_const

def test_const():
    assert repr_const(True) == 't'
    assert repr_const(False) == 'nil'
    assert repr_const(42) == '42'
    assert repr_const(None) == 'nil'
    assert repr_const('a') == '#\\a'
    assert repr_const('answer') == '"answer"'
    assert repr_const((2, 3)) == "'(2 3)"
    assert repr_const([2, 3]) == "#(2 3)"
