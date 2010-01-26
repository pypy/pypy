
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.lltypesystem.rbuilder import *
from pypy.rpython.annlowlevel import llstr, hlstr
from pypy.rlib.rstring import StringBuilder, UnicodeBuilder


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

class TestLLtype(BaseTestStringBuilder, LLRtypeMixin):
    pass

class TestOOtype(BaseTestStringBuilder, OORtypeMixin):
    pass
