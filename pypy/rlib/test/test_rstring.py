
from pypy.rlib.rstring import StringBuilder, UnicodeBuilder

def test_string_builder():
    s = StringBuilder()
    s.append("a")
    s.append("abc")
    s.append("a")
    s.append_slice("abc", 1, 2)
    s.append_multiple_char('d', 4)
    assert s.build() == "aabcabdddd"

def test_unicode_builder():
    s = UnicodeBuilder()
    s.append(u'a')
    s.append(u'abc')
    s.append_slice(u'abcdef', 1, 2)
    s.append_multiple_char('d', 4)
    assert s.build() == 'aabcbdddd'
    assert isinstance(s.build(), unicode)
