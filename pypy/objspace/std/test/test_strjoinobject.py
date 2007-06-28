import py

from pypy.objspace.std.test import test_stringobject
from pypy.conftest import gettestobjspace

class AppTestStringObject(test_stringobject.AppTestStringObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withstrjoin": True})

    def test_basic(self):
        import __pypy__
        # cannot do "Hello, " + "World!" because cpy2.5 optimises this
        # away on AST level (no idea why it doesn't this one)
        s = "Hello, ".__add__("World!")
        assert type(s) is str
        assert 'W_StringJoinObject' in __pypy__.internal_repr(s)

    def test_add_twice(self):
        x = "a" + ""
        y = x + "b"
        c = x + "b"
        assert c == "ab"

    def test_add(self):
        import __pypy__
        all = ""
        for i in range(20):
            all += str(i)
        assert 'W_StringJoinObject' in __pypy__.internal_repr(all)

    def test_hash(self):
        import __pypy__
        # check that we have the same hash as CPython for at least 31 bits
        # (but don't go checking CPython's special case -1)
        # disabled: assert hash('') == 0 --- different special case
        def join(s): return s[:len(s) // 2] + s[len(s) // 2:]
        s = join('a' * 101)
        assert 'W_StringJoinObject' in __pypy__.internal_repr(s)
        assert hash(s) & 0x7fffffff == 0x7e0bce58

    def test_len(self):
        s = "a" + "b"
        r = "c" + "d"
        t = s + r
        assert len(s) == 2

    def test_add_strjoin_strjoin(self):
        # make three strjoin objects
        s = 'a' + 'b'
        t = 'c' + 'd'
        u = 'e' + 'f'

        # add two different strjoins to the same string
        v = s + t
        w = s + u

        # check that insanity hasn't resulted.
        assert len(v) == len(w) == 4

    def test_more_adding_fun(self):
        s = 'a' + 'b' # s is a strjoin now
        t = s + 'c'   # this calls s.force() which sets s.until to 1
        u = s + 'd'
        v = s + 'e'
        assert v == 'abe' # meaning u is abcd

    def test_buh_even_more(self):
        a = 'a' + 'b'
        b = a + 'c'
        c = '0' + '1'
        x = c + a
        assert x == '01ab'

