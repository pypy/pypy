from __future__ import with_statement
import pytest, os, errno
from pypy.interpreter.gateway import interp2app, unwrap_spec

def getfile(space):
    return space.appexec([], """():
        try:
            import _file
            return _file.file
        except ImportError:     # when running with py.test -A
            return file
    """)

# the following function is used e.g. in test_resource_warning
@unwrap_spec(regex=str, s=str)
def regex_search(space, regex, s):
    import re
    import textwrap
    regex = textwrap.dedent(regex).strip()
    m = re.search(regex, s)
    m = bool(m)
    return space.wrap(m)

class AppTestFile(object):
    spaceconfig = dict(usemodules=("_file",))

    def setup_class(cls):
        cls.w_temppath = cls.space.wrap(
            str(pytest.ensuretemp("fileimpl").join("foo.txt")))
        cls.w_file = getfile(cls.space)
        cls.w_regex_search = cls.space.wrap(interp2app(regex_search))

    def test_simple(self):
        f = self.file(self.temppath, "w")
        f.write("foo")
        f.close()
        f = self.file(self.temppath, "r")
        raises(TypeError, f.read, None)
        try:
            s = f.read()
            assert s == "foo"
        finally:
            f.close()

    def test_readline(self):
        f = self.file(self.temppath, "w")
        try:
            f.write("foo\nbar\n")
        finally:
            f.close()
        f = self.file(self.temppath, "r")
        raises(TypeError, f.readline, None)
        try:
            s = f.readline()
            assert s == "foo\n"
            s = f.readline()
            assert s == "bar\n"
        finally:
            f.close()

    def test_readlines(self):
        f = self.file(self.temppath, "w")
        try:
            f.write("foo\nbar\n")
        finally:
            f.close()
        f = self.file(self.temppath, "r")
        raises(TypeError, f.readlines, None)
        try:
            s = f.readlines()
            assert s == ["foo\n", "bar\n"]
        finally:
            f.close()

    def test_fdopen(self):
        import os
        f = self.file(self.temppath, "w")
        try:
            f.write("foo\nbaz\n")
        finally:
            f.close()
        try:
            fdopen = self.file.fdopen
        except AttributeError:
            fdopen = os.fdopen      # when running with -A
        fd = os.open(self.temppath, os.O_WRONLY | os.O_CREAT)
        f2 = fdopen(fd, "a")
        f2.seek(0, 2)
        f2.write("bar\nboo")
        f2.close()
        # don't close fd, will get a whining __del__
        f = self.file(self.temppath, "r")
        try:
            s = f.read()
            assert s == "foo\nbaz\nbar\nboo"
        finally:
            f.close()

    def test_badmode(self):
        raises(ValueError, self.file, "foo", "bar")

    def test_wraposerror(self):
        raises(IOError, self.file, "hopefully/not/existant.bar")

    def test_correct_file_mode(self):
        import os
        f = self.file(self.temppath, "w")
        umask = os.umask(0)
        os.umask(umask)
        try:
            f.write("foo")
        finally:
            f.close()
        assert oct(os.stat(self.temppath).st_mode & 0777) == oct(0666 & ~umask)

    def test_newlines(self):
        import os
        f = self.file(self.temppath, "wb")
        f.write("\r\n")
        assert f.newlines is None
        f.close()
        assert f.newlines is None
        f = self.file(self.temppath, "rU")
        res = f.read()
        assert res == "\n"
        assert f.newlines == "\r\n"
        f.close()
        assert f.newlines == "\r\n"

        # now use readline()
        f = self.file(self.temppath, "rU")
        res = f.readline()
        assert res == "\n"
        # this tell() is necessary for CPython as well to update f.newlines
        f.tell()
        assert f.newlines == "\r\n"
        res = f.readline()
        assert res == ""
        assert f.newlines == "\r\n"
        f.close()

    def test_unicode(self):
        import os
        f = self.file(self.temppath, "w")
        f.write(u"hello\n")
        raises(UnicodeEncodeError, f.write, u'\xe9')
        f.close()
        f = self.file(self.temppath, "r")
        res = f.read()
        assert res == "hello\n"
        assert type(res) is str
        f.close()

    def test_unicode_filename(self):
        import sys
        try:
            u'\xe9'.encode(sys.getfilesystemencoding())
        except UnicodeEncodeError:
            skip("encoding not good enough")
        f = self.file(self.temppath + u'\xe9', "w")
        f.close()

    def test_oserror_has_filename(self):
        try:
            f = self.file("file that is clearly not there")
        except IOError as e:
            assert e.filename == 'file that is clearly not there'
        else:
            raise Exception("did not raise")

    def test_readline_mixed_with_read(self):
        s = '''From MAILER-DAEMON Wed Jan 14 14:42:30 2009
From: foo

0
From MAILER-DAEMON Wed Jan 14 14:42:44 2009
Return-Path: <gkj@gregorykjohnson.com>
X-Original-To: gkj+person@localhost
Delivered-To: gkj+person@localhost
Received: from localhost (localhost [127.0.0.1])
        by andy.gregorykjohnson.com (Postfix) with ESMTP id 356ED9DD17
        for <gkj+person@localhost>; Wed, 13 Jul 2005 17:23:16 -0400 (EDT)
Delivered-To: gkj@sundance.gregorykjohnson.com'''
        f = self.file(self.temppath, "w")
        f.write(s)
        f.close()
        f = self.file(self.temppath, "r")
        f.seek(0L)
        f.readline()
        pos = f.tell()
        assert f.read(12L) == 'From: foo\n\n0'
        f.seek(pos)
        assert f.read(12L) == 'From: foo\n\n0'
        f.close()

    def test_invalid_modes(self):
        raises(ValueError, self.file, self.temppath, "aU")
        raises(ValueError, self.file, self.temppath, "wU+")
        raises(ValueError, self.file, self.temppath, "")

    def test_write_resets_softspace(self):
        f = self.file(self.temppath, "w")
        print >> f, '.',
        f.write(',')
        print >> f, '.',
        f.close()
        f = self.file(self.temppath, "r")
        res = f.read()
        assert res == ".,."
        f.close()

    def test_open_dir(self):
        import os

        exc = raises(IOError, self.file, os.curdir)
        assert exc.value.filename == os.curdir
        exc = raises(IOError, self.file, os.curdir, 'w')
        assert exc.value.filename == os.curdir

    def test_encoding_errors(self):
        import sys
        if '__pypy__' not in sys.builtin_module_names:
            pytest.skip("pypy only test")
        import _file

        with self.file(self.temppath, "w") as f:
            _file.set_file_encoding(f, "utf-8")
            f.write(u'15\u20ac')

            assert f.encoding == "utf-8"
            assert f.errors is None

        with self.file(self.temppath, "r") as f:
            data = f.read()
            assert data == '15\xe2\x82\xac'

        with self.file(self.temppath, "w") as f:
            _file.set_file_encoding(f, "iso-8859-1", "ignore")
            f.write(u'15\u20ac')

            assert f.encoding == "iso-8859-1"
            assert f.errors == "ignore"

        with self.file(self.temppath, "r") as f:
            data = f.read()
            assert data == "15"

    def test_exception_from_close(self):
        import os
        f = self.file(self.temppath, 'w')
        os.close(f.fileno())
        raises(IOError, f.close)    # bad file descriptor

    def test_exception_from_del(self):
        import os, gc, sys, cStringIO
        f = self.file(self.temppath, 'w')
        g = cStringIO.StringIO()
        preverr = sys.stderr
        try:
            sys.stderr = g
            os.close(f.fileno())
            del f
            gc.collect()     # bad file descriptor in f.__del__()
        finally:
            sys.stderr = preverr
        import errno
        assert os.strerror(errno.EBADF) in g.getvalue()
        # the following is a "nice to have" feature that CPython doesn't have
        if '__pypy__' in sys.builtin_module_names:
            assert repr(self.temppath) in g.getvalue()

    @pytest.mark.skipif("config.option.runappdirect")
    def test_track_resources(self):
        import os, gc, sys, cStringIO
        if '__pypy__' not in sys.builtin_module_names:
            skip("pypy specific test")
        def fn(flag1, flag2, do_close=False):
            sys.pypy_set_track_resources(flag1)
            f = self.file(self.temppath, 'w')
            sys.pypy_set_track_resources(flag2)
            buf = cStringIO.StringIO()
            preverr = sys.stderr
            try:
                sys.stderr = buf
                if do_close:
                    f.close()
                del f
                gc.collect() # force __del__ to be called
            finally:
                sys.stderr = preverr
                sys.pypy_set_track_resources(False)
            return buf.getvalue()

        # check with track_resources disabled
        assert fn(False, False) == ""
        #
        # check that we don't get the warning if we actually close the file
        assert fn(False, False, do_close=True) == ""
        #
        # check with track_resources enabled
        msg = fn(True, True)
        assert self.regex_search(r"""
        WARNING: unclosed file: <open file .*>
        Created at \(most recent call last\):
          File ".*", line .*, in test_track_resources
          File ".*", line .*, in fn
        """, msg)
        #
        # check with track_resources enabled in the destructor BUT with a
        # file which was created when track_resources was disabled
        msg = fn(False, True)
        assert self.regex_search("WARNING: unclosed file: <open file .*>", msg)
        assert "Created at" not in msg

    @pytest.mark.skipif("config.option.runappdirect")
    def test_track_resources_dont_crash(self):
        import os, gc, sys, cStringIO
        if '__pypy__' not in sys.builtin_module_names:
            skip("pypy specific test")
        #
        # try hard to create a code object whose co_filename points to an
        # EXISTING file, so that traceback.py tries to open it when formatting
        # the stacktrace
        f = open(self.temppath, 'w')
        f.close()
        co = compile('open(r"%s")' % self.temppath, self.temppath, 'exec')
        sys.pypy_set_track_resources(True)
        try:
            # this exec used to fail, because space.format_traceback tried to
            # recurively open a file, causing an infinite recursion. For the
            # purpose of this test, it is enough that it actually finishes
            # without errors
            exec co
        finally:
            sys.pypy_set_track_resources(False)

    def test_truncate(self):
        f = self.file(self.temppath, "w")
        f.write("foo")
        f.close()
        with self.file(self.temppath, 'r') as f:
            raises(IOError, f.truncate, 100)

    def test_write_full(self):
        try:
            f = self.file('/dev/full', 'w', 1)
        except IOError:
            skip("requires '/dev/full'")
        try:
            f.write('hello')
            raises(IOError, f.write, '\n')
            f.write('zzz')
            raises(IOError, f.flush)
            f.flush()
        finally:
            f.close()

    def test_ignore_ioerror_in_readall_if_nonempty_result(self):
        # this is the behavior of regular files in CPython 2.7, as
        # well as of _io.FileIO at least in CPython 3.3.  This is
        # *not* the behavior of _io.FileIO in CPython 3.4 or 3.5;
        # see CPython's issue #21090.
        import sys
        try:
            from posix import openpty, fdopen, write, close
        except ImportError:
            skip('no openpty on this platform')
        if 'gnukfreebsd' in sys.platform:
            skip('close() hangs forever on kFreeBSD')
        read_fd, write_fd = openpty()
        write(write_fd, 'Abc\n')
        close(write_fd)
        f = fdopen(read_fd)
        # behavior on Linux: f.read() returns 'Abc\r\n', then the next time
        # it raises IOError.  Behavior on OS/X (Python 2.7.5): the close()
        # above threw away the buffer, and f.read() always returns ''.
        if sys.platform.startswith('linux'):
            s = f.read()
            assert s == 'Abc\r\n'
            raises(IOError, f.read)
        else:
            s = f.read()
            assert s == ''
            s = f.read()
            assert s == ''
        f.close()


class AppTestNonblocking(object):
    def setup_class(cls):
        from pypy.module._file.interp_file import W_File

        cls.old_read = os.read

        if cls.runappdirect:
            pytest.skip("works with internals of _file impl on py.py")
        def read(fd, n=None):
            if fd != 424242:
                return cls.old_read(fd, n)
            if cls.state == 0:
                cls.state += 1
                return "xyz"
            if cls.state < 3:
                cls.state += 1
                raise OSError(errno.EAGAIN, "xyz")
            return ''
        os.read = read
        stdin = W_File(cls.space)
        stdin.file_fdopen(424242, 'rb', 1)
        stdin.name = '<stdin>'
        cls.w_stream = stdin

    def setup_method(self, meth):
        self.__class__.state = 0

    def teardown_class(cls):
        os.read = cls.old_read

    def test_nonblocking_file_all(self):
        res = self.stream.read()
        assert res == 'xyz'

    def test_nonblocking_file_max(self):
        res = self.stream.read(100)
        assert res == 'xyz'

class AppTestConcurrency(object):
    # these tests only really make sense on top of a translated pypy-c,
    # because on top of py.py the inner calls to os.write() don't
    # release our object space's GIL.
    spaceconfig = dict(usemodules=("_file",))

    def setup_class(cls):
        if not cls.runappdirect:
            pytest.skip("likely to deadlock when interpreted by py.py")
        cls.w_temppath = cls.space.wrap(
            str(pytest.ensuretemp("fileimpl").join("concurrency.txt")))
        cls.w_file = getfile(cls.space)

    def test_concurrent_writes(self):
        # check that f.write() is atomic
        import thread, time
        f = self.file(self.temppath, "w+b")
        def writer(i):
            for j in range(150):
                f.write('%3d %3d\n' % (i, j))
            locks[i].release()
        locks = []
        for i in range(10):
            lock = thread.allocate_lock()
            lock.acquire()
            locks.append(lock)
        for i in range(10):
            thread.start_new_thread(writer, (i,))
        # wait until all threads are done
        for i in range(10):
            locks[i].acquire()
        f.seek(0)
        lines = f.readlines()
        lines.sort()
        assert lines == ['%3d %3d\n' % (i, j) for i in range(10)
                                              for j in range(150)]
        f.close()

    def test_parallel_writes_and_reads(self):
        # Warning: a test like the one below deadlocks CPython
        # http://bugs.python.org/issue1164
        # It also deadlocks on py.py because the space GIL is not
        # released.
        import thread, sys, os
        try:
            fdopen = self.file.fdopen
        except AttributeError:
            # when running with -A
            skip("deadlocks on top of CPython")
        read_fd, write_fd = os.pipe()
        fread = fdopen(read_fd, 'rb', 200)
        fwrite = fdopen(write_fd, 'wb', 200)
        run = True
        readers_done = [0]

        def writer():
            f = 0.1
            while run:
                print >> fwrite, f,
                f = 4*f - 3*f*f
            print >> fwrite, "X"
            fwrite.flush()
            sys.stdout.write('writer ends\n')

        def reader(j):
            while True:
                data = fread.read(1)
                #sys.stdout.write('%d%r ' % (j, data))
                if data == "X":
                    break
            sys.stdout.write('reader ends\n')
            readers_done[0] += 1

        for j in range(3):
            thread.start_new_thread(reader, (j,))
            thread.start_new_thread(writer, ())

        import time
        t = time.time() + 5
        print "start of test"
        while time.time() < t:
            time.sleep(1)
        print "end of test"

        assert readers_done[0] == 0
        run = False    # end the writers
        for i in range(600):
            time.sleep(0.4)
            sys.stdout.flush()
            x = readers_done[0]
            if x == 3:
                break
            print 'readers_done == %d, still waiting...' % (x,)
        else:
            raise Exception("time out")
        print 'Passed.'

    def test_seek_from_cur_backwards_off_end(self):
        import os

        f = self.file(self.temppath, "w+b")
        f.write('123456789x12345678><123456789\n')

        f.seek(0, os.SEEK_END)
        f.seek(-25, os.SEEK_CUR)
        f.read(25)
        f.seek(-25, os.SEEK_CUR)
        try:
            f.seek(-25, os.SEEK_CUR)
        except IOError:
            pass
        else:
            raise AssertionError("Didn't raise IOError")
        assert f.tell() == 5


class AppTestFile25:
    spaceconfig = dict(usemodules=("_file",))

    def setup_class(cls):
        cls.w_temppath = cls.space.wrap(
            str(pytest.ensuretemp("fileimpl").join("foo.txt")))
        cls.w_file = getfile(cls.space)

    def test___enter__(self):
        f = self.file(self.temppath, 'w')
        assert f.__enter__() is f

    def test___exit__(self):
        f = self.file(self.temppath, 'w')
        assert f.__exit__() is None
        assert f.closed

    def test_file_and_with_statement(self):
        with self.file(self.temppath, 'w') as f:
            f.write('foo')
        assert f.closed

        with self.file(self.temppath, 'r') as f:
            s = f.readline()

        assert s == "foo"
        assert f.closed

    def test_subclass_with(self):
        file = self.file
        class C(file):
            def __init__(self, *args, **kwargs):
                self.subclass_closed = False
                file.__init__(self, *args, **kwargs)

            def close(self):
                self.subclass_closed = True
                file.close(self)

        with C(self.temppath, 'w') as f:
            pass
        assert f.subclass_closed

    def test_readline_unbuffered_should_read_one_line_only(self):
        import os

        with self.file(self.temppath, 'wb') as f:
            f.write('foo\nbar\n')

        with self.file(self.temppath, 'rb', 0) as f:
            s = f.readline()
            assert s == 'foo\n'
            s = os.read(f.fileno(), 10)
            assert s == 'bar\n'

def test_flush_at_exit():
    from pypy import conftest
    from pypy.tool.option import make_config, make_objspace
    from rpython.tool.udir import udir

    tmpfile = udir.join('test_flush_at_exit')
    config = make_config(conftest.option)
    space = make_objspace(config)
    space.appexec([space.wrap(str(tmpfile))], """(tmpfile):
        f = open(tmpfile, 'w')
        f.write('42')
        # no flush() and no close()
        import sys; sys._keepalivesomewhereobscure = f
    """)
    space.finish()
    assert tmpfile.read() == '42'
