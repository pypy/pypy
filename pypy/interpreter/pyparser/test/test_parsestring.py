from pypy.interpreter.pyparser import parsestring
import py, sys

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

    def test_unicode_literals(self):
        space = self.space
        w_ret = parsestring.parsestr(space, None, repr("hello"), True)
        assert space.isinstance_w(w_ret, space.w_unicode)
        w_ret = parsestring.parsestr(space, None, "b'hi'", True)
        assert space.isinstance_w(w_ret, space.w_str)
        w_ret = parsestring.parsestr(space, None, "r'hi'", True)
        assert space.isinstance_w(w_ret, space.w_unicode)

    def test_bytes(self):
        space = self.space
        b = "b'hello'"
        w_ret = parsestring.parsestr(space, None, b)
        assert space.unwrap(w_ret) == "hello"
        b = "b'''hello'''"
        w_ret = parsestring.parsestr(space, None, b)
        assert space.unwrap(w_ret) == "hello"

    def test_simple_enc_roundtrip(self):
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

    def test_bug1(self):
        space = self.space
        expected = ['x', ' ', chr(0xc3), chr(0xa9), ' ', '\n']
        input = ["'", 'x', ' ', chr(0xc3), chr(0xa9), ' ', chr(92), 'n', "'"]
        w_ret = parsestring.parsestr(space, 'utf8', ''.join(input))
        assert space.str_w(w_ret) == ''.join(expected)

    def test_wide_unicode_in_source(self):
        if sys.maxunicode == 65535:
            py.test.skip("requires a wide-unicode host")
        self.parse_and_compare('u"\xf0\x9f\x92\x8b"',
                               unichr(0x1f48b),
                               encoding='utf-8')

    def test_decode_unicode_utf8(self):
        buf = parsestring.decode_unicode_utf8(self.space,
                                              'u"\xf0\x9f\x92\x8b"', 2, 6)
        if sys.maxunicode == 65535:
            assert buf == r"\U0000d83d\U0000dc8b"
        else:
            assert buf == r"\U0001f48b"
