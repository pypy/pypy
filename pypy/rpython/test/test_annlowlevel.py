
""" Few tests for annlowlevel helpers
"""

from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.lltypesystem.rstr import mallocstr, mallocunicode
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import hlstr, llstr, oostr
from pypy.rpython.annlowlevel import hlunicode, llunicode
from pypy.rpython import annlowlevel


class TestLLType(BaseRtypingTest, LLRtypeMixin):
    def test_hlstr(self):
        s = mallocstr(3)
        s.chars[0] = "a"
        s.chars[1] = "b"
        s.chars[2] = "c"
        assert hlstr(s) == "abc"

    def test_llstr(self):
        s = llstr("abc")
        assert len(s.chars) == 3
        assert s.chars[0] == "a"
        assert s.chars[1] == "b"
        assert s.chars[2] == "c"

    def test_llstr_compile(self):
        def f(arg):
            s = llstr(hlstr(arg))
            return len(s.chars)

        res = self.interpret(f, [self.string_to_ll("abc")])
        assert res == 3
    
    def test_hlunicode(self):
        s = mallocunicode(3)
        s.chars[0] = u"a"
        s.chars[1] = u"b"
        s.chars[2] = u"c"
        assert hlunicode(s) == u"abc"

    def test_llunicode(self):
        s = llunicode(u"abc")
        assert len(s.chars) == 3
        assert s.chars[0] == u"a"
        assert s.chars[1] == u"b"
        assert s.chars[2] == u"c"

    def test_llunicode_compile(self):
        def f(arg):
            s = llunicode(hlunicode(arg))
            return len(s.chars)

        res = self.interpret(f, [self.unicode_to_ll(u"abc")])
        assert res == 3

    def test_cast_instance_to_base_ptr(self):
        class X(object):
            pass
        x = X()
        ptr = annlowlevel.cast_instance_to_base_ptr(x)
        assert lltype.typeOf(ptr) == annlowlevel.base_ptr_lltype()
        y = annlowlevel.cast_base_ptr_to_instance(X, ptr)
        assert y is x


class TestOOType(BaseRtypingTest, OORtypeMixin):
    def test_hlstr(self):
        s = ootype.make_string("abc")
        assert hlstr(s) == "abc"

    def test_oostr(self):
        s = oostr("abc")
        assert ootype.typeOf(s) == ootype.String
        assert s._str == "abc"

    def test_oostr_compile(self):
        def f(arg):
            s = oostr(hlstr(arg))
            return s.ll_strlen()

        res = self.interpret(f, [self.string_to_ll("abc")])
        assert res == 3

    def test_cast_instance_to_base_obj(self):
        class X(object):
            pass
        x = X()
        obj = annlowlevel.cast_instance_to_base_obj(x)
        assert lltype.typeOf(obj) == annlowlevel.base_obj_ootype()
        y = annlowlevel.cast_base_ptr_to_instance(X, obj)
        assert y is x
