"""Unit tests for streamio (new standard I/O)."""

import os
import time
from pypy.tool.udir import udir

from pypy.rlib import streamio

from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin


class TSource(streamio.Stream):

    def __init__(self, packets):
        for x in packets:
            assert x
        self.orig_packets = packets[:]
        self.packets = packets[:]
        self.pos = 0
        self.chunks = []

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        if whence == 1:
            offset += self.pos
        elif whence == 2:
            for packet in self.orig_packets:
                offset += len(packet)
        else:
            assert whence == 0
        self.packets = list(self.orig_packets)
        self.pos = 0
        while self.pos < offset:
            data = self.read(offset - self.pos)
            assert data
        assert self.pos == offset

    def read(self, n):
        assert n >= 0
        try:
            data = self.packets.pop(0)
        except IndexError:
            return ""
        if len(data) > n:
            data, rest = data[:n], data[n:]
            self.packets.insert(0, rest)
        self.chunks.append((n, len(data), self.pos))
        self.pos += len(data)
        return data

    def close(self):
        pass

class TReader(TSource):

    def flush(self):
        pass

class TWriter(streamio.Stream):

    def __init__(self, data=''):
        self.buf = data
        self.chunks = []
        self.pos = 0

    def write(self, data):
        self.chunks.append((self.pos, data))
        if self.pos >= len(self.buf):
            self.buf += "\0" * (self.pos - len(self.buf)) + data
            self.pos = len(self.buf)
        else:
            start = self.pos
            assert start >= 0
            self.buf = (self.buf[:start] + data +
                        self.buf[start + len(data):])
            self.pos += len(data)

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        if whence == 0:
            pass
        elif whence == 1:
            offset += self.pos
        elif whence == 2:
            offset += len(self.buf)
        else:
            raise ValueError, "whence should be 0, 1 or 2"
        if offset < 0:
            offset = 0
        self.pos = offset

    def close(self):
        pass

    def truncate(self, size=None):
        if size is None:
            size = self.pos
        if size <= len(self.buf):
            self.buf = self.buf[:size]
        else:
            self.buf += '\0' * (size - len(self.buf))

    def flush(self):
        pass
            
class TReaderWriter(TWriter):

    def read(self, n=-1):
        start = self.pos
        assert start >= 0
        if n < 1:
            result = self.buf[start: ]
            self.pos = len(self.buf)
        else:
            if n > len(self.buf) - start:
                n = len(self.buf) - start
            stop = start + n
            assert stop >= 0
            result = self.buf[start: stop]
            self.pos += n
        return result
    
class BaseTestBufferingInputStreamTests(BaseRtypingTest):

    packets = ["a", "b", "\n", "def", "\nxy\npq\nuv", "wx"]
    lines = ["ab\n", "def\n", "xy\n", "pq\n", "uvwx"]

    def _freeze_(self):
        return True

    def makeStream(self, tell=False, seek=False, bufsize=-1):
        base = TSource(self.packets)
        self.source = base
        def f(*args):
            raise NotImplementedError
        if not tell:
            base.tell = f
        if not seek:
            base.seek = f

        return streamio.BufferingInputStream(base, bufsize)

    def test_readline(self):
        for file in [self.makeStream(), self.makeStream(bufsize=1)]:
            def f():
                i = 0
                result = True
                while 1:
                    r = file.readline()
                    if r == "":
                        break
                    result = result and self.lines[i] == r
                    i += 1
                return result
            res = self.interpret(f, [])
            assert res

    def test_readall(self):
        file = self.makeStream()
        def f():
            return file.readall() == "".join(self.lines)
        res = self.interpret(f, [])
        assert res

    def test_readall_small_bufsize(self):
        file = self.makeStream(bufsize=1)
        def f():
            return file.readall() == "".join(self.lines)
        res = self.interpret(f, [])
        assert res

    def test_readall_after_readline(self):
        file = self.makeStream()
        def f():
            return (file.readline() == self.lines[0] and
                    file.readline() == self.lines[1] and
                    file.readall() == "".join(self.lines[2:]))
        res = self.interpret(f, [])
        assert res

    def test_read_1_after_readline(self):
        file = self.makeStream()
        def f():
            assert file.readline() == "ab\n"
            assert file.readline() == "def\n"
            os.write(1, "3\n")
            blocks = []
            while 1:
                block = file.read(1)
                os.write(1, "XXXX" + block + "YYYY")
                os.write(1, "4\n")
                if not block:
                    break
                os.write(1, "5\n")
                blocks.append(block)
                assert file.read(0) == ""
            os.write(1, "6\n")
            return "".join(blocks) == "".join(self.lines)[7:]
        res = self.interpret(f, [])
        assert res

    def test_read_1(self):
        file = self.makeStream()
        def f():
            blocks = []
            while 1:
                block = file.read(1)
                if not block:
                    break
                blocks.append(block)
                assert file.read(0) == ""
            return "".join(blocks) == "".join(self.lines)
        res = self.interpret(f, [])
        assert res

    def test_read_2(self):
        file = self.makeStream()
        def f():
            blocks = []
            while 1:
                block = file.read(2)
                if not block:
                    break
                blocks.append(block)
                assert file.read(0) == ""
            return blocks == ["ab", "\nd", "ef", "\nx", "y\n", "pq",
                              "\nu", "vw", "x"]
        res = self.interpret(f, [])
        assert res

    def test_read_4(self):
        file = self.makeStream()
        def f():
            blocks = []
            while 1:
                block = file.read(4)
                if not block:
                    break
                blocks.append(block)
                assert file.read(0) == ""
            return blocks == ["ab\nd", "ef\nx", "y\npq", "\nuvw", "x"]
        res = self.interpret(f, [])
        assert res
        
    def test_read_4_after_readline(self):
        file = self.makeStream()
        def f():
            os.write(1, "1\n")
            res = file.readline()
            assert res == "ab\n"
            os.write(1, "2\n")
            assert file.readline() == "def\n"
            os.write(1, "3\n")
            blocks = [file.read(4)]
            while 1:
                block = file.read(4)
                if not block:
                    break
                blocks.append(block)
                os.write(1, "4\n")
                assert file.read(0) == ""
            os.write(1, "5\n")
            for element in blocks:
                os.write(1, element + "XXX\n")
            return blocks == ["xy\np", "q\nuv", "wx"]
        res = self.interpret(f, [])
        assert res

    def test_read_4_small_bufsize(self):
        file = self.makeStream(bufsize=1)
        def f():
            blocks = []
            while 1:
                block = file.read(4)
                if not block:
                    break
                blocks.append(block)
            return blocks == ["ab\nd", "ef\nx", "y\npq", "\nuvw", "x"]
        res = self.interpret(f, [])
        assert res

    def test_tell_1(self):
        file = self.makeStream(tell=True)
        def f():
            pos = 0
            while 1:
                assert file.tell() == pos
                n = len(file.read(1))
                if not n:
                    break
                pos += n
            return True
        res = self.interpret(f, [])
        assert res

    def test_tell_1_after_readline(self):
        file = self.makeStream(tell=True)
        def f():
            pos = 0
            pos += len(file.readline())
            assert file.tell() == pos
            pos += len(file.readline())
            assert file.tell() == pos
            while 1:
                assert file.tell() == pos
                n = len(file.read(1))
                if not n:
                    break
                pos += n
            return True
        res = self.interpret(f, [])
        assert res

    def test_tell_2(self):
        file = self.makeStream(tell=True)
        def f():
            pos = 0
            while 1:
                assert file.tell() == pos
                n = len(file.read(2))
                if not n:
                    break
                pos += n
            return True
        res = self.interpret(f, [])
        assert res

    def test_tell_4(self):
        file = self.makeStream(tell=True)
        def f():
            pos = 0
            while 1:
                assert file.tell() == pos
                n = len(file.read(4))
                if not n:
                    break
                pos += n
            return True
        res = self.interpret(f, [])
        assert res

    def test_tell_readline(self):
        file = self.makeStream(tell=True)
        def f():
            pos = 0
            while 1:
                assert file.tell() == pos
                n = len(file.readline())
                if not n:
                    break
                pos += n
            return True
        res = self.interpret(f, [])
        assert res

    def test_seek(self):
        file = self.makeStream(tell=True, seek=True)
        def f():
            all = file.readall()
            end = len(all)
            for readto in range(0, end+1):
                for seekto in range(0, end+1):
                    for whence in [0, 1, 2]:
                        file.seek(0)
                        assert file.tell() == 0
                        head = file.read(readto)
                        assert head == all[:readto]
                        if whence == 1:
                            offset = seekto - readto
                        elif whence == 2:
                            offset = seekto - end
                        else:
                            offset = seekto
                        file.seek(offset, whence)
                        here = file.tell()
                        assert here == seekto
                        rest = file.readall()
                        assert rest == all[seekto:]
            return True
        res = self.interpret(f, [])
        assert res

    def test_seek_noseek(self):
        file = self.makeStream()
        all = file.readall()
        end = len(all)
        def f():
            for readto in range(0, end+1):
                for seekto in range(readto, end+1):
                    for whence in [1, 2]:
                        base = TSource(self.packets)
                        file = streamio.BufferingInputStream(base)
                        head = file.read(readto)
                        assert head == all[:readto]
                        offset = 42 # for the flow space
                        if whence == 1:
                            offset = seekto - readto
                        elif whence == 2:
                            offset = seekto - end
                        file.seek(offset, whence)
                        rest = file.readall()
                        assert rest == all[seekto:]
            return True
        res = self.interpret(f, [])
        assert res

class TestBufferingInputStreamTests(BaseTestBufferingInputStreamTests):
    def interpret(self, func, args, **kwds):
        return func(*args)

class TestBufferingInputStreamTestsLLinterp(BaseTestBufferingInputStreamTests,
                                            LLRtypeMixin):
    pass

class TestBufferedRead:
    packets = ["a", "b", "\n", "def", "\nxy\npq\nuv", "wx"]
    lines = ["ab\n", "def\n", "xy\n", "pq\n", "uvwx"]

    def makeStream(self, tell=False, seek=False, bufsize=-1):
        base = TSource(self.packets)
        self.source = base
        def f(*args):
            raise NotImplementedError
        if not tell:
            base.tell = f
        if not seek:
            base.seek = f
        return streamio.BufferingInputStream(base, bufsize)

    def test_dont_read_small(self):
        import sys
        file = self.makeStream(bufsize=4)
        while file.read(1): pass
        for want, got, pos in self.source.chunks:
            assert want >= 4

class BaseTestBufferingOutputStream(BaseRtypingTest):

    def test_write(self):
        def f():
            base = TWriter()
            filter = streamio.BufferingOutputStream(base, 4)
            filter.write("123")
            assert not base.chunks
            assert filter.tell() == 3
            filter.write("456")
            filter.write("789ABCDEF")
            filter.write("0123")
            assert filter.tell() == 19
            filter.close()
            assert base.buf == "123456789ABCDEF0123"
            for chunk in base.chunks[:-1]:
                assert len(chunk[1]) >= 4
        self.interpret(f, [])

    def test_write_seek(self):
        def f():
            base = TWriter()
            filter = streamio.BufferingOutputStream(base, 4)
            filter.write("x"*6)
            filter.seek(3)
            filter.write("y"*2)
            filter.close()
            assert base.buf == "x"*3 + "y"*2 + "x"*1
        self.interpret(f, [])

    def test_write_seek_beyond_end(self):
        "Linux behaviour. May be different on other platforms."
        def f():
            base = TWriter()
            filter = streamio.BufferingOutputStream(base, 4)
            filter.seek(3)
            filter.write("y"*2)
            filter.close()
            assert base.buf == "\0"*3 + "y"*2
        self.interpret(f, [])

    def test_truncate(self):
        "Linux behaviour. May be different on other platforms."
        def f():
            base = TWriter()
            filter = streamio.BufferingOutputStream(base, 4)
            filter.write('x')
            filter.truncate(4)
            filter.write('y')
            filter.close()
            assert base.buf == 'xy' + '\0' * 2
        self.interpret(f, [])

    def test_truncate2(self):
        "Linux behaviour. May be different on other platforms."
        def f():
            base = TWriter()
            filter = streamio.BufferingOutputStream(base, 4)
            filter.write('12345678')
            filter.truncate(4)
            filter.write('y')
            filter.close()
            assert base.buf == '1234' + '\0' * 4 + 'y'
        self.interpret(f, [])

class TestBufferingOutputStream(BaseTestBufferingOutputStream):
    def interpret(self, func, args, **kwds):
        return func(*args)

class TestBufferingOutputStreamLLinterp(BaseTestBufferingOutputStream,
                                        LLRtypeMixin):
    pass
    

class BaseTestLineBufferingOutputStream(BaseRtypingTest):

    def test_write(self):
        base = TWriter()
        filter = streamio.LineBufferingOutputStream(base)
        def f():
            filter.bufsize = 4 # More handy for testing than the default
            filter.write("123")
            assert base.buf == ""
            assert filter.tell() == 3
            filter.write("456")
            assert base.buf == "1234"
            filter.write("789ABCDEF\n")
            assert base.buf == "123456789ABCDEF\n"
            filter.write("0123")
            assert base.buf == "123456789ABCDEF\n0123"
            assert filter.tell() == 20
            filter.close()
            assert base.buf == "123456789ABCDEF\n0123"
        self.interpret(f, [])

    def xtest_write_seek(self):
        base = TWriter()
        filter = streamio.BufferingOutputStream(base, 4)
        filter.write("x"*6)
        filter.seek(3)
        filter.write("y"*2)
        filter.close()
        assert base.buf == "x"*3 + "y"*2 + "x"*1

class TestLineBufferingOutputStream(BaseTestLineBufferingOutputStream):
    def interpret(self, func, args, **kwds):
        return func(*args)

class TestLineBufferingOutputStreamLLinterp(BaseTestLineBufferingOutputStream,
                                        LLRtypeMixin):
    pass
    

class TestCRLFFilter:

    def test_filter(self):
        packets = ["abc\ndef\rghi\r\nxyz\r", "123\r", "\n456"]
        expected = ["abc\ndef\nghi\nxyz\n", "123\n", "456"]
        crlf = streamio.CRLFFilter(TSource(packets))
        blocks = []
        while 1:
            block = crlf.read(100)
            if not block:
                break
            blocks.append(block)
        assert blocks == expected

class TestMMapFile(BaseTestBufferingInputStreamTests):
    tfn = None
    fd = None
    Counter = 0

    def interpret(self, func, args, **kwargs):
        return func(*args)

    def teardown_method(self, method):
        tfn = self.tfn
        if tfn:
            self.tfn = None
            try:
                os.remove(tfn)
            except os.error, msg:
                print "can't remove %s: %s" % (tfn, msg)

    def makeStream(self, tell=None, seek=None, bufsize=-1, mode="r"):
        mmapmode = 0
        filemode = 0
        import mmap
        if "r" in mode:
            mmapmode = mmap.ACCESS_READ
            filemode = os.O_RDONLY
        if "w" in mode:
            mmapmode |= mmap.ACCESS_WRITE
            filemode |= os.O_WRONLY
        self.teardown_method(None) # for tests calling makeStream() several time
        self.tfn = str(udir.join('streamio%03d' % TestMMapFile.Counter))
        TestMMapFile.Counter += 1
        f = open(self.tfn, "wb")
        f.writelines(self.packets)
        f.close()
        self.fd = os.open(self.tfn, filemode)
        return streamio.MMapFile(self.fd, mmapmode)

    def test_write(self):
        if os.name == "posix":
            return # write() does't work on Unix :-(
        file = self.makeStream(mode="w")
        file.write("BooHoo\n")
        file.write("Barf\n")
        file.writelines(["a\n", "b\n", "c\n"])
        assert file.tell() == len("BooHoo\nBarf\na\nb\nc\n")
        file.seek(0)
        assert file.read() == "BooHoo\nBarf\na\nb\nc\n"
        file.seek(0)
        assert file.readlines() == (
                         ["BooHoo\n", "Barf\n", "a\n", "b\n", "c\n"])
        assert file.tell() == len("BooHoo\nBarf\na\nb\nc\n")


class BaseTestBufferingInputOutputStreamTests(BaseRtypingTest):

    def test_write(self):
        import sys
        base = TReaderWriter()
        filter = streamio.BufferingInputStream(
                streamio.BufferingOutputStream(base, 4), 4)
        def f():
            filter.write("123456789")
            for chunk in base.chunks:
                assert len(chunk[1]) >= 4
            s = filter.read(sys.maxint)
            assert base.buf == "123456789"
            base.chunks = []
            filter.write("abc")
            assert not base.chunks
            s = filter.read(sys.maxint)
            assert base.buf == "123456789abc"
            base.chunks = []
            filter.write("012")
            assert not base.chunks
            filter.seek(4, 0)
            assert base.buf == "123456789abc012"
            assert filter.read(3) == "567"
            filter.write('x')
            filter.flush()
            assert base.buf == "1234567x9abc012"
        self.interpret(f, [])

    def test_write_seek_beyond_end(self):
        "Linux behaviour. May be different on other platforms."
        base = TReaderWriter()
        filter = streamio.BufferingInputStream(
            streamio.BufferingOutputStream(base, 4), 4)
        def f():
            filter.seek(3)
            filter.write("y"*2)
            filter.close()
            assert base.buf == "\0"*3 + "y"*2
        self.interpret(f, [])

class TestBufferingInputOutputStreamTests(
        BaseTestBufferingInputOutputStreamTests):
    def interpret(self, func, args):
        return func(*args)

class TestBufferingInputOutputStreamTestsLLinterp(
        BaseTestBufferingInputOutputStreamTests, LLRtypeMixin):
    pass


class TestTextInputFilter:

    packets = [
        "foo\r",
        "bar\r",
        "\nfoo\r\n",
        "abc\ndef\rghi\r\nxyz",
        "\nuvw\npqr\r",
        "\n",
        "abc\n",
        ]
    expected = [
        ("foo\n", 4),
        ("bar\n", 9),
        ("foo\n", 14),
        ("abc\ndef\nghi\nxyz", 30),
        ("\nuvw\npqr\n", 40),
        ("abc\n", 44),
        ("", 44),
        ("", 44),
        ]

    expected_with_tell = [
        ("foo\n", 4),
        ("b", 5),
        ("ar\n", 9),
        ("foo\n", 14),
        ("abc\ndef\nghi\nxyz", 30),
        ("\nuvw\npqr\n", 40),
        ("abc\n", 44),
        ("", 44),
        ("", 44),
        ]

    expected_newlines = [
        (["abcd"], [None]),
        (["abcd\n"], ["\n"]),
        (["abcd\r\n"],["\r\n"]),
        (["abcd\r"],[None]), # wrong, but requires precognition to fix
        (["abcd\r", "\nefgh"], [None, "\r\n"]),
        (["abcd", "\nefg\r", "hij", "k\r\n"], [None, "\n", ("\r", "\n"),
                                               ("\r", "\n", "\r\n")]),
        (["abcd", "\refg\r", "\nhij", "k\n"], [None, "\r", ("\r", "\r\n"),
                                               ("\r", "\n", "\r\n")])
        ]

    def test_read(self):
        base = TReader(self.packets)
        filter = streamio.TextInputFilter(base)
        for data, pos in self.expected:
            assert filter.read(100) == data

    def test_read_tell(self):
        base = TReader(self.packets)
        filter = streamio.TextInputFilter(base)
        for data, pos in self.expected_with_tell:
            assert filter.read(100) == data
            assert filter.tell() == pos
            assert filter.tell() == pos # Repeat the tell() !

    def test_seek(self):
        base = TReader(self.packets)
        filter = streamio.TextInputFilter(base)
        sofar = ""
        pairs = []
        while True:
            pairs.append((sofar, filter.tell()))
            c = filter.read(1)
            if not c:
                break
            assert len(c) == 1
            sofar += c
        all = sofar
        for i in range(len(pairs)):
            sofar, pos = pairs[i]
            filter.seek(pos)
            assert filter.tell() == pos
            assert filter.tell() == pos
            bufs = [sofar]
            while True:
                data = filter.read(100)
                if not data:
                    assert filter.read(100) == ""
                    break
                bufs.append(data)
            assert "".join(bufs) == all
            
class TestTextOutputFilter: 

    def test_write_nl(self):
        base = TWriter()
        filter = streamio.TextOutputFilter(base, linesep="\n")
        filter.write("abc")
        filter.write("def\npqr\nuvw")
        filter.write("\n123\n")
        assert base.buf == "abcdef\npqr\nuvw\n123\n"

    def test_write_cr(self):
        base = TWriter()
        filter = streamio.TextOutputFilter(base, linesep="\r")
        filter.write("abc")
        filter.write("def\npqr\nuvw")
        filter.write("\n123\n")
        assert base.buf == "abcdef\rpqr\ruvw\r123\r"

    def test_write_crnl(self):
        base = TWriter()
        filter = streamio.TextOutputFilter(base, linesep="\r\n")
        filter.write("abc")
        filter.write("def\npqr\nuvw")
        filter.write("\n123\n")
        assert base.buf == "abcdef\r\npqr\r\nuvw\r\n123\r\n"

    def test_write_tell_nl(self):
        base = TWriter()
        filter = streamio.TextOutputFilter(base, linesep="\n")
        filter.write("xxx")
        assert filter.tell() == 3
        filter.write("\nabc\n")
        assert filter.tell() == 8

    def test_write_tell_cr(self):
        base = TWriter()
        filter = streamio.TextOutputFilter(base, linesep="\r")
        filter.write("xxx")
        assert filter.tell() == 3
        filter.write("\nabc\n")
        assert filter.tell() == 8

    def test_write_tell_crnl(self):
        base = TWriter()
        filter = streamio.TextOutputFilter(base, linesep="\r\n")
        filter.write("xxx")
        assert filter.tell() == 3
        filter.write("\nabc\n")
        assert filter.tell() == 10

    def test_write_seek(self):
        base = TWriter()
        filter = streamio.TextOutputFilter(base, linesep="\n")
        filter.write("x"*100)
        filter.seek(50)
        filter.write("y"*10)
        assert base.buf == "x"*50 + "y"*10 + "x"*40

class TestDecodingInputFilter:

    def test_read(self):
        chars = u"abc\xff\u1234\u4321\x80xyz"
        data = chars.encode("utf8")
        base = TReader([data])
        filter = streamio.DecodingInputFilter(base)
        bufs = []
        for n in range(1, 11):
            while 1:
                c = filter.read(n)
                assert type(c) == unicode
                if not c:
                    break
                bufs.append(c)
            assert u"".join(bufs) == chars

class TestEncodingOutputFilterTests: 

    def test_write(self):
        chars = u"abc\xff\u1234\u4321\x80xyz"
        data = chars.encode("utf8")
        for n in range(1, 11):
            base = TWriter()
            filter = streamio.EncodingOutputFilter(base)
            pos = 0
            while 1:
                c = chars[pos:pos+n]
                if not c:
                    break
                pos += len(c)
                filter.write(c)
            assert base.buf == data

class OldDisabledTests:
    def test_readlines(self):
        # This also tests next() and __iter__()
        file = self.makeStream()
        assert file.readlines() == self.lines

    
    def test_newlines_attribute(self):

        for packets, expected in self.expected_newlines:
            base = TReader(packets)
            filter = streamio.TextInputFilter(base)
            for e in expected:
                filter.read(100)
                assert filter.newlines == e



# Speed test

FN = "BIG"

def timeit(fn=FN, opener=streamio.MMapFile):
    f = opener(fn, "r")
    lines = bytes = 0
    t0 = time.clock()
    for line in iter(f.readline, ""):
        lines += 1
        bytes += len(line)
    t1 = time.clock()
    print "%d lines (%d bytes) in %.3f seconds for %s" % (
        lines, bytes, t1-t0, opener.__name__)

def speed_main():
    def diskopen(fn, mode):
        filemode = 0
        import mmap
        if "r" in mode:
            filemode = os.O_RDONLY
        if "w" in mode:
            filemode |= os.O_WRONLY
        
        fd = os.open(fn, filemode)
        base = streamio.DiskFile(fd)
        return streamio.BufferingInputStream(base)
    def mmapopen(fn, mode):
        mmapmode = 0
        filemode = 0
        import mmap
        if "r" in mode:
            mmapmode = mmap.ACCESS_READ
            filemode = os.O_RDONLY
        if "w" in mode:
            mmapmode |= mmap.ACCESS_WRITE
            filemode |= os.O_WRONLY
        fd = os.open(fn, filemode)
        return streamio.MMapFile(fd, mmapmode)
    timeit(opener=diskopen)
    timeit(opener=mmapopen)
    timeit(opener=open)

