from pypy.interpreter.pyparser import parsestring

class TestParsetring:
    def test_simple(self):
        space = self.space
        s = 'hello world'
        w_ret = parsestring.parsestr(space, None, repr(s))
        assert space.str_w(w_ret) == s
        s = 'hello\n world'
        w_ret = parsestring.parsestr(space, None, repr(s))
        assert space.str_w(w_ret) == s
        s = "'''hello\\x42 world'''"
        w_ret = parsestring.parsestr(space, None, s)
        assert space.str_w(w_ret) == 'hello\x42 world'

    def test_unicode(self):
        space = self.space
        s = u'hello world'
        w_ret = parsestring.parsestr(space, None, repr(s))
        ret = space.unwrap(w_ret)
        assert isinstance(ret, unicode)
        assert ret == s
        s = u'hello\n world'
        w_ret = parsestring.parsestr(self.space, None, repr(s))
        ret = space.unwrap(w_ret)
        assert isinstance(ret, unicode)
        assert ret == s
        s = "u'''hello\\x42 world'''"
        w_ret = parsestring.parsestr(self.space, None, s)
        ret = space.unwrap(w_ret)
        assert isinstance(ret, unicode)
        assert ret == u'hello\x42 world'
        s = "u'''hello\\u0842 world'''"
        w_ret = parsestring.parsestr(self.space, None, s)
        ret = space.unwrap(w_ret)
        assert isinstance(ret, unicode)
        assert ret == u'hello\u0842 world'
        s = "u'\x81'"
        s = s.decode("koi8-u").encode("utf8")
        w_ret = parsestring.parsestr(self.space, 'koi8-u', s)
        ret = space.unwrap(w_ret)
        assert ret == u'\u2502'
