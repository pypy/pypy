import autopath, py

from pypy.objspace.std.test import test_stringobject
from pypy.conftest import gettestobjspace

class AppTestStringObject(test_stringobject.AppTestStringObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withstrjoin": True})

    def test_basic(self):
        import pypymagic
        s = "Hello, " + "World!"
        assert type(s) is str
        assert 'W_StringJoinObject' in pypymagic.pypy_repr(s)

    def test_function_with_strjoin(self):
        skip("Failing")
        def f(x, y):
            if x[-1] != "/":
                x += "/"
            if y.startswith(x):
                return y[len(x):]

        x = "a"
        y = "a/b/c/d"
        x += ""
        y += ""

        assert f(x, y)
        assert f(x, y)

    def test_add(self):
        import pypymagic
        all = ""
        for i in range(20):
            all += str(i)
        assert 'W_StringJoinObject' in pypymagic.pypy_repr(all)

    def test_hash(self):
        import pypymagic
        # check that we have the same hash as CPython for at least 31 bits
        # (but don't go checking CPython's special case -1)
        # disabled: assert hash('') == 0 --- different special case
        def join(s): return s[:len(s) // 2] + s[len(s) // 2:]
        s = join('a' * 101)
        assert 'W_StringJoinObject' in pypymagic.pypy_repr(s)
        assert hash(s) & 0x7fffffff == 0x7e0bce58

    def test_len(self):
        s = "a" + "b"
        r = "c" + "d"
        t = s + r
        assert len(s) == 2
