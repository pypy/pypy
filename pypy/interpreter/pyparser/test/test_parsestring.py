from pypy.interpreter.pyparser import parsestring
import py

class TestParsetring:
    def parse_and_compare(self, literal, value):
        space = self.space
        w_ret = parsestring.parsestr(space, None, literal)
        if isinstance(value, str):
            assert space.type(w_ret) == space.w_str
            assert space.str_w(w_ret) == value
        elif isinstance(value, unicode):
            assert space.type(w_ret) == space.w_unicode
            assert space.unicode_w(w_ret) == value
        else:
            assert False

    def test_simple(self):
        space = self.space
        for s in ['hello world', 'hello\n world']:
            self.parse_and_compare(repr(s), s)

        self.parse_and_compare("'''hello\\x42 world'''", 'hello\x42 world')

        # octal
        self.parse_and_compare(r'"\0"', chr(0))
        self.parse_and_compare(r'"\07"', chr(7))
        self.parse_and_compare(r'"\123"', chr(0123))
        self.parse_and_compare(r'"\400"', chr(0))
        self.parse_and_compare(r'"\9"', '\\' + '9')
        self.parse_and_compare(r'"\08"', chr(0) + '8')

        # hexadecimal
        self.parse_and_compare(r'"\xfF"', chr(0xFF))
        self.parse_and_compare(r'"\""', '"')
        self.parse_and_compare(r"'\''", "'")
        for s in (r'"\x"', r'"\x7"', r'"\x7g"'):
            space.raises_w(space.w_ValueError,
                           parsestring.parsestr, space, None, s)

    def test_unicode(self):
        space = self.space
        for s in [u'hello world', u'hello\n world']:
            self.parse_and_compare(repr(s), s)

        self.parse_and_compare("u'''hello\\x42 world'''",
                               u'hello\x42 world')
        self.parse_and_compare("u'''hello\\u0842 world'''",
                               u'hello\u0842 world')

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

    def test_multiline_unicode_strings_with_backslash(self):
        space = self.space
        s = '"""' + '\\' + '\n"""'
        w_ret = parsestring.parsestr(space, None, s)
        assert space.str_w(w_ret) == ''
