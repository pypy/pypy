import sys, py

from rpython.rlib.rstring import StringBuilder, UnicodeBuilder, split, rsplit
from rpython.rlib.rstring import replace, startswith, endswith
from rpython.rtyper.test.tool import BaseRtypingTest

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

def test_split_None():
    assert split("") == []
    assert split(' a\ta\na b') == ['a', 'a', 'a', 'b']
    assert split(" a a ", maxsplit=1) == ['a', 'a ']

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

def test_rsplit_None():
    assert rsplit("") == []
    assert rsplit(' a\ta\na b') == ['a', 'a', 'a', 'b']
    assert rsplit(" a a ", maxsplit=1) == [' a', 'a']

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
    assert replace('one!two!three!', '!', '@', 1) == 'one@two!three!'
    assert replace('one!two!three!', '!', '') == 'onetwothree'
    assert replace('one!two!three!', '!', '@', 2) == 'one@two@three!'
    assert replace('one!two!three!', '!', '@', 3) == 'one@two@three@'
    assert replace('one!two!three!', '!', '@', 4) == 'one@two@three@'
    assert replace('one!two!three!', '!', '@', 0) == 'one!two!three!'
    assert replace('one!two!three!', '!', '@') == 'one@two@three@'
    assert replace('one!two!three!', 'x', '@') == 'one!two!three!'
    assert replace('one!two!three!', 'x', '@', 2) == 'one!two!three!'
    assert replace('abc', '', '-') == '-a-b-c-'
    assert replace('abc', '', '-', 3) == '-a-b-c'
    assert replace('abc', '', '-', 0) == 'abc'
    assert replace('', '', '') == ''
    assert replace('', '', 'a') == 'a'
    assert replace('abc', 'ab', '--', 0) == 'abc'
    assert replace('abc', 'xy', '--') == 'abc'
    assert replace('123', '123', '') == ''
    assert replace('123123', '123', '') == ''
    assert replace('123x123', '123', '') == 'x'

def test_string_replace_overflow():
    if sys.maxint > 2**31-1:
        py.test.skip("Wrong platform")
    s = "a" * (2**16)
    with py.test.raises(OverflowError):
        replace(s, "", s)
    with py.test.raises(OverflowError):
        replace(s, "a", s)
    with py.test.raises(OverflowError):
        replace(s, "a", s, len(s) - 10)

def test_unicode_replace():
    assert replace(u'one!two!three!', u'!', u'@', 1) == u'one@two!three!'
    assert replace(u'one!two!three!', u'!', u'') == u'onetwothree'
    assert replace(u'one!two!three!', u'!', u'@', 2) == u'one@two@three!'
    assert replace(u'one!two!three!', u'!', u'@', 3) == u'one@two@three@'
    assert replace(u'one!two!three!', u'!', u'@', 4) == u'one@two@three@'
    assert replace(u'one!two!three!', u'!', u'@', 0) == u'one!two!three!'
    assert replace(u'one!two!three!', u'!', u'@') == u'one@two@three@'
    assert replace(u'one!two!three!', u'x', u'@') == u'one!two!three!'
    assert replace(u'one!two!three!', u'x', u'@', 2) == u'one!two!three!'
    assert replace(u'abc', u'', u'-') == u'-a-b-c-'
    assert replace(u'abc', u'', u'-', 3) == u'-a-b-c'
    assert replace(u'abc', u'', u'-', 0) == u'abc'
    assert replace(u'', u'', u'') == u''
    assert replace(u'', u'', u'a') == u'a'
    assert replace(u'abc', u'ab', u'--', 0) == u'abc'
    assert replace(u'abc', u'xy', u'--') == u'abc'
    assert replace(u'123', u'123', u'') == u''
    assert replace(u'123123', u'123', u'') == u''
    assert replace(u'123x123', u'123', u'') == u'x'

def test_unicode_replace_overflow():
    if sys.maxint > 2**31-1:
        py.test.skip("Wrong platform")
    s = u"a" * (2**16)
    with py.test.raises(OverflowError):
        replace(s, u"", s)
    with py.test.raises(OverflowError):
        replace(s, u"a", s)
    with py.test.raises(OverflowError):
        replace(s, u"a", s, len(s) - 10)

def test_startswith():
    assert startswith('ab', 'ab') is True
    assert startswith('ab', 'a') is True
    assert startswith('ab', '') is True
    assert startswith('x', 'a') is False
    assert startswith('x', 'x') is True
    assert startswith('', '') is True
    assert startswith('', 'a') is False
    assert startswith('x', 'xx') is False
    assert startswith('y', 'xx') is False
    assert startswith('ab', 'a', 0) is True
    assert startswith('ab', 'a', 1) is False
    assert startswith('ab', 'b', 1) is True
    assert startswith('abc', 'bc', 1, 2) is False
    assert startswith('abc', 'c', -1, 4) is True

def test_endswith():
    assert endswith('ab', 'ab') is True
    assert endswith('ab', 'b') is True
    assert endswith('ab', '') is True
    assert endswith('x', 'a') is False
    assert endswith('x', 'x') is True
    assert endswith('', '') is True
    assert endswith('', 'a') is False
    assert endswith('x', 'xx') is False
    assert endswith('y', 'xx') is False
    assert endswith('abc', 'ab', 0, 2) is True
    assert endswith('abc', 'bc', 1) is True
    assert endswith('abc', 'bc', 2) is False
    assert endswith('abc', 'b', -3, -1) is True

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


class TestTranslates(BaseRtypingTest):
    def test_split_rsplit(self):
        def fn():
            res = True
            res = res and split('a//b//c//d', '//') == ['a', 'b', 'c', 'd']
            res = res and split(' a\ta\na b') == ['a', 'a', 'a', 'b']
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

    def test_replace(self):
        def fn():
            res = True
            res = res and replace('abc', 'ab', '--', 0) == 'abc'
            res = res and replace('abc', 'xy', '--') == 'abc'
            res = res and replace('abc', 'ab', '--', 0) == 'abc'
            res = res and replace('abc', 'xy', '--') == 'abc'
            return res
        res = self.interpret(fn, [])
        assert res
