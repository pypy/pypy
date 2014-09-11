from pypy.module.operator.tscmp import pypy_tscmp, pypy_tscmp_wide

class TestTimingSafeCompare:
    tostr = str
    tscmp = staticmethod(pypy_tscmp)

    def test_tscmp_neq(self):
        assert not self.tscmp(self.tostr('asd'), self.tostr('qwe'), 3, 3)

    def test_tscmp_eq(self):
        assert self.tscmp(self.tostr('asd'), self.tostr('asd'), 3, 3)

    def test_tscmp_len(self):
        assert self.tscmp(self.tostr('asdp'), self.tostr('asdq'), 3, 3)

    def test_tscmp_nlen(self):
        assert not self.tscmp(self.tostr('asd'), self.tostr('asd'), 2, 3)


class TestTimingSafeCompareWide(TestTimingSafeCompare):
    tostr = unicode
    tscmp = staticmethod(pypy_tscmp_wide)

    def test_tscmp_wide_nonascii(self):
        a, b = u"\ud808\udf45", u"\ud808\udf45"
        assert self.tscmp(a, b, len(a), len(b))
        a, b = u"\ud808\udf45", u"\ud808\udf45 "
        assert not self.tscmp(a, b, len(a), len(b))
