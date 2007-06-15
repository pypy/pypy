
from pypy.annotation.signature import _annotation_key

def test__annotation_key():
    assert _annotation_key([[str]]) == ('list', ('list', str))
    assert _annotation_key({str:(str, [str])}) == ('dict', (str, (str, ('list', str))))
    for i in ([[str]], [str], (int, int, {str: [str]})):
        assert hash(_annotation_key(i))

