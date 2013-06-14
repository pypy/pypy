import sys, py

from rpython.rlib.rstring import StringBuilder, UnicodeBuilder, split, rsplit
from rpython.rlib.rstring import string_replace
from rpython.rtyper.test.tool import BaseRtypingTest, LLRtypeMixin

def test_split():
    assert split("", 'x') == ['']
    assert split("a", "a", 1) == ['', '']
    assert split(" ", " ", 1) == ['', '']
    assert split("aa", "a", 2) == ['', '', '']
    assert split('a|b|c|d', '|') == ['a', 'b', 'c', 'd']
    assert split('a|b|c|d', '|', 2) == ['a', 'b', 'c|d']
    assert split('a//b//c//d', '//') == ['a', 'b', 'c', 'd']
    assert split('a//b//c//d', '//', 2) == ['a', 'b', 'c//d']
    assert split('endcase test', 'test') == ['endcase ', '']
    py.test.raises(ValueError, split, 'abc', '')

def test_split_unicode():
    assert split(u"", u'x') == [u'']
    assert split(u"a", u"a", 1) == [u'', u'']
    assert split(u" ", u" ", 1) == [u'', u'']
    assert split(u"aa", u"a", 2) == [u'', u'', u'']
    assert split(u'a|b|c|d', u'|') == [u'a', u'b', u'c', u'd']
    assert split(u'a|b|c|d', u'|', 2) == [u'a', u'b', u'c|d']
    assert split(u'a//b//c//d', u'//') == [u'a', u'b', u'c', u'd']
    assert split(u'endcase test', u'test') == [u'endcase ', u'']
    py.test.raises(ValueError, split, u'abc', u'')

def test_rsplit():
    assert rsplit("a", "a", 1) == ['', '']
    assert rsplit(" ", " ", 1) == ['', '']
    assert rsplit("aa", "a", 2) == ['', '', '']
    assert rsplit('a|b|c|d', '|') == ['a', 'b', 'c', 'd']
    assert rsplit('a|b|c|d', '|', 2) == ['a|b', 'c', 'd']
    assert rsplit('a//b//c//d', '//') == ['a', 'b', 'c', 'd']
    assert rsplit('endcase test', 'test') == ['endcase ', '']
    py.test.raises(ValueError, rsplit, "abc", '')

def test_rsplit_unicode():
    assert rsplit(u"a", u"a", 1) == [u'', u'']
    assert rsplit(u" ", u" ", 1) == [u'', u'']
    assert rsplit(u"aa", u"a", 2) == [u'', u'', u'']
    assert rsplit(u'a|b|c|d', u'|') == [u'a', u'b', u'c', u'd']
    assert rsplit(u'a|b|c|d', u'|', 2) == [u'a|b', u'c', u'd']
    assert rsplit(u'a//b//c//d', u'//') == [u'a', u'b', u'c', u'd']
    assert rsplit(u'endcase test', u'test') == [u'endcase ', u'']
    py.test.raises(ValueError, rsplit, u"abc", u'')

def test_string_replace():
    assert string_replace('one!two!three!', '!', '@', 1) == 'one@two!three!'
    assert string_replace('one!two!three!', '!', '') == 'onetwothree'
    assert string_replace('one!two!three!', '!', '@', 2) == 'one@two@three!'
    assert string_replace('one!two!three!', '!', '@', 3) == 'one@two@three@'
    assert string_replace('one!two!three!', '!', '@', 4) == 'one@two@three@'
    assert string_replace('one!two!three!', '!', '@', 0) == 'one!two!three!'
    assert string_replace('one!two!three!', '!', '@') == 'one@two@three@'
    assert string_replace('one!two!three!', 'x', '@') == 'one!two!three!'
    assert string_replace('one!two!three!', 'x', '@', 2) == 'one!two!three!'
    assert string_replace('abc', '', '-') == '-a-b-c-'
    assert string_replace('abc', '', '-', 3) == '-a-b-c'
    assert string_replace('abc', '', '-', 0) == 'abc'
    assert string_replace('', '', '') == ''
    assert string_replace('', '', 'a') == 'a'
    assert string_replace('abc', 'ab', '--', 0) == 'abc'
    assert string_replace('abc', 'xy', '--') == 'abc'
    assert string_replace('123', '123', '') == ''
    assert string_replace('123123', '123', '') == ''
    assert string_replace('123x123', '123', '') == 'x'

def test_string_replace_overflow():
    if sys.maxint > 2**31-1:
        py.test.skip("Wrong platform")
    s = "a" * (2**16)
    with py.test.raises(OverflowError):
        string_replace(s, "", s)
    with py.test.raises(OverflowError):
        string_replace(s, "a", s)
    with py.test.raises(OverflowError):
        string_replace(s, "a", s, len(s) - 10)


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


class TestTranslates(LLRtypeMixin, BaseRtypingTest):
    def test_split_rsplit_translate(self):
        def fn():
            res = True
            res = res and split('a//b//c//d', '//') == ['a', 'b', 'c', 'd']
            res = res and split('a//b//c//d', '//', 2) == ['a', 'b', 'c//d']
            res = res and split(u'a//b//c//d', u'//') == [u'a', u'b', u'c', u'd']
            res = res and split(u'endcase test', u'test') == [u'endcase ', u'']
            res = res and rsplit('a|b|c|d', '|', 2) == ['a|b', 'c', 'd']
            res = res and rsplit('a//b//c//d', '//') == ['a', 'b', 'c', 'd']
            res = res and rsplit(u'a|b|c|d', u'|') == [u'a', u'b', u'c', u'd']
            res = res and rsplit(u'a|b|c|d', u'|', 2) == [u'a|b', u'c', u'd']
            res = res and rsplit(u'a//b//c//d', u'//') == [u'a', u'b', u'c', u'd']
            return res
        res = self.interpret(fn, [])
        assert res

