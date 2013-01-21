from rpython.rtyper.test.tool import BaseRtypingTest, LLRtypeMixin
from rpython.rlib.unicodedata import unicodedb_5_2_0
from rpython.rlib.unicodedata.ucd import code_to_unichr

class TestTranslated(BaseRtypingTest, LLRtypeMixin):

    def test_translated(self):
        def f(n):
            if n == 0:
                return -1
            else:
                u = unicodedb_5_2_0.lookup("GOTHIC LETTER FAIHU")
                return u
        res = self.interpret(f, [1])
        print hex(res)
        assert res == f(1)

    def test_code_to_unichr(self):
        def f(c):
            return code_to_unichr(c) + u''
        res = self.ll_to_unicode(self.interpret(f, [0x10346]))
        assert res == u'\U00010346'
