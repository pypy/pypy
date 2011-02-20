import os, random, sys
import pypy.tool.udir
import py
from pypy.conftest import gettestobjspace

udir = pypy.tool.udir.udir.ensure('test_file_extra', dir=1)


# XXX this file is a random test.  It may only fail occasionally
# depending on the details of the random string SAMPLE.

SAMPLE = ''.join([chr(random.randrange(0, 256)) for i in range(12487)])
for extra in ['\r\r', '\r\n', '\n\r', '\n\n']:
    for i in range(20):
        j = random.randrange(0, len(SAMPLE)+1)
        SAMPLE = SAMPLE[:j] + extra + SAMPLE[j:]
    if random.random() < 0.1:
        SAMPLE += extra    # occasionally, also test strings ending in an EOL


def setup_module(mod):
    udir.join('sample').write(SAMPLE, 'wb')


class BaseROTests:
    sample = SAMPLE

    def get_expected_lines(self):
        lines = self.sample.split('\n')
        for i in range(len(lines)-1):
            lines[i] += '\n'
        # if self.sample ends exactly in '\n', the split() gives a
        # spurious empty line at the end.  Fix it:
        if lines[-1] == '':
            del lines[-1]
        return lines

    def test_simple_tell(self):
        assert self.file.tell() == 0

    def test_plain_read(self):
        data1 = self.file.read()
        assert data1 == self.sample

    def test_readline(self):
        lines = self.expected_lines
        for sampleline in lines:
            inputline = self.file.readline()
            assert inputline == sampleline
        for i in range(5):
            inputline = self.file.readline()
            assert inputline == ""

    def test_readline_max(self):
        import random
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
        assert inputlines == self.expected_lines

    def test_isatty(self):
        assert not self.file.isatty()

    def test_next(self):
        lines = self.expected_lines
        for sampleline in lines:
            inputline = self.file.next()
            assert inputline == sampleline
        for i in range(5):
            raises(StopIteration, self.file.next)

    def test_read(self):
        import random
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
        assert lines == self.expected_lines

    def test_readlines_max(self):
        import random
        i = 0
        stop = 0
        samplelines = self.expected_lines
        while stop < 5:
            morelines = self.file.readlines(random.randrange(1, 300))
            for inputline in morelines:
                assert inputline == samplelines[0]
                samplelines.pop(0)
            if not samplelines:
                stop += 1
            else:
                assert len(morelines) >= 1    # otherwise, this test (and
                                              # real programs) would be prone
                                              # to endless loops

    def test_seek(self):
        import random
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
        import random
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
        import random
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
        raises((TypeError, AttributeError), 'f.name = 42')
        raises((TypeError, AttributeError), 'f.name = "stuff"')
        raises((TypeError, AttributeError), 'f.mode = "r"')
        raises((TypeError, AttributeError), 'f.closed = True')
        f.softspace = True
        assert f.softspace
        f.softspace = False
        assert not f.softspace
        f.close()
        assert f.closed == True

    def test_repr(self):
        assert repr(self.file).startswith(
            "<open file '%s', mode '%s' at 0x" % (
                self.expected_filename, self.expected_mode))
        self.file.close()
        assert repr(self.file).startswith(
            "<closed file '%s', mode '%s' at 0x" % (
                self.expected_filename, self.expected_mode))
        
# ____________________________________________________________
#
#  Basic 'rb' mode

class AppTestFile(BaseROTests):
    expected_filename  = str(udir.join('sample'))
    expected_mode      = 'rb'
    extra_args = ()

    def setup_method(self, method):
        space = self.space
        if hasattr(space, 'gettypeobject'):
            from pypy.module._file.interp_file import W_File
            w_filetype = space.gettypeobject(W_File.typedef)
        else:
            w_filetype = file    # TinyObjSpace, for "py.test -A"
        self.w_file = space.call_function(
            w_filetype,
            space.wrap(self.expected_filename),
            space.wrap(self.expected_mode),
            *[space.wrap(a) for a in self.extra_args])
        self.w_sample = space.wrap(self.sample)
        self.w_expected_filename = space.wrap(self.expected_filename)
        self.w_expected_mode = space.wrap(self.expected_mode)
        self.w_expected_lines = space.wrap(self.get_expected_lines())

    def teardown_method(self, method):
        self.space.call_method(self.w_file, 'close')


class AppTestUnbufferedFile(AppTestFile):
    extra_args = (0,)


class AppTestLineBufferedFile(AppTestFile):
    extra_args = (1,)


class AppTestLargeBufferFile(AppTestFile):
    extra_args = (len(SAMPLE),)


# ____________________________________________________________
#
#  Check on top of CPython


class TestWithCPython(BaseROTests):
    expected_filename = str(udir.join('sample'))
    expected_mode     = 'rb'

    def setup_method(self, method):
        self.file = open(self.expected_filename, self.expected_mode)
        self.expected_lines = self.get_expected_lines()

    def teardown_method(self, method):
        self.file.close()

# ____________________________________________________________
#
#  Files built with fdopen()

class AppTestFdOpen(BaseROTests):
    expected_filename  = '<fdopen>'
    expected_mode      = 'rb'
    extra_args = ()

    def setup_method(self, method):
        space = self.space
        O_BINARY = getattr(os, "O_BINARY", 0)
        if hasattr(space, 'gettypeobject'):
            from pypy.module._file.interp_file import W_File
            w_filetype = space.gettypeobject(W_File.typedef)
        else:
            w_filetype = os    # TinyObjSpace, for "py.test -A"
                               # (CPython has no file.fdopen, only os.fdopen)
        fd = os.open(AppTestFile.expected_filename, os.O_RDONLY | O_BINARY)
        self.w_file = space.call_method(
            w_filetype,
            'fdopen',
            space.wrap(fd),
            space.wrap(self.expected_mode),
            *[space.wrap(a) for a in self.extra_args])
        self.w_fd = space.wrap(fd)
        self.w_sample = space.wrap(self.sample)
        self.w_expected_filename = space.wrap(self.expected_filename)
        self.w_expected_mode = space.wrap(self.expected_mode)
        self.w_expected_lines = space.wrap(self.get_expected_lines())

    def teardown_method(self, method):
        self.space.call_method(self.w_file, 'close')

    def test_fileno(self):
        assert self.file.fileno() == self.fd


class AppTestUnbufferedFdOpen(AppTestFdOpen):
    extra_args = (0,)


class AppTestLineBufferedFdOpen(AppTestFdOpen):
    extra_args = (1,)


class AppTestLargeBufferFdOpen(AppTestFdOpen):
    extra_args = (len(SAMPLE),)


# ____________________________________________________________
#
#  Universal newlines

class AppTestUniversalNewlines(AppTestFile):
    expected_mode = 'rU'
    sample = '\n'.join((SAMPLE+'X').splitlines(False))[:-1]
    # ^^^ if SAMPLE ends in any end-of-line character combination, read()ing
    # it in 'rU' mode gives a final '\n', but splitlines(False) doesn't give
    # a final empty line.  Adding and removing an extra 'X' avoids this
    # corner case.

    def test_seek(self):
        skip("does not apply in universal newlines mode")

    test_tell = test_seek


class AppTestUnbufferedUniversal(AppTestUniversalNewlines):
    extra_args = (0,)


class AppTestLineBufferedUniversal(AppTestUniversalNewlines):
    extra_args = (1,)


class AppTestLargeBufferUniversal(AppTestUniversalNewlines):
    extra_args = (len(SAMPLE),)


# ____________________________________________________________
#
#  A few extra tests

class AppTestAFewExtra:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('array',))
        cls.space = space

    def setup_method(self, method):
        fn = str(udir.join('temptestfile'))
        self.w_temptestfile = self.space.wrap(fn)

    def test_case_readonly(self):
        fn = self.temptestfile
        f = file(fn, 'w')
        assert f.name == fn
        assert f.mode == 'w'
        assert f.closed == False
        assert f.encoding == None # Fix when we find out what this is
        raises((TypeError, AttributeError), setattr, f, 'name', 42)

    def test_readlines(self):
        fn = self.temptestfile
        lines = ['line%d\n' % i for i in range(1000)]
        f = file(fn, 'w')
        f.writelines(lines)
        f.close()
        assert open(fn, 'r').readlines() == lines
        assert file(fn, 'r').readlines() == lines
        somelines = file(fn, 'r').readlines(2000)
        assert len(somelines) > 200
        assert somelines == lines[:len(somelines)]

    def test_nasty_writelines(self):
        # The stream lock should be released between writes
        fn = self.temptestfile
        f = file(fn, 'w')
        def nasty():
            for i in range(5):
                if i == 3:
                    # should not raise because of acquired lock
                    f.close()
                yield str(i)
        exc = raises(ValueError, f.writelines, nasty())
        assert exc.value.message == "I/O operation on closed file"
        f.close()

    def test_rw_bin(self):
        import random
        flags = 'w+b'
        checkflags = 'rb'
        eolstyles = [('', ''),     ('\n', '\n'),
                     ('\r', '\r'), ('\r\n', '\r\n')]
        fn = self.temptestfile
        f = file(fn, flags)
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

    def test_rw(self):
        fn = self.temptestfile
        f = file(fn, 'w+')
        f.write('hello\nworld\n')
        f.seek(0)
        assert f.read() == 'hello\nworld\n'
        f.close()

    def test_r_universal(self):
        fn = self.temptestfile
        f = open(fn, 'wb')
        f.write('hello\r\nworld\r\n')
        f.close()
        f = file(fn, 'rU')
        assert f.read() == 'hello\nworld\n'
        f.close()

    def test_flush(self):
        import os
        fn = self.temptestfile
        f = file(fn, 'w', 0)
        f.write('x')
        assert os.stat(fn).st_size == 1
        f.close()

        f = file(fn, 'wb', 1)
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

        f = file(fn, 'wb', 1000)
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

    def test_isatty(self):
        try:
            f = file('/dev/tty')
        except IOError:
            pass
        else:
            assert f.isatty()
            f.close()

    def test_truncate(self):
        fn = self.temptestfile
        f = open(fn, 'w+b')
        f.write('hello world')
        f.seek(7)
        f.truncate()
        f.seek(0)
        data = f.read()
        assert data == 'hello w'
        f.seek(0, 2)
        assert f.tell() == 7
        f.seek(0)
        f.truncate(3)
        data = f.read(123)
        assert data == 'hel'
        f.close()

        import errno, sys
        f = open(fn)
        exc = raises(EnvironmentError, f.truncate, 3)
        if sys.platform == 'win32':
            assert exc.value.winerror == 5 # ERROR_ACCESS_DENIED
        else:
            # CPython explicitely checks the file mode
            # PyPy relies on the libc to raise the error
            assert (exc.value.message == "File not open for writing" or
                    exc.value.errno == errno.EINVAL)
        f.close()

    def test_readinto(self):
        from array import array
        a = array('c')
        a.fromstring('0123456789')
        fn = self.temptestfile
        f = open(fn, 'w+b')
        f.write('foobar')
        f.seek(0)
        n = f.readinto(a)
        f.close()
        assert n == 6
        assert len(a) == 10
        assert a.tostring() == 'foobar6789'

    def test_weakref(self):
        """Files are weakrefable."""
        import weakref
        fn = self.temptestfile
        f = open(fn, 'wb')
        ref = weakref.ref(f)
        ref().write('hello')
        assert f.tell() == 5
        f.close()

    def test_weakref_dies_before_file_closes(self):
        # Hard-to-reproduce failure (which should now be fixed).
        # I think that this is how lib-python/modified-2.5.2/test_file.py
        # sometimes failed on a Boehm pypy-c.
        import weakref, gc
        fn = self.temptestfile
        f = open(fn, 'wb')
        f.close()
        f = open(fn, 'rb')
        ref = weakref.ref(f)
        attempts = range(10)
        del f
        for i in attempts:
            f1 = ref()
            if f1 is None:
                break     # all gone
            assert not f1.closed   # if still reachable, should be still open
            del f1
            gc.collect()

    def test_ValueError(self):
        fn = self.temptestfile
        f = open(fn, 'wb')
        f.close()
        raises(ValueError, f.fileno)
        raises(ValueError, f.flush)
        raises(ValueError, f.isatty)
        raises(ValueError, f.next)
        raises(ValueError, f.read)
        raises(ValueError, f.readline)
        raises(ValueError, f.readlines)
        raises(ValueError, f.seek, 0)
        raises(ValueError, f.tell)
        raises(ValueError, f.truncate)
        raises(ValueError, f.write, "")
        raises(ValueError, f.writelines, [])
        raises(ValueError, iter, f)
        raises(ValueError, f.xreadlines)
        raises(ValueError, f.__enter__)
        f.close()     # accepted as a no-op

    def test_docstrings(self):
        assert file.closed.__doc__ == 'True if the file is closed'

    def test_repr_unicode_filename(self):
        f = open(unicode(self.temptestfile), 'w')
        assert repr(f).startswith("<open file " + 
                                  repr(unicode(self.temptestfile)))
        f.close()

