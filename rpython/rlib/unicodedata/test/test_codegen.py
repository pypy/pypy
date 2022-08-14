import pytest
from StringIO import StringIO
from hypothesis import given, strategies, example

from rpython.rlib.unicodedata.codegen import CodeWriter, get_char_list_offset

def test_charlist():
    l = []
    d = {}
    offset = get_char_list_offset([1, 2, 3], l, d)
    assert offset == 0
    assert l == [1, 2, 3]
    assert d == {(1, ): 0, (2, ): 1, (3, ): 2, (1, 2): 0,
                 (2, 3): 1, (1, 2, 3): 0}

@example(l=[0, 1])
@given(strategies.lists(strategies.integers(min_value=0, max_value=2*32-1)))
def test_print_listlike(l):
    f = StringIO()
    c = CodeWriter(f)
    print >> c, 'from rpython.rlib.rarithmetic import r_longlong, r_int32, r_uint32, intmask'
    print >> c, '''\
from rpython.rlib.unicodedata.supportcode import (signed_ord, _all_short,
    _all_ushort, _all_int32, _all_uint32)'''
    c.print_listlike("l", l)
    d = {}
    s = f.getvalue()
    print l
    print s
    exec s in d
    func = d['l']
    for i, value in enumerate(l):
        assert func(i) == value
    for index in range(len(l), len(l) + 100):
        with pytest.raises((IndexError, KeyError)):
            func(index)

