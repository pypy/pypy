import sys

from pypy.rlib.rstring import StringBuilder, UnicodeBuilder, split, rsplit


def test_split():
    assert split("", 'x') == ['']
    assert split("a", "a", 1) == ['', '']
    assert split(" ", " ", 1) == ['', '']
    assert split("aa", "a", 2) == ['', '', '']
    assert split('a|b|c|d', '|') == ['a', 'b', 'c', 'd']
    assert split('a|b|c|d', '|', 2) == ['a', 'b', 'c|d']
    assert split('a//b//c//d', '//') == ['a', 'b', 'c', 'd']
    assert split('endcase test', 'test') == ['endcase ', '']
    raises(ValueError, split, 'abc', '')

def test_rsplit():
    assert rsplit("a", "a", 1) == ['', '']
    assert rsplit(" ", " ", 1) == ['', '']
    assert rsplit("aa", "a", 2) == ['', '', '']
    assert rsplit('a|b|c|d', '|') == ['a', 'b', 'c', 'd']
    assert rsplit('a|b|c|d', '|', 2) == ['a|b', 'c', 'd']
    assert rsplit('a//b//c//d', '//') == ['a', 'b', 'c', 'd']
    assert rsplit('endcase test', 'test') == ['endcase ', '']
    raises(ValueError, rsplit, "abc", '')

def test_string_builder():
    s = StringBuilder()
    s.append("a")
    s.append("abc")
    assert s.getlength() == len('aabc')
    s.append("a")
    s.append_slice("abc", 1, 2)
    s.append_multiple_char('d', 4)
    assert s.build() == "aabcabdddd"

def test_unicode_builder():
    s = UnicodeBuilder()
    s.append(u'a')
    s.append(u'abc')
    s.append_slice(u'abcdef', 1, 2)
    assert s.getlength() == len('aabcb')
    s.append_multiple_char(u'd', 4)
    assert s.build() == 'aabcbdddd'
    assert isinstance(s.build(), unicode)