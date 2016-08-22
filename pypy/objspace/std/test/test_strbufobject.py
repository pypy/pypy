import py

from pypy.objspace.std.test import test_bytesobject

class AppTestStringObject(test_bytesobject.AppTestBytesObject):
    spaceconfig = {"objspace.std.withstrbuf": True}

    def test_basic(self):
        import __pypy__
        # cannot do "Hello, " + "World!" because cpy2.5 optimises this
        # away on AST level
        s = "Hello, ".__add__("World!")
        assert type(s) is str
        assert 'W_StringBuilderObject' in __pypy__.internal_repr(s)

    def test_add_twice(self):
        x = "a".__add__("b")
        y = x + "c"
        c = x + "d"
        assert y == "abc"
        assert c == "abd"

    def test_add(self):
        import __pypy__
        all = ""
        for i in range(20):
            all += str(i)
        assert 'W_StringBuilderObject' in __pypy__.internal_repr(all)
        assert all == "012345678910111213141516171819"

    def test_hash(self):
        import __pypy__
        def join(s): return s[:len(s) // 2] + s[len(s) // 2:]
        t = 'a' * 101
        s = join(t)
        assert 'W_StringBuilderObject' in __pypy__.internal_repr(s)
        assert hash(s) == hash(t)

    def test_len(self):
        s = "a".__add__("b")
        r = "c".__add__("d")
        t = s + r
        assert len(s) == 2
        assert len(r) == 2
        assert len(t) == 4

    def test_buffer(self):
        s = b'a'.__add__(b'b')
        assert buffer(s) == buffer(b'ab')
        assert memoryview(s) == b'ab'

    def test_add_strbuf(self):
        # make three strbuf objects
        s = 'a'.__add__('b')
        t = 'x'.__add__('c')
        u = 'y'.__add__('d')

        # add two different strbufs to the same string
        v = s + t
        w = s + u

        # check that insanity hasn't resulted.
        assert v == "abxc"
        assert w == "abyd"

    def test_more_adding_fun(self):
        s = 'a'.__add__('b') # s is a strbuf now
        t = s + 'c'
        u = s + 'd'
        v = s + 'e'
        assert v == 'abe'
        assert u == 'abd'
        assert t == 'abc'

    def test_buh_even_more(self):
        a = 'a'.__add__('b')
        b = a + 'c'
        c = '0'.__add__('1')
        x = c + a
        assert x == '01ab'

    def test_add_non_string(self):
        a = 'a'
        a += 'b'
        raises(TypeError, "a += 5")
