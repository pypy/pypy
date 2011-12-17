from pypy.conftest import gettestobjspace


class AppTestClasses:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_multibytecodec'])
        cls.w_IncrementalHzDecoder = cls.space.appexec([], """():
            import _codecs_cn
            from _multibytecodec import MultibyteIncrementalDecoder

            class IncrementalHzDecoder(MultibyteIncrementalDecoder):
                codec = _codecs_cn.getcodec('hz')

            return IncrementalHzDecoder
        """)
        cls.w_IncrementalHzEncoder = cls.space.appexec([], """():
            import _codecs_cn
            from _multibytecodec import MultibyteIncrementalEncoder

            class IncrementalHzEncoder(MultibyteIncrementalEncoder):
                codec = _codecs_cn.getcodec('hz')

            return IncrementalHzEncoder
        """)
        cls.w_IncrementalBig5hkscsEncoder = cls.space.appexec([], """():
            import _codecs_cn
            from _multibytecodec import MultibyteIncrementalEncoder

            class IncrementalBig5hkscsEncoder(MultibyteIncrementalEncoder):
                codec = _codecs_cn.getcodec('big5hkscs')

            return IncrementalBig5hkscsEncoder
        """)

    def test_decode_hz(self):
        d = self.IncrementalHzDecoder()
        r = d.decode(b"~{abcd~}")
        assert r == '\u5f95\u6c85'
        r = d.decode(b"~{efgh~}")
        assert r == '\u5f50\u73b7'
        for c, output in zip(b"!~{abcd~}xyz~{efgh",
              ['!',  # !
               '',   # ~
               '',   # {
               '',   # a
               '\u5f95',   # b
               '',   # c
               '\u6c85',   # d
               '',   # ~
               '',   # }
               'x',  # x
               'y',  # y
               'z',  # z
               '',   # ~
               '',   # {
               '',   # e
               '\u5f50',   # f
               '',   # g
               '\u73b7',   # h
               ]):
            r = d.decode(bytes([c]))
            assert r == output

    def test_decode_hz_final(self):
        d = self.IncrementalHzDecoder()
        r = d.decode(b"~{", True)
        assert r == ''
        raises(UnicodeDecodeError, d.decode, b"~", True)
        raises(UnicodeDecodeError, d.decode, b"~{a", True)

    def test_decode_hz_reset(self):
        d = self.IncrementalHzDecoder()
        r = d.decode(b"ab")
        assert r == 'ab'
        r = d.decode(b"~{")
        assert r == ''
        r = d.decode(b"ab")
        assert r == '\u5f95'
        r = d.decode(b"ab")
        assert r == '\u5f95'
        d.reset()
        r = d.decode(b"ab")
        assert r == 'ab'

    def test_decode_hz_error(self):
        d = self.IncrementalHzDecoder()
        raises(UnicodeDecodeError, d.decode, b"~{abc", True)
        d = self.IncrementalHzDecoder("ignore")
        r = d.decode(b"~{abc", True)
        assert r == u'\u5f95'
        d = self.IncrementalHzDecoder()
        d.errors = "replace"
        r = d.decode(b"~{abc", True)
        assert r == '\u5f95\ufffd'

    def test_decode_hz_buffer_grow(self):
        d = self.IncrementalHzDecoder()
        for i in range(13):
            r = d.decode(b"a" * (2**i))
            assert r == "a" * (2**i)

    def test_encode_hz(self):
        e = self.IncrementalHzEncoder()
        r = e.encode("abcd")
        assert r == b'abcd'
        r = e.encode("\u5f95\u6c85")
        assert r == b'~{abcd~}'
        r = e.encode("\u5f50")
        assert r == b'~{ef~}'
        r = e.encode("\u73b7")
        assert r == b'~{gh~}'

    def test_encode_hz_final(self):
        e = self.IncrementalHzEncoder()
        r = e.encode("xyz\u5f95\u6c85", True)
        assert r == b'xyz~{abcd~}'
        # This is a bit hard to test, because the only way I can see that
        # encoders can return MBERR_TOOFEW is with surrogates, which only
        # occur with 2-byte unicode characters...  We will just have to
        # trust that the logic works, because it is exactly the same one
        # as in the decode case :-/

    def test_encode_hz_reset(self):
        # Same issue as with test_encode_hz_final
        e = self.IncrementalHzEncoder()
        r = e.encode("xyz\u5f95\u6c85", True)
        assert r == b'xyz~{abcd~}'
        e.reset()
        r = e.encode("xyz\u5f95\u6c85")
        assert r == b'xyz~{abcd~}'

    def test_encode_hz_error(self):
        e = self.IncrementalHzEncoder()
        raises(UnicodeEncodeError, e.encode, "\u4321", True)
        e = self.IncrementalHzEncoder("ignore")
        r = e.encode("xy\u4321z", True)
        assert r == b'xyz'
        e = self.IncrementalHzEncoder()
        e.errors = "replace"
        r = e.encode("xy\u4321z", True)
        assert r == b'xy?z'

    def test_encode_hz_buffer_grow(self):
        e = self.IncrementalHzEncoder()
        for i in range(13):
            r = e.encode("a" * (2**i))
            assert r == b"a" * (2**i)

    def test_encode_big5hkscs(self):
        #e = self.IncrementalBig5hkscsEncoder()
        #r = e.encode('\xca', True)
        #assert r == b'\x88f'
        #r = e.encode('\xca', True)
        #assert r == b'\x88f'
        #raises(UnicodeEncodeError, e.encode, '\u0304', True)
        #
        e = self.IncrementalBig5hkscsEncoder()
        r = e.encode('\xca')
        assert r == b''
        r = e.encode('\xca')
        assert r == b'\x88f'
        r = e.encode('\u0304')
        assert r == b'\x88b'
