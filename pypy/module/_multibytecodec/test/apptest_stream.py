# spaceconfig = {"usemodules": ["_multibytecodec", "_codecs"]}
import _codecs_cn
import _codecs_jp
from _multibytecodec import MultibyteStreamReader, MultibyteStreamWriter


class HzStreamReader(MultibyteStreamReader):
    codec = _codecs_cn.getcodec('hz')


class HzStreamWriter(MultibyteStreamWriter):
    codec = _codecs_cn.getcodec('hz')


class ShiftJisx0213StreamWriter(MultibyteStreamWriter):
    codec = _codecs_jp.getcodec('shift_jisx0213')


def test_reader():
    class FakeFile:
        def __init__(self, data):
            self.data = data
            self.pos = 0
        def read(self, size):
            res = self.data[self.pos : self.pos + size]
            self.pos += size
            return res

    r = HzStreamReader(FakeFile(b"!~{abcd~}xyz~{efgh"))
    for expected in '!\u5f95\u6c85xyz\u5f50\u73b7':
        c = r.read(1)
        assert c == expected
    c = r.read(1)
    assert c == ''


def test_reader_replace():
    class FakeFile:
        def __init__(self, data):
            self.data = data
        def read(self):
            return self.data

    r = HzStreamReader(FakeFile(b"!~{a"), "replace")
    c = r.read()
    assert c == '!\ufffd'
    #
    r = HzStreamReader(FakeFile(b"!~{a"))
    r.errors = "replace"
    assert r.errors == "replace"
    c = r.read()
    assert c == '!\ufffd'


def test_writer():
    class FakeFile:
        def __init__(self):
            self.output = []
        def write(self, data):
            self.output.append(data)

    w = HzStreamWriter(FakeFile())
    for char in '!\u5f95\u6c85xyz\u5f50\u73b7':
        w.write(char)
    w.reset()
    assert w.stream.output == [b'!', b'~{ab', b'cd', b'~}x', b'y', b'z',
                               b'~{ef', b'gh', b'~}']


def test_no_flush():
    class FakeFile:
        def __init__(self):
            self.output = []
        def write(self, data):
            self.output.append(data)

    w = ShiftJisx0213StreamWriter(FakeFile())
    w.write('\u30ce')
    w.write('\u304b')
    w.write('\u309a')
    assert w.stream.output == [b'\x83m', b'', b'\x82\xf5']


def test_writer_seek_no_empty_write():
    # issue #2293: codecs.py will sometimes issue a reset()
    # on a StreamWriter attached to a file that is not opened
    # for writing at all.  We must not emit a "write('')"!
    class FakeFile:
        def write(self, data):
            raise IOError("can't write!")

    w = ShiftJisx0213StreamWriter(FakeFile())
    w.reset()
    # assert did not crash
