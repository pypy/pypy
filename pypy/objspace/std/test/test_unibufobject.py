import py

from pypy.objspace.std.test import test_unicodeobject

class AppTestUnicodeObject(test_unicodeobject.AppTestUnicodeString):
    spaceconfig = test_unicodeobject.AppTestUnicodeString.spaceconfig.copy()
    spaceconfig.update({"objspace.std.withstrbuf": True})

    def test_basic(self):
        import __pypy__
        # cannot do "Hello, " + "World!" because cpy2.5 optimises this
        # away on AST level
        s = u"Hello, ".__add__(u"World!")
        assert type(s) is unicode
        assert 'W_UnicodeBufferObject' in __pypy__.internal_repr(s)

    def test_add_twice(self):
        x = u"a".__add__(u"b")
        y = x + u"c"
        c = x + u"d"
        assert y == u"abc"
        assert c == u"abd"

    def test_add(self):
        import __pypy__
        all = ""
        for i in range(20):
            all += unicode(i)
        assert 'W_UnicodeBufferObject' in __pypy__.internal_repr(all)
        assert all == u"012345678910111213141516171819"

    def test_hash(self):
        import __pypy__
        def join(s): return s[:len(s) // 2] + s[len(s) // 2:]
        t = u'a' * 101
        s = join(t)
        assert 'W_UnicodeBufferObject' in __pypy__.internal_repr(s)
        assert hash(s) == hash(t)

    def test_len(self):
        s = u"a".__add__(u"b")
        r = u"c".__add__(u"d")
        t = s + r
        assert len(s) == 2
        assert len(r) == 2
        assert len(t) == 4

    def test_add_strbuf(self):
        # make three strbuf objects
        s = u'a'.__add__(u'b')
        t = u'x'.__add__(u'c')
        u = u'y'.__add__(u'd')

        # add two different strbufs to the same string
        v = s + t
        w = s + u

        # check that insanity hasn't resulted.
        assert v == u"abxc"
        assert w == u"abyd"

    def test_more_adding_fun(self):
        s = u'a'.__add__(u'b') # s is a strbuf now
        t = s + u'c'
        u = s + u'd'
        v = s + u'e'
        assert v == u'abe'
        assert u == u'abd'
        assert t == u'abc'

    def test_buh_even_more(self):
        a = u'a'.__add__(u'b')
        b = a + u'c'
        c = u'0'.__add__(u'1')
        x = c + a
        assert x == u'01ab'

    def test_add_non_string(self):
        a = u'a'
        a += u'b'
        raises(TypeError, "a += 5")

    def test_add_plain_string(self):
        a = u'a'
        a += u'\u1234'
        a += 'b'
        assert a == u'a\u1234b'
        assert isinstance(a, unicode)

    def test_mix_strings_format(self):
        a = u'a'
        a += u'b'
        assert u'foo%s' % a == u'fooab'
        assert (a + u'%s') % (u'foo',) == u'abfoo'

    def test_print(self):
        a = u'abc'
        a += u'bc'
        print a

    def test_formatter_parser(self):
        a = u'abc'
        a += u'bc'
        assert list(a._formatter_parser()) == [(u'abcbc', None, None, None)]

    def test_startswith_s(self):
        a = u'abc'
        a += u'bc'
        assert a.startswith('abcb')
        assert not a.startswith('1234')
