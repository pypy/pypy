import py

from pypy.objspace.std.test import test_bytesobject

class AppTestStringObject(test_bytesobject.AppTestBytesObject):
    spaceconfig = {"objspace.std.withstrbuf": True}

    def test_basic(self):
        import __pypy__
        # cannot do "Hello, " + "World!" because cpy2.5 optimises this
        # away on AST level
        s = b"Hello, ".__add__(b"World!")
        assert type(s) is bytes
        assert 'W_StringBufferObject' in __pypy__.internal_repr(s)

    def test_add_twice(self):
        x = b"a".__add__(b"b")
        y = x + b"c"
        c = x + b"d"
        assert y == b"abc"
        assert c == b"abd"

    def test_add(self):
        import __pypy__
        all = b""
        for i in range(20):
            all += str(i).encode()
        assert 'W_StringBufferObject' in __pypy__.internal_repr(all)
        assert all == b"012345678910111213141516171819"

    def test_hash(self):
        import __pypy__
        def join(s): return s[:len(s) // 2] + s[len(s) // 2:]
        t = b'a' * 101
        s = join(t)
        assert 'W_StringBufferObject' in __pypy__.internal_repr(s)
        assert hash(s) == hash(t)

    def test_len(self):
        s = b"a".__add__(b"b")
        r = b"c".__add__(b"d")
        t = s + r
        assert len(s) == 2
        assert len(r) == 2
        assert len(t) == 4

    def test_buffer(self):
        s = 'a'.__add__('b')
        assert buffer(s) == buffer('ab')
        assert memoryview(s) == 'ab'

    def test_add_strbuf(self):
        # make three strbuf objects
        s = b'a'.__add__(b'b')
        t = b'x'.__add__(b'c')
        u = b'y'.__add__(b'd')

        # add two different strbufs to the same string
        v = s + t
        w = s + u

        # check that insanity hasn't resulted.
        assert v == b"abxc"
        assert w == b"abyd"

    def test_more_adding_fun(self):
        s = b'a'.__add__(b'b') # s is a strbuf now
        t = s + b'c'
        u = s + b'd'
        v = s + b'e'
        assert v == b'abe'
        assert u == b'abd'
        assert t == b'abc'

    def test_buh_even_more(self):
        a = b'a'.__add__(b'b')
        b = a + b'c'
        c = b'0'.__add__(b'1')
        x = c + a
        assert x == b'01ab'
