import py
from pypy.annotation.signature import _annotation_key, annotation

def test__annotation_key():
    assert _annotation_key([[str]]) == ('list', ('list', str))
    assert _annotation_key({str:(str, [str])}) == ('dict', (str, (str, ('list', str))))
    for i in ([[str]], [str], (int, int, {str: [str]})):
        assert hash(_annotation_key(i))

def test_genericcallable():
    py.test.skip("this two annotations should be equal - fix!")
    from pypy.rpython.extfunc import genericcallable
    s1 = annotation([genericcallable([str], int)])
    s2 = annotation([genericcallable([str], int)])
    assert s1 == s2
