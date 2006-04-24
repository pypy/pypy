from pypy.translator.cl.buildcl import writelisp

def test_write():
    assert writelisp(True) == 't'
    assert writelisp(False) == 'nil'
    assert writelisp(42) == '42'
    assert writelisp(None) == 'nil'
    assert writelisp('answer') == '"answer"'
    assert writelisp((2, 3)) == "'(2 3)"
    assert writelisp([2, 3]) == "#(2 3)"
