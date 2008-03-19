
""" Few tests for annlowlevel helpers
"""

from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.lltypesystem.rstr import mallocstr
from pypy.rpython.annlowlevel import hlstr

class TestLLType(BaseRtypingTest, LLRtypeMixin):
    def test_hlstr(self):
        s = mallocstr(3)
        s.chars[0] = "a"
        s.chars[1] = "b"
        s.chars[2] = "c"
        assert hlstr(s) == "abc"
    
