
""" Few tests for annlowlevel helpers
"""

from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.lltypesystem.rstr import mallocstr
from pypy.rpython.annlowlevel import hlstr, llstr

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
    
