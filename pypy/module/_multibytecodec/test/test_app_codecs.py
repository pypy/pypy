from pypy.conftest import gettestobjspace


class AppTestCodecs:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_multibytecodec'])

    def test_missing_codec(self):
        import _codecs_cn
        raises(LookupError, _codecs_cn.getcodec, "foobar")

    def test_decode_hz(self):
        import _codecs_cn
        codec = _codecs_cn.getcodec("hz")
        r = codec.decode("~{abc}")
        assert r == (u'\u5f95\u6cef', 6)

    def test_strict_error(self):
        import _codecs_cn
        codec = _codecs_cn.getcodec("hz")
        r = codec.decode("~{abc}", "strict")
        assert r == (u'\u5f95\u6cef', 6)

    def test_decode_hz_error(self):
        import _codecs_cn
        codec = _codecs_cn.getcodec("hz")
        e = raises(UnicodeDecodeError, codec.decode, "~{}").value
        assert e.args == ('hz', '~{}', 2, 3, 'incomplete multibyte sequence')
        assert e.encoding == 'hz'
        assert e.object == '~{}'
        assert e.start == 2
        assert e.end == 3
        assert e.reason == "incomplete multibyte sequence"
        #
        e = raises(UnicodeDecodeError, codec.decode, "~{xyz}").value
        assert e.args == ('hz', '~{xyz}', 2, 4, 'illegal multibyte sequence')
