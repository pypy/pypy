from rpython.rlib.runicode import code_to_unichr, MAXUNICODE
from rpython.rlib.unicodedata import unicodedb_5_2_0
from rpython.rtyper.test.tool import BaseRtypingTest
from rpython.translator.c.test.test_genc import compile


class TestTranslated(BaseRtypingTest):
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


def test_code_to_unichr():
    def f(c):
        return ord(code_to_unichr(c)[0])
    f1 = compile(f, [int])
    got = f1(0x12346)
    if MAXUNICODE == 65535:
        assert got == 0xd808    # first char of a pair
    else:
        assert got == 0x12346
