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
        s = b"Hello, ".__add__(b"World!")
        assert type(s) is bytes
        assert 'W_StringJoinObject' in __pypy__.internal_repr(s)

    def test_add_twice(self):
        x = b"a" + b""
        y = x + b"b"
        c = x + b"b"
        assert c == b"ab"

    def test_add(self):
        import __pypy__
        all = b""
        for i in range(20):
            all += str(i).encode()
        assert 'W_StringJoinObject' in __pypy__.internal_repr(all)

    def test_hash(self):
        import __pypy__
        # check that we have the same hash as CPython for at least 31 bits
        # (but don't go checking CPython's special case -1)
        # disabled: assert hash('') == 0 --- different special case
        def join(s): return s[:len(s) // 2] + s[len(s) // 2:]
        s = join(b'a' * 101)
        assert 'W_StringJoinObject' in __pypy__.internal_repr(s)
        assert hash(s) & 0x7fffffff == 0x7e0bce58

    def test_len(self):
        s = b"a" + b"b"
        r = b"c" + b"d"
        t = s + r
        assert len(s) == 2

    def test_add_strjoin_strjoin(self):
        # make three strjoin objects
        s = b'a' + b'b'
        t = b'c' + b'd'
        u = b'e' + b'f'

        # add two different strjoins to the same string
        v = s + t
        w = s + u

        # check that insanity hasn't resulted.
        assert len(v) == len(w) == 4

    def test_more_adding_fun(self):
        s = b'a' + b'b' # s is a strjoin now
        t = s + b'c'   # this calls s.force() which sets s.until to 1
        u = s + b'd'
        v = s + b'e'
        assert v == b'abe' # meaning u is abcd

    def test_buh_even_more(self):
        a = b'a' + b'b'
        b = a + b'c'
        c = b'0' + b'1'
        x = c + a
        assert x == b'01ab'

