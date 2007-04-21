import os, random, sys
from pypy.tool.udir import udir
import py
from pypy.interpreter.mixedmodule import testmodule


SAMPLE = ''.join([chr(random.randrange(0, 256)) for i in range(12487)])
for extra in ['\r\r', '\r\n', '\n\r', '\n\n']:
    for i in range(20):
        j = random.randrange(0, len(SAMPLE)+1)
        SAMPLE = SAMPLE[:j] + extra + SAMPLE[j:]


def setup_module(mod):
    mod._file = testmodule("_file")
    udir.join('sample').write(SAMPLE)
    # workaround for testing _file on top of CPython
    if not hasattr(sys, 'pypy_objspaceclass'):
        sys.pypy__exithandlers__ = {}


class BaseROTests:
    sample = SAMPLE

    def expected_lines(self):
        lines = self.sample.split('\n')
        for i in range(len(lines)-1):
            lines[i] += '\n'
        return lines

    def test_simple_tell(self):
        assert self.file.tell() == 0

    def test_plain_read(self):
        data1 = self.file.read()
        assert data1 == self.sample

    def test_readline(self):
        lines = self.expected_lines()
        for sampleline in lines:
            inputline = self.file.readline()
            assert inputline == sampleline
        for i in range(5):
            inputline = self.file.readline()
            assert inputline == ""

    def test_readline_max(self):
        i = 0
        stop = 0
        while stop < 5:
            max = random.randrange(0, 100)
            sampleline = self.sample[i:i+max]
            nexteol = sampleline.find('\n')
            if nexteol >= 0:
                sampleline = sampleline[:nexteol+1]
            inputline = self.file.readline(max)
            assert inputline == sampleline
            i += len(sampleline)
            if i == len(self.sample):
                stop += 1

    def test_iter(self):
        inputlines = list(self.file)
        assert inputlines == self.expected_lines()

    def test_repr(self):
        r = repr(self.file)
        assert r.find('open file') >= 0
        assert r.find(self.file.name) >= 0
        assert r.find(self.file.mode) >= 0

    def test_isatty(self):
        assert not self.file.isatty()
        try:
            f = _file.file('/dev/tty')
        except IOError:
            pass
        else:
            assert f.isatty()
            f.close()

    def test_next(self):
        lines = self.expected_lines()
        for sampleline in lines:
            inputline = self.file.next()
            assert inputline == sampleline
        for i in range(5):
            py.test.raises(StopIteration, self.file.next)

    def test_read(self):
        i = 0
        stop = 0
        while stop < 5:
            max = random.randrange(0, 100)
            samplebuf = self.sample[i:i+max]
            inputbuf = self.file.read(max)
            assert inputbuf == samplebuf
            i += len(samplebuf)
            if i == len(self.sample):
                stop += 1

    def test_readlines(self):
        lines = self.file.readlines()
        assert lines == self.expected_lines()

    def test_readlines_max(self):
        i = 0
        stop = 0
        samplelines = self.expected_lines()
        while stop < 5:
            morelines = self.file.readlines(random.randrange(0, 300))
            for inputline in morelines:
                assert inputline == samplelines[0]
                samplelines.pop(0)
            if not samplelines:
                stop += 1

    def test_seek(self):
        for i in range(100):
            position = random.randrange(0, len(self.sample))
            self.file.seek(position)
            inputchar = self.file.read(1)
            assert inputchar == self.sample[position]
        for i in range(100):
            position = random.randrange(0, len(self.sample))
            self.file.seek(position - len(self.sample), 2)
            inputchar = self.file.read(1)
            assert inputchar == self.sample[position]
        prevpos = position + 1
        for i in range(100):
            position = random.randrange(0, len(self.sample))
            self.file.seek(position - prevpos, 1)
            inputchar = self.file.read(1)
            assert inputchar == self.sample[position]
            prevpos = position + 1

    def test_tell(self):
        for i in range(100):
            position = random.randrange(0, len(self.sample)+1)
            self.file.seek(position)
            told = self.file.tell()
            assert told == position
        for i in range(100):
            position = random.randrange(0, len(self.sample)+1)
            self.file.seek(position - len(self.sample), 2)
            told = self.file.tell()
            assert told == position
        prevpos = position
        for i in range(100):
            position = random.randrange(0, len(self.sample)+1)
            self.file.seek(position - prevpos, 1)
            told = self.file.tell()
            assert told == position
            prevpos = position

    def test_tell_and_seek_back(self):
        i = 0
        stop = 0
        secondpass = []
        while stop < 5:
            max = random.randrange(0, 100)
            samplebuf = self.sample[i:i+max]
            secondpass.append((self.file.tell(), i))
            inputbuf = self.file.read(max)
            assert inputbuf == samplebuf
            i += len(samplebuf)
            if i == len(self.sample):
                stop += 1
        for i in range(100):
            saved_position, i = random.choice(secondpass)
            max = random.randrange(0, 100)
            samplebuf = self.sample[i:i+max]
            self.file.seek(saved_position)
            inputbuf = self.file.read(max)
            assert inputbuf == samplebuf

    def test_xreadlines(self):
        assert self.file.xreadlines() is self.file

    def test_attr(self):
        f = self.file
        if self.expected_filename is not None:
            assert f.name == self.expected_filename
        if self.expected_mode is not None:
            assert f.mode == self.expected_mode
        assert f.closed == False
        assert not f.softspace
        py.test.raises((TypeError, AttributeError), 'f.name = 42')
        py.test.raises((TypeError, AttributeError), 'f.name = "stuff"')
        py.test.raises((TypeError, AttributeError), 'f.mode = "r"')
        py.test.raises((TypeError, AttributeError), 'f.closed = True')
        f.softspace = True
        assert f.softspace
        f.softspace = False
        assert not f.softspace
        f.close()
        assert f.closed == True

# ____________________________________________________________
#
#  Basic 'rb' mode

class TestFile(BaseROTests):
    expected_filename  = str(udir.join('sample'))
    expected_mode      = 'rb'
    extra_args = ()

    def setup_method(self, method):
        self.file = _file.file(self.expected_filename,
                               self.expected_mode,
                               *self.extra_args)

    def teardown_method(self, method):
        self.file.close()


class TestUnbufferedFile(TestFile):
    extra_args = (0,)


class TestLineBufferedFile(TestFile):
    extra_args = (1,)


class TestLargeBufferFile(TestFile):
    extra_args = (len(SAMPLE),)


# ____________________________________________________________
#
#  Check on top of CPython


class TestWithCPython(TestFile):
    def setup_method(self, method):
        self.file = open(self.expected_filename,
                         self.expected_mode,
                         *self.extra_args)


# ____________________________________________________________
#
#  Files built with fdopen()

class TestFdOpen(BaseROTests):
    expected_filename  = None
    expected_mode      = 'rb'
    extra_args = ()

    def setup_method(self, method):
        O_BINARY = getattr(os, "O_BINARY", 0)
        fd = os.open(TestFile.expected_filename, os.O_RDONLY | O_BINARY)
        self.file = _file.file.fdopen(fd,
                                      self.expected_mode,
                                      *self.extra_args)

    def teardown_method(self, method):
        self.file.close()


class TestUnbufferedFdOpen(TestFdOpen):
    extra_args = (0,)


class TestLineBufferedFdOpen(TestFdOpen):
    extra_args = (1,)


class TestLargeBufferFdOpen(TestFdOpen):
    extra_args = (len(SAMPLE),)


# ____________________________________________________________
#
#  Universal newlines

class TestUniversalNewlines(TestFile):
    expected_mode = 'rU'
    sample = '\n'.join(SAMPLE.splitlines(False))

    def test_seek(self):
        py.test.skip("does not apply in universal newlines mode")

    test_tell = test_seek


class TestUnbufferedUniversal(TestUniversalNewlines):
    extra_args = (0,)


class TestLineBufferedUniversal(TestUniversalNewlines):
    extra_args = (1,)


class TestLargeBufferUniversal(TestUniversalNewlines):
    extra_args = (len(SAMPLE),)


# ____________________________________________________________
#
#  A few extra tests

def test_case_readonly():
    fn = str(udir.join('temptestfile'))
    f = _file.file(fn, 'w')
    assert f.name == fn
    assert f.mode == 'w'
    assert f.closed == False
    assert f.encoding == None # Fix when we find out what this is
    py.test.raises((TypeError, AttributeError), setattr, f, 'name', 42)

def test_readlines():
    fn = str(udir.join('temptestfile'))
    lines = ['line%d\n' % i for i in range(1000)]
    f=_file.file(fn, 'w')
    f.writelines(lines)
    f.close()
    assert open(fn, 'r').readlines() == lines
    assert _file.file(fn, 'r').readlines() == lines
    somelines = _file.file(fn, 'r').readlines(2000)
    assert len(somelines) > 200
    assert somelines == lines[:len(somelines)]

def stresstest(flags, checkflags, eolstyles):
    fn = str(udir.join('temptestfile'))
    f = _file.file(fn, flags)
    expected = ''
    pos = 0
    for i in range(5000):
        x = random.random()
        if x < 0.4:
            l = int(x*100)
            buf = f.read(l)
            assert buf == expected[pos:pos+l]
            pos += len(buf)
        elif x < 0.75:
            writeeol, expecteol = random.choice(eolstyles)
            x = str(x)
            buf1 = x+writeeol
            buf2 = x+expecteol
            f.write(buf1)
            expected = expected[:pos] + buf2 + expected[pos+len(buf2):]
            pos += len(buf2)
        elif x < 0.80:
            pos = random.randint(0, len(expected))
            f.seek(pos)
        elif x < 0.85:
            pos = random.randint(0, len(expected))
            f.seek(pos - len(expected), 2)
        elif x < 0.90:
            currentpos = pos
            pos = random.randint(0, len(expected))
            f.seek(pos - currentpos, 1)
        elif x < 0.95:
            assert f.tell() == pos
        else:
            f.flush()
            g = open(fn, checkflags)
            buf = g.read()
            g.close()
            assert buf == expected
    f.close()
    g = open(fn, checkflags)
    buf = g.read()
    g.close()
    assert buf == expected

def test_rw_bin():
    stresstest('w+b', 'rb', [('', ''),     ('\n', '\n'),
                                  ('\r', '\r'), ('\r\n', '\r\n')])

def test_rw():
    fn = str(udir.join('temptestfile'))
    f = _file.file(fn, 'w+')
    f.write('hello\nworld\n')
    f.seek(0)
    assert f.read() == 'hello\nworld\n'
    f.close()

def test_r_universal():
    fn = str(udir.join('temptestfile'))
    f = open(fn, 'wb')
    f.write('hello\r\nworld\r\n')
    f.close()
    f = _file.file(fn, 'rU')
    assert f.read() == 'hello\nworld\n'
    f.close()

def test_flush():
    fn = str(udir.join('temptestfile'))
    f = _file.file(fn, 'w', 0)
    f.write('x')
    assert os.stat(fn).st_size == 1
    f.close()

    f = _file.file(fn, 'wb', 1)
    f.write('x')
    assert os.stat(fn).st_size == 0
    f.write('\n')
    assert os.stat(fn).st_size == 2
    f.write('x')
    assert os.stat(fn).st_size == 2
    f.flush()
    assert os.stat(fn).st_size == 3
    f.close()
    assert os.stat(fn).st_size == 3

    f = _file.file(fn, 'wb', 100)
    f.write('x')
    assert os.stat(fn).st_size == 0
    f.write('\n')
    assert os.stat(fn).st_size == 0
    f.write('x')
    assert os.stat(fn).st_size == 0
    f.flush()
    assert os.stat(fn).st_size == 3
    f.close()
    assert os.stat(fn).st_size == 3
