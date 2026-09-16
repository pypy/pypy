# coding: utf-8
import sys
import pytest
from pypy.module._codecs import interp_codecs
from pypy.module._codecs.locale import (
    str_decode_locale_surrogateescape, utf8_encode_locale_surrogateescape,
    str_decode_locale_strict, utf8_encode_locale_strict)
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
            pytest.skip("%s locale unsupported" % locale)

    def test_encode_locale(self):
        self.setlocale("en_US.UTF-8")
        for locale_encoder in (utf8_encode_locale_surrogateescape,
                               utf8_encode_locale_strict):
            for val in u'foo', u' 日本', u'\U0001320C':
                utf8 = val.encode('utf-8')
                encoded = locale_encoder(utf8, len(val))
                assert encoded.decode('utf8') == val

    def test_encode_locale_errorhandler(self):
        self.setlocale("en_US.UTF-8")
        locale_encoder = utf8_encode_locale_surrogateescape
        utf8_encoder = self.getencoder('utf-8')
        encode_error_handler = self.getstate().encode_error_handler
        for val in u'foo\udc80bar', u'\udcff\U0001320C':
            s = val.encode('utf8')
            w_s = self.space.newtext(s)
            expected = utf8_encoder(self.space, s, w_s, 'surrogateescape',
                                    encode_error_handler)
            utf8 = val.encode('utf-8')
            assert locale_encoder(utf8, len(val)) == expected

    def test_decode_locale(self):
        self.setlocale("en_US.UTF-8")
        utf8_decoder = self.getdecoder('utf-8')
        values = ['foo', ' \xe6\x97\xa5\xe6\x9c\xac']
        if sys.platform != 'win32':
            # the UCRT's mbstowcs() emits one wchar_t per character, so a
            # non-BMP character decodes to U+FFFD, in CPython as well
            values.append('\xf0\x93\x88\x8c')
        for locale_decoder in (str_decode_locale_surrogateescape,
                               str_decode_locale_strict):
            for val in values:
                w_s = self.space.newbytes(val)
                assert (locale_decoder(val) ==
                                utf8_decoder(self.space, val, w_s, 'strict',
                                             True, None)[:2])

    @pytest.mark.parametrize('locale_decoder',
                 (str_decode_locale_surrogateescape, str_decode_locale_strict))
    def test_decode_locale_latin1(self, locale_decoder):
        self.setlocale("fr_FR")
        uni = u"août"
        string = uni.encode('latin1')
        assert locale_decoder(string) == (uni.encode('utf8'), len(uni))

    def test_decode_locale_errorhandler(self):
        self.setlocale("en_US.UTF-8")
        locale_decoder = str_decode_locale_surrogateescape
        utf8_decoder = self.getdecoder('utf-8')
        decode_error_handler = self.getstate().decode_error_handler
        val = 'foo\xe3bar'
        w_val = self.space.newbytes(val)
        expected = utf8_decoder(self.space, val, w_val, 'surrogateescape', True,
                                decode_error_handler)
        assert locale_decoder(val) == expected[:2]

    def test_utf16_wchar_buffer(self, monkeypatch):
        # with a 16-bit wchar_t (Windows), non-BMP code points must be
        # passed to the C library as surrogate pairs and merged back
        from pypy.module._codecs import locale
        from rpython.rlib.rarithmetic import r_uint
        monkeypatch.setattr(locale, '_should_split_surrogates', lambda: True)
        monkeypatch.setattr(locale, '_should_merge_surrogates', lambda: False)
        utf8 = u'a\U0001320C\udcffz'.encode('utf-8')
        with locale.scoped_utf82rawwcharp(utf8, 4) as buf:
            units = [int(r_uint(buf[i])) for i in range(6)]
            assert units == [0x61, 0xD80C, 0xDE0C, 0xDCFF, 0x7A, 0]
            assert locale.rawwcharp2utf8en(buf, 5) == (utf8, 4)
        assert locale._wchar_pos_to_index(utf8, 0) == 0
        assert locale._wchar_pos_to_index(utf8, 1) == 1
        assert locale._wchar_pos_to_index(utf8, 3) == 2
        assert locale._wchar_pos_to_index(utf8, 4) == 3
