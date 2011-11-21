from __future__ import with_statement
import py

from pypy.rlib.rstring import StringBuilder, UnicodeBuilder
from pypy.rpython.annlowlevel import llstr, hlstr
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem.rbuilder import *
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin


class TestStringBuilderDirect(object):
    def test_simple(self):
        sb = StringBuilderRepr.ll_new(3)
        StringBuilderRepr.ll_append_char(sb, 'x')
        StringBuilderRepr.ll_append(sb, llstr("abc"))
        StringBuilderRepr.ll_append_slice(sb, llstr("foobar"), 2, 5)
        StringBuilderRepr.ll_append_multiple_char(sb, 'y', 3)
        s = StringBuilderRepr.ll_build(sb)
        assert hlstr(s) == "xabcobayyy"

    def test_nooveralloc(self):
        sb = StringBuilderRepr.ll_new(3)
        StringBuilderRepr.ll_append(sb, llstr("abc"))
        assert StringBuilderRepr.ll_build(sb) == sb.buf

class BaseTestStringBuilder(BaseRtypingTest):
    def test_simple(self):
        def func():
            s = StringBuilder()
            s.append("a")
            s.append("abc")
            s.append_slice("abc", 1, 2)
            s.append_multiple_char('d', 4)
            return s.build()
        res = self.ll_to_string(self.interpret(func, []))
        assert res == "aabcbdddd"

    def test_overallocation(self):
        def func():
            s = StringBuilder(4)
            s.append("abcd")
            s.append("defg")
            s.append("rty")
            return s.build()
        res = self.ll_to_string(self.interpret(func, []))
        assert res == "abcddefgrty"

    def test_unicode(self):
        def func():
            s = UnicodeBuilder()
            s.append(u'a')
            s.append(u'abc')
            s.append(u'abcdef')
            s.append_slice(u'abc', 1, 2)
            s.append_multiple_char(u'u', 4)
            return s.build()
        res = self.ll_to_unicode(self.interpret(func, []))
        assert res == 'aabcabcdefbuuuu'
        assert isinstance(res, unicode)

    def test_string_getlength(self):
        def func():
            s = StringBuilder()
            s.append("a")
            s.append("abc")
            return s.getlength()
        res = self.interpret(func, [])
        assert res == 4

    def test_unicode_getlength(self):
        def func():
            s = UnicodeBuilder()
            s.append(u"a")
            s.append(u"abc")
            return s.getlength()
        res = self.interpret(func, [])
        assert res == 4

    def test_append_charpsize(self):
        def func(l):
            s = StringBuilder()
            with rffi.scoped_str2charp("hello world") as x:
                s.append_charpsize(x, l)
            return s.build()
        res = self.ll_to_string(self.interpret(func, [5]))
        assert res == "hello"

    def test_builder_or_none(self):
        def g(s):
            if s:
                s.append("3")
            return bool(s)
        
        def func(i):
            if i:
                s = StringBuilder()
            else:
                s = None
            return g(s)
        res = self.interpret(func, [0])
        assert not res
        res = self.interpret(func, [1])
        assert res

    def test_unicode_builder_or_none(self):
        def g(s):
            if s:
                s.append(u"3")
            return bool(s)
        
        def func(i):
            if i:
                s = UnicodeBuilder()
            else:
                s = None
            return g(s)
        res = self.interpret(func, [0])
        assert not res
        res = self.interpret(func, [1])
        assert res


class TestLLtype(BaseTestStringBuilder, LLRtypeMixin):
    pass

class TestOOtype(BaseTestStringBuilder, OORtypeMixin):
    def test_string_getlength(self):
        py.test.skip("getlength(): not implemented on ootype")
    def test_unicode_getlength(self):
        py.test.skip("getlength(): not implemented on ootype")
    def test_append_charpsize(self):
        py.test.skip("append_charpsize(): not implemented on ootype")
