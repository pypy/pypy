# encoding: utf-8
from rpython.tool.udir import udir
import os


class AppTestFileIO:
    spaceconfig = dict(usemodules=['_io'] + (['fcntl'] if os.name != 'nt' else []))

    def setup_class(cls):
        tmpfile = udir.join('tmpfile')
        tmpfile.write("a\nb\nc", mode='wb')
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))
        cls.w_tmpdir = cls.space.wrap(str(udir))
        cls.w_posix = cls.space.appexec([], """():
            import %s as m;
            return m""" % os.name)

    def test_constructor(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'a')
        assert f.name.endswith('tmpfile')
        assert f.mode == 'ab'
        assert f.closefd is True
        f.close()

    def test_invalid_fd(self):
        import _io
        raises(ValueError, _io.FileIO, -10)
        raises(TypeError, _io.FileIO, 2 ** 31)
        raises(TypeError, _io.FileIO, -2 ** 31 - 1)

    def test_weakrefable(self):
        import _io
        from weakref import proxy
        f = _io.FileIO(self.tmpfile)
        p = proxy(f)
        assert p.mode == 'rb'
        f.close()

    def test_open_fd(self):
        import _io
        os = self.posix
        fd = os.open(self.tmpfile, os.O_RDONLY, 0o666)
        f = _io.FileIO(fd, "rb", closefd=False)
        assert f.fileno() == fd
        assert f.closefd is False
        f.close()
        os.close(fd)

    def test_open_directory(self):
        import _io
        import os
        raises(IOError, _io.FileIO, self.tmpdir, "rb")
        if os.name != 'nt':
            fd = os.open(self.tmpdir, os.O_RDONLY)
            raises(IOError, _io.FileIO, fd, "rb")
            os.close(fd)

    def test_open_non_existent_unicode(self):
        import _io
        import os
        path = os.path.join(self.tmpdir, '_pypy-日本')
        try:
            os.fsencode(path)
        except UnicodeEncodeError:
            import sys
            skip("can't run this test with %s as filesystem encoding" %
                 sys.getfilesystemencoding())
        exc = raises(IOError, _io.FileIO, path)
        expected = "[Errno 2] No such file or directory: %r" % path
        assert str(exc.value) == expected

    def test_readline(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        assert f.readline() == b'a\n'
        assert f.readline() == b'b\n'
        assert f.readline() == b'c'
        assert f.readline() == b''
        f.close()

    def test_readlines(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        assert f.readlines() == [b"a\n", b"b\n", b"c"]
        f.seek(0)
        assert f.readlines(3) == [b"a\n", b"b\n"]
        f.close()

    def test_readall(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        assert f.readall() == b"a\nb\nc"
        f.close()

    def test_write(self):
        import _io
        filename = self.tmpfile + '_w'
        f = _io.FileIO(filename, 'wb')
        f.write(b"test")
        # try without flushing
        f2 = _io.FileIO(filename, 'rb')
        assert f2.read() == b"test"
        f.close()
        f2.close()

    def test_writelines(self):
        import _io
        filename = self.tmpfile + '_w'
        f = _io.FileIO(filename, 'wb')
        f.writelines([b"line1\n", b"line2", b"line3"])
        f2 = _io.FileIO(filename, 'rb')
        assert f2.read() == b"line1\nline2line3"
        f.close()
        f2.close()

    def test_seek(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        f.seek(0)
        self.posix.close(f.fileno())
        raises(IOError, f.seek, 0)

    def test_tell(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        f.seek(3)
        assert f.tell() == 3
        f.close()

    def test_truncate(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'r+b')
        assert f.truncate(100) == 100 # grow the file
        f.close()
        f = _io.FileIO(self.tmpfile)
        assert len(f.read()) == 100
        f.close()
        #
        f = _io.FileIO(self.tmpfile, 'r+b')
        f.seek(50)
        assert f.truncate() == 50
        f.close()
        f = _io.FileIO(self.tmpfile)
        assert len(f.read()) == 50
        f.close()

    def test_readinto(self):
        import _io
        a = bytearray(b'x' * 10)
        f = _io.FileIO(self.tmpfile, 'r+')
        assert f.readinto(a) == 10
        f.seek(0)
        m = memoryview(bytearray(b"helloworld"))
        assert f.readinto(m) == 10
        exc = raises(TypeError, f.readinto, u"hello")
        assert str(exc.value) == "must be read-write buffer, not str"
        exc = raises(TypeError, f.readinto, memoryview(b"hello"))
        assert str(exc.value) == "must be read-write buffer, not memoryview"
        f.close()
        assert a == b'a\nb\nc\0\0\0\0\0'
        #
        a = bytearray(b'x' * 10)
        f = _io.FileIO(self.tmpfile, 'r+')
        f.truncate(3)
        assert f.readinto(a) == 3
        f.close()
        assert a == b'a\nbxxxxxxx'

    def test_nonblocking_read(self):
        try:
            import os, fcntl
        except ImportError:
            skip("need fcntl to set nonblocking mode")
        r_fd, w_fd = os.pipe()
        # set nonblocking
        fcntl.fcntl(r_fd, fcntl.F_SETFL, os.O_NONBLOCK)
        import _io
        f = _io.FileIO(r_fd, 'r')
        # Read from stream sould return None
        assert f.read() is None
        assert f.read(10) is None
        a = bytearray(b'x' * 10)
        assert f.readinto(a) is None

    def test_repr(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'r')
        assert repr(f) == ("<_io.FileIO name=%r mode='%s'>"
                           % (f.name, f.mode))
        del f.name
        assert repr(f) == ("<_io.FileIO fd=%r mode='%s'>"
                           % (f.fileno(), f.mode))
        f.close()
        assert repr(f) == "<_io.FileIO [closed]>"

    def test_unclosed_fd_on_exception(self):
        import _io
        import os
        class MyException(Exception): pass
        class MyFileIO(_io.FileIO):
            def __setattr__(self, name, value):
                if name == "name":
                    raise MyException("blocked setting name")
                return super(MyFileIO, self).__setattr__(name, value)
        fd = os.open(self.tmpfile, os.O_RDONLY)
        raises(MyException, MyFileIO, fd)
        os.close(fd)  # should not raise OSError(EBADF)

    def test_mode_strings(self):
        import _io
        import os
        for modes in [('w', 'wb'), ('wb', 'wb'), ('wb+', 'rb+'),
                      ('w+b', 'rb+'), ('a', 'ab'), ('ab', 'ab'),
                      ('ab+', 'ab+'), ('a+b', 'ab+'), ('r', 'rb'),
                      ('rb', 'rb'), ('rb+', 'rb+'), ('r+b', 'rb+')]:
            # read modes are last so that TESTFN will exist first
            with _io.FileIO(self.tmpfile, modes[0]) as f:
                assert f.mode == modes[1]

    def test_flush_error_on_close(self):
        # Test that the file is closed despite failed flush
        # and that flush() is called before file closed.
        import _io, os
        fd = os.open(self.tmpfile, os.O_RDONLY, 0o666)
        f = _io.FileIO(fd, 'r', closefd=False)
        closed = []
        def bad_flush():
            closed[:] = [f.closed]
            raise IOError()
        f.flush = bad_flush
        raises(IOError, f.close) # exception not swallowed
        assert f.closed
        assert closed         # flush() called
        assert not closed[0]  # flush() called before file closed
        os.close(fd)

    def test_open_exclusive(self):
        # XXX: should raise FileExistsError
        FileExistsError = OSError

        import _io
        filename = self.tmpfile + '_x1'
        raises(ValueError, _io.FileIO, filename, 'xw')
        with _io.FileIO(filename, 'x') as f:
            assert f.mode == 'xb'
        raises(FileExistsError, _io.FileIO, filename, 'x')

    def test_close_upon_reinit(self):
        import _io, posix
        f = _io.FileIO(self.tmpfile, 'r')
        fd1 = f.fileno()
        f.__init__(self.tmpfile, 'w')
        fd2 = f.fileno()
        if fd1 != fd2:
            raises(OSError, posix.close, fd1)


def test_flush_at_exit():
    from pypy import conftest
    from pypy.tool.option import make_config, make_objspace
    from rpython.tool.udir import udir

    tmpfile = udir.join('test_flush_at_exit')
    config = make_config(conftest.option)
    space = make_objspace(config)
    space.appexec([space.wrap(str(tmpfile))], """(tmpfile):
        import io
        f = io.open(tmpfile, 'w', encoding='ascii')
        f.write(u'42')
        # no flush() and no close()
        import sys; sys._keepalivesomewhereobscure = f
    """)
    space.finish()
    assert tmpfile.read() == '42'


def test_flush_at_exit_IOError_and_ValueError():
    from pypy import conftest
    from pypy.tool.option import make_config, make_objspace

    config = make_config(conftest.option)
    space = make_objspace(config)
    space.appexec([], """():
        import io
        class MyStream(io.IOBase):
            def flush(self):
                raise IOError

        class MyStream2(io.IOBase):
            def flush(self):
                raise ValueError

        s = MyStream()
        s2 = MyStream2()
        import sys; sys._keepalivesomewhereobscure = s
    """)
    space.finish() # the IOError has been ignored
