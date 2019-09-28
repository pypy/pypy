# coding: utf-8
import py
from pypy.module._codecs import interp_codecs
from pypy.module._codecs.locale import (
    str_decode_locale_surrogateescape,
    unicode_encode_locale_surrogateescape)
from rpython.rlib import rlocale
from pypy.interpreter import unicodehelper

class TestLocaleCodec(object):

    def setup_class(cls):
        from rpython.rlib import rlocale
        cls.oldlocale = rlocale.setlocale(rlocale.LC_ALL, None)

    def teardown_class(cls):
        if hasattr(cls, 'oldlocale'):
            from rpython.rlib import rlocale
            rlocale.setlocale(rlocale.LC_ALL, cls.oldlocale)

    def getdecoder(self, encoding):
        return getattr(unicodehelper, "str_decode_%s" % encoding.replace("-", ""))

    def getencoder(self, encoding):
        return getattr(unicodehelper,
                       "utf8_encode_%s" % encoding.replace("-", "_"))

    def getstate(self):
        return self.space.fromcache(interp_codecs.CodecState)

    def setlocale(self, locale):
        from rpython.rlib import rlocale
        try:
            rlocale.setlocale(rlocale.LC_ALL, locale)
        except rlocale.LocaleError:
            py.test.skip("%s locale unsupported" % locale)

    def test_encode_locale(self):
        self.setlocale("en_US.UTF-8")
        locale_encoder = unicode_encode_locale_surrogateescape
        utf8_encoder = self.getencoder('utf-8')
        for val in u'foo', u' 日本', u'\U0001320C':
            assert locale_encoder(val).decode('utf8') == val

    def test_encode_locale_errorhandler(self):
        self.setlocale("en_US.UTF-8")
        locale_encoder = unicode_encode_locale_surrogateescape
        utf8_encoder = self.getencoder('utf-8')
        encode_error_handler = self.getstate().encode_error_handler
        for val in u'foo\udc80bar', u'\udcff\U0001320C':
            expected = utf8_encoder(val.encode('utf8'), 'surrogateescape',
                                    encode_error_handler)
            assert locale_encoder(val) == expected

    def test_decode_locale(self):
        self.setlocale("en_US.UTF-8")
        locale_decoder = str_decode_locale_surrogateescape
        utf8_decoder = self.getdecoder('utf-8')
        for val in 'foo', ' \xe6\x97\xa5\xe6\x9c\xac', '\xf0\x93\x88\x8c':
            assert (locale_decoder(val) ==
                    utf8_decoder(val, 'strict', True, None)[:2])

    def test_decode_locale_latin1(self):
        self.setlocale("fr_FR")
        uni = u"août"
        string = uni.encode('latin1')
        assert str_decode_locale_surrogateescape(string) == (uni.encode('utf8'), len(uni))

    def test_decode_locale_errorhandler(self):
        self.setlocale("en_US.UTF-8")
        locale_decoder = str_decode_locale_surrogateescape
        utf8_decoder = self.getdecoder('utf-8')
        decode_error_handler = self.getstate().decode_error_handler
        val = 'foo\xe3bar'
        expected = utf8_decoder(val, 'surrogateescape', True,
                                decode_error_handler)
        assert locale_decoder(val) == expected[:2]
