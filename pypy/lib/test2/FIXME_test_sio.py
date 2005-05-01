"""Unit tests for sio (new standard I/O)."""

import support
import os
import time
from pypy.tool.udir import udir

sio = support.libmodule("_sio")


class TSource(object):

    def __init__(self, packets):
        for x in packets:
            assert x
        self.orig_packets = list(packets)
        self.packets = list(packets)
        self.pos = 0

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
            if not data:
                break
        assert self.pos == offset

    def read(self, n):
        try:
            data = self.packets.pop(0)
        except IndexError:
            return ""
        if len(data) > n:
            data, rest = data[:n], data[n:]
            self.packets.insert(0, rest)
        self.pos += len(data)
        return data

    def close(self):
        pass

class TReader(object):

    def __init__(self, packets):
        for x in packets:
            assert x
        self.orig_packets = list(packets)
        self.packets = list(packets)
        self.pos = 0

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
            if not data:
                break
        assert self.pos == offset

    def read(self, n):
        try:
            data = self.packets.pop(0)
        except IndexError:
            return ""
        if len(data) > n:
            data, rest = data[:n], data[n:]
            self.packets.insert(0, rest)
        self.pos += len(data)
        return data

    def close(self):
        pass

    def flush(self):
        pass

class TWriter(object):

    def __init__(self, data=''):
        self.buf = data
        self.pos = 0

    def write(self, data):
        if self.pos >= len(self.buf):
            self.buf += "\0" * (self.pos - len(self.buf)) + data
            self.pos = len(self.buf)
        else:
            self.buf = (self.buf[:self.pos] + data +
                        self.buf[self.pos + len(data):])
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
        if n < 1:
            result = self.buf[self.pos: ]
            self.pos = len(self.buf)
        else:
            if self.pos + n > len(self.buf):
                n = len(self.buf) - self.pos
            result = self.buf[self.pos: self.pos+n]
            self.pos += n
        return result
    
class TestBufferingInputStreamTests: 

    packets = ["a", "b", "\n", "def", "\nxy\npq\nuv", "wx"]
    lines = ["ab\n", "def\n", "xy\n", "pq\n", "uvwx"]

    def makeStream(self, tell=False, seek=False, bufsize=None):
        base = TSource(self.packets)
        if not tell:
            base.tell = None
        if not seek:
            base.seek = None
        return sio.BufferingInputStream(base, bufsize)

    def test_readline(self):
        file = self.makeStream()
        assert list(iter(file.readline, "")) == self.lines

    def test_readlines(self):
        # This also tests next() and __iter__()
        file = self.makeStream()
        assert file.readlines() == self.lines

    def test_readlines_small_bufsize(self):
        file = self.makeStream(bufsize=1)
        assert list(file) == self.lines

    def test_readall(self):
        file = self.makeStream()
        assert file.readall() == "".join(self.lines)

    def test_readall_small_bufsize(self):
        file = self.makeStream(bufsize=1)
        assert file.readall() == "".join(self.lines)

    def test_readall_after_readline(self):
        file = self.makeStream()
        assert file.readline() == self.lines[0]
        assert file.readline() == self.lines[1]
        assert file.readall() == "".join(self.lines[2:])

    def test_read_1_after_readline(self):
        file = self.makeStream()
        assert file.readline() == "ab\n"
        assert file.readline() == "def\n"
        blocks = []
        while 1:
            block = file.read(1)
            if not block:
                break
            blocks.append(block)
            assert file.read(0) == ""
        assert blocks == list("".join(self.lines)[7:])

    def test_read_1(self):
        file = self.makeStream()
        blocks = []
        while 1:
            block = file.read(1)
            if not block:
                break
            blocks.append(block)
            assert file.read(0) == ""
        assert blocks == list("".join(self.lines))

    def test_read_2(self):
        file = self.makeStream()
        blocks = []
        while 1:
            block = file.read(2)
            if not block:
                break
            blocks.append(block)
            assert file.read(0) == ""
        assert blocks == ["ab", "\nd", "ef", "\nx", "y\n", "pq",
                                  "\nu", "vw", "x"]

    def test_read_4(self):
        file = self.makeStream()
        blocks = []
        while 1:
            block = file.read(4)
            if not block:
                break
            blocks.append(block)
            assert file.read(0) == ""
        assert blocks == ["ab\nd", "ef\nx", "y\npq", "\nuvw", "x"]
        
    def test_read_4_after_readline(self):
        file = self.makeStream()
        assert file.readline() == "ab\n"
        assert file.readline() == "def\n"
        blocks = [file.read(4)]
        while 1:
            block = file.read(4)
            if not block:
                break
            blocks.append(block)
            assert file.read(0) == ""
        assert blocks == ["xy\np", "q\nuv", "wx"]

    def test_read_4_small_bufsize(self):
        file = self.makeStream(bufsize=1)
        blocks = []
        while 1:
            block = file.read(4)
            if not block:
                break
            blocks.append(block)
        assert blocks == ["ab\nd", "ef\nx", "y\npq", "\nuvw", "x"]

    def test_tell_1(self):
        file = self.makeStream(tell=True)
        pos = 0
        while 1:
            assert file.tell() == pos
            n = len(file.read(1))
            if not n:
                break
            pos += n

    def test_tell_1_after_readline(self):
        file = self.makeStream(tell=True)
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

    def test_tell_2(self):
        file = self.makeStream(tell=True)
        pos = 0
        while 1:
            assert file.tell() == pos
            n = len(file.read(2))
            if not n:
                break
            pos += n

    def test_tell_4(self):
        file = self.makeStream(tell=True)
        pos = 0
        while 1:
            assert file.tell() == pos
            n = len(file.read(4))
            if not n:
                break
            pos += n

    def test_tell_readline(self):
        file = self.makeStream(tell=True)
        pos = 0
        while 1:
            assert file.tell() == pos
            n = len(file.readline())
            if not n:
                break
            pos += n

    def test_seek(self):
        file = self.makeStream(tell=True, seek=True)
        all = file.readall()
        end = len(all)
        for readto in range(0, end+1):
            for seekto in range(0, end+1):
                for whence in 0, 1, 2:
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

    def test_seek_noseek(self):
        file = self.makeStream()
        all = file.readall()
        end = len(all)
        for readto in range(0, end+1):
            for seekto in range(readto, end+1):
                for whence in 1, 2:
                    file = self.makeStream()
                    head = file.read(readto)
                    assert head == all[:readto]
                    if whence == 1:
                        offset = seekto - readto
                    elif whence == 2:
                        offset = seekto - end
                    file.seek(offset, whence)
                    rest = file.readall()
                    assert rest == all[seekto:]

class TestBufferingOutputStream: 

    def test_write(self):
        base = TWriter()
        filter = sio.BufferingOutputStream(base, 4)
        filter.write("123")
        assert base.buf == ""
        assert filter.tell() == 3
        filter.write("456")
        assert base.buf == "1234"
        filter.write("789ABCDEF")
        assert base.buf == "123456789ABC"
        filter.write("0123")
        assert base.buf == "123456789ABCDEF0"
        assert filter.tell() == 19
        filter.close()
        assert base.buf == "123456789ABCDEF0123"

    def test_write_seek(self):
        base = TWriter()
        filter = sio.BufferingOutputStream(base, 4)
        filter.write("x"*6)
        filter.seek(3)
        filter.write("y"*2)
        filter.close()
        assert base.buf == "x"*3 + "y"*2 + "x"*1

    def test_write_seek_beyond_end(self):
        "Linux behaviour. May be different on other platforms."
        base = TWriter()
        filter = sio.BufferingOutputStream(base, 4)
        filter.seek(3)
        filter.write("y"*2)
        filter.close()
        assert base.buf == "\0"*3 + "y"*2

    def test_truncate(self):
        "Linux behaviour. May be different on other platforms."
        base = TWriter()
        filter = sio.BufferingOutputStream(base, 4)
        filter.write('x')
        filter.truncate(4)
        filter.write('y')
        filter.close()
        assert base.buf == 'xy' + '\0' * 2

    def test_truncate2(self):
        "Linux behaviour. May be different on other platforms."
        base = TWriter()
        filter = sio.BufferingOutputStream(base, 4)
        filter.write('12345678')
        filter.truncate(4)
        filter.write('y')
        filter.close()
        assert base.buf == '1234' + '\0' * 4 + 'y'

class TestLineBufferingOutputStreamTests: 

    def test_write(self):
        base = TWriter()
        filter = sio.LineBufferingOutputStream(base)
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

    def xtest_write_seek(self):
        base = TWriter()
        filter = sio.BufferingOutputStream(base, 4)
        filter.write("x"*6)
        filter.seek(3)
        filter.write("y"*2)
        filter.close()
        assert base.buf == "x"*3 + "y"*2 + "x"*1

class TestBufferingInputOutputStreamTests: 

    def test_write(self):
        base = TReaderWriter()
        filter = sio.BufferingInputOutputStream(base, 4)
        filter.write("123456789")
        assert base.buf == "12345678"
        s = filter.read()
        assert base.buf == "123456789"
        filter.write("01234")
        assert base.buf == "1234567890123"
        filter.seek(4,0)
        assert base.buf == "12345678901234"
        assert filter.read(3) == "567"
        filter.write('x')
        filter.flush()
        assert base.buf == "1234567x901234"
        
    def test_write_seek_beyond_end(self):
        "Linux behaviour. May be different on other platforms."
        base = TReaderWriter()
        filter = sio.BufferingInputOutputStream(base, 4)
        filter.seek(3)
        filter.write("y"*2)
        filter.close()
        assert base.buf == "\0"*3 + "y"*2

class TestCRLFFilter: 

    def test_filter(self):
        packets = ["abc\ndef\rghi\r\nxyz\r", "123\r", "\n456"]
        expected = ["abc\ndef\nghi\nxyz\n", "123\n", "456"]
        crlf = sio.CRLFFilter(TSource(packets))
        blocks = []
        while 1:
            block = crlf.read(100)
            if not block:
                break
            blocks.append(block)
        assert blocks == expected

class TestMMapFile(TestBufferingInputStreamTests): 
    tfn = None
    Counter = 0

    def teardown_method(self, method):
        tfn = self.tfn
        if tfn:
            self.tfn = None
            try:
                os.remove(tfn)
            except os.error, msg:
                print "can't remove %s: %s" % (tfn, msg)

    def makeStream(self, tell=None, seek=None, bufsize=None, mode="r"):
        self.teardown_method(None) # for tests calling makeStream() several time
        self.tfn = str(udir.join('sio%03d' % TestMMapFile.Counter))
        TestMMapFile.Counter += 1
        f = open(self.tfn, "wb")
        f.writelines(self.packets)
        f.close()
        return sio.MMapFile(self.tfn, mode)

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
        filter = sio.TextInputFilter(base)
        for data, pos in self.expected:
            assert filter.read(100) == data

    def test_read_tell(self):
        base = TReader(self.packets)
        filter = sio.TextInputFilter(base)
        for data, pos in self.expected_with_tell:
            assert filter.read(100) == data
            assert filter.tell() == pos
            assert filter.tell() == pos # Repeat the tell() !

    def test_seek(self):
        base = TReader(self.packets)
        filter = sio.TextInputFilter(base)
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
            
    def test_newlines_attribute(self):

        for packets, expected in self.expected_newlines:
            base = TReader(packets)
            filter = sio.TextInputFilter(base)
            for e in expected:
                filter.read(100)
                assert filter.newlines == e

class TestTextOutputFilter: 

    def test_write_nl(self):
        base = TWriter()
        filter = sio.TextOutputFilter(base, linesep="\n")
        filter.write("abc")
        filter.write("def\npqr\nuvw")
        filter.write("\n123\n")
        assert base.buf == "abcdef\npqr\nuvw\n123\n"

    def test_write_cr(self):
        base = TWriter()
        filter = sio.TextOutputFilter(base, linesep="\r")
        filter.write("abc")
        filter.write("def\npqr\nuvw")
        filter.write("\n123\n")
        assert base.buf == "abcdef\rpqr\ruvw\r123\r"

    def test_write_crnl(self):
        base = TWriter()
        filter = sio.TextOutputFilter(base, linesep="\r\n")
        filter.write("abc")
        filter.write("def\npqr\nuvw")
        filter.write("\n123\n")
        assert base.buf == "abcdef\r\npqr\r\nuvw\r\n123\r\n"

    def test_write_tell_nl(self):
        base = TWriter()
        filter = sio.TextOutputFilter(base, linesep="\n")
        filter.write("xxx")
        assert filter.tell() == 3
        filter.write("\nabc\n")
        assert filter.tell() == 8

    def test_write_tell_cr(self):
        base = TWriter()
        filter = sio.TextOutputFilter(base, linesep="\r")
        filter.write("xxx")
        assert filter.tell() == 3
        filter.write("\nabc\n")
        assert filter.tell() == 8

    def test_write_tell_crnl(self):
        base = TWriter()
        filter = sio.TextOutputFilter(base, linesep="\r\n")
        filter.write("xxx")
        assert filter.tell() == 3
        filter.write("\nabc\n")
        assert filter.tell() == 10

    def test_write_seek(self):
        base = TWriter()
        filter = sio.TextOutputFilter(base, linesep="\n")
        filter.write("x"*100)
        filter.seek(50)
        filter.write("y"*10)
        assert base.buf == "x"*50 + "y"*10 + "x"*40

class TestDecodingInputFilter:

    def test_read(self):
        chars = u"abc\xff\u1234\u4321\x80xyz"
        data = chars.encode("utf8")
        base = TReader([data])
        filter = sio.DecodingInputFilter(base)
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
            filter = sio.EncodingOutputFilter(base)
            pos = 0
            while 1:
                c = chars[pos:pos+n]
                if not c:
                    break
                pos += len(c)
                filter.write(c)
            assert base.buf == data

# Speed test

FN = "BIG"

def timeit(fn=FN, opener=sio.MMapFile):
    f = opener(fn, "r")
    lines = bytes = 0
    t0 = time.clock()
    for line in f:
        lines += 1
        bytes += len(line)
    t1 = time.clock()
    print "%d lines (%d bytes) in %.3f seconds for %s" % (
        lines, bytes, t1-t0, opener.__name__)

def speed_main():
    def diskopen(fn, mode):
        base = sio.DiskFile(fn, mode)
        return sio.BufferingInputStream(base)
    timeit(opener=diskopen)
    timeit(opener=sio.MMapFile)
    timeit(opener=open)

# Functional test

def functional_main():
    f = sio.DiskFile("sio.py")
    f = sio.DecodingInputFilter(f)
    f = sio.TextInputFilter(f)
    f = sio.BufferingInputStream(f)
    for i in range(10):
        print repr(f.readline())

