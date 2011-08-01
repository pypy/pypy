from pypy.conftest import gettestobjspace


class AppTestStreams:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_multibytecodec'])
        cls.w_HzStreamReader = cls.space.appexec([], """():
            import _codecs_cn
            from _multibytecodec import MultibyteStreamReader

            class HzStreamReader(MultibyteStreamReader):
                codec = _codecs_cn.getcodec('hz')

            return HzStreamReader
        """)
        cls.w_HzStreamWriter = cls.space.appexec([], """():
            import _codecs_cn
            from _multibytecodec import MultibyteStreamWriter

            class HzStreamWriter(MultibyteStreamWriter):
                codec = _codecs_cn.getcodec('hz')

            return HzStreamWriter
        """)

    def test_reader(self):
        class FakeFile:
            def __init__(self, data):
                self.data = data
                self.pos = 0
            def read(self, size):
                res = self.data[self.pos : self.pos + size]
                self.pos += size
                return res
        #
        r = self.HzStreamReader(FakeFile("!~{abcd~}xyz~{efgh"))
        for expected in u'!\u5f95\u6c85xyz\u5f50\u73b7':
            c = r.read(1)
            assert c == expected
        c = r.read(1)
        assert c == ''

    def test_reader_replace(self):
        class FakeFile:
            def __init__(self, data):
                self.data = data
            def read(self):
                return self.data
        #
        r = self.HzStreamReader(FakeFile("!~{a"), "replace")
        c = r.read()
        assert c == u'!\ufffd'
        #
        r = self.HzStreamReader(FakeFile("!~{a"))
        r.errors = "replace"
        assert r.errors == "replace"
        c = r.read()
        assert c == u'!\ufffd'

    def test_writer(self):
        class FakeFile:
            def __init__(self):
                self.output = []
            def write(self, data):
                self.output.append(data)
        #
        w = self.HzStreamWriter(FakeFile())
        for input in u'!\u5f95\u6c85xyz\u5f50\u73b7':
            w.write(input)
        assert w.stream.output == ['!', '~{ab~}', '~{cd~}', 'x', 'y', 'z',
                                   '~{ef~}', '~{gh~}']
