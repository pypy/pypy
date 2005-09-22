from pypy.interpreter.pyparser import parsestring
import py

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
        s = r'"\0"'
        w_ret = parsestring.parsestr(space, None, s)
        assert space.str_w(w_ret) == chr(0)
        s = r'"\07"'
        w_ret = parsestring.parsestr(space, None, s)
        assert space.str_w(w_ret) == chr(7)
        s = r'"\123"'
        w_ret = parsestring.parsestr(space, None, s)
        assert space.str_w(w_ret) == chr(0123)
        s = r'"\x"'
        space.raises_w(space.w_ValueError, parsestring.parsestr, space, None, s)
        s = r'"\x7"'
        space.raises_w(space.w_ValueError, parsestring.parsestr, space, None, s)
        s = r'"\x7g"'
        space.raises_w(space.w_ValueError, parsestring.parsestr, space, None, s)
        s = r'"\xfF"'
        w_ret = parsestring.parsestr(space, None, s)
        assert space.str_w(w_ret) == chr(0xFF)

        s = r'"\""'
        w_ret = parsestring.parsestr(space, None, s)
        assert space.str_w(w_ret) == '"'
        
        s = r"'\''"
        w_ret = parsestring.parsestr(space, None, s)
        assert space.str_w(w_ret) == "'"
        
        
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
        assert ret == eval("# -*- coding: koi8-u -*-\nu'\x81'") 

    def test_simple_enc_roundtrip(self):
        #py.test.skip("crashes in app_codecs, but when cheating using .encode at interp-level passes?!")
        space = self.space
        s = "'\x81'"
        s = s.decode("koi8-u").encode("utf8")
        w_ret = parsestring.parsestr(self.space, 'koi8-u', s)
        ret = space.unwrap(w_ret)
        assert ret == eval("# -*- coding: koi8-u -*-\n'\x81'") 

