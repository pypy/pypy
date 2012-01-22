from __future__ import with_statement
import py, os, errno

from pypy.conftest import gettestobjspace, option

def getfile(space):
    return space.appexec([], """():
        try:
            import _file
            return _file.file
        except ImportError:     # when running with py.test -A
            return file
    """)

class AppTestFile(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=("_file", ))
        cls.w_temppath = cls.space.wrap(
            str(py.test.ensuretemp("fileimpl").join("foo.txt")))
        cls.w_file = getfile(cls.space)

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
        except IOError, e:
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
            assert self.temppath in g.getvalue()


class AppTestNonblocking(object):
    def setup_class(cls):
        from pypy.module._file.interp_file import W_File

        cls.old_read = os.read

        if option.runappdirect:
            py.test.skip("works with internals of _file impl on py.py")

        state = [0]
        def read(fd, n=None):
            if fd != 42:
                return cls.old_read(fd, n)
            if state[0] == 0:
                state[0] += 1
                return "xyz"
            if state[0] < 3:
                state[0] += 1
                raise OSError(errno.EAGAIN, "xyz")
            return ''
        os.read = read
        stdin = W_File(cls.space)
        stdin.file_fdopen(42, "r", 1)
        stdin.name = '<stdin>'
        cls.w_stream = stdin

    def teardown_class(cls):
        os.read = cls.old_read

    def test_nonblocking_file(self):
        res = self.stream.read()
        assert res == 'xyz'

class AppTestConcurrency(object):
    # these tests only really make sense on top of a translated pypy-c,
    # because on top of py.py the inner calls to os.write() don't
    # release our object space's GIL.
    def setup_class(cls):
        if not option.runappdirect:
            py.test.skip("likely to deadlock when interpreted by py.py")
        cls.space = gettestobjspace(usemodules=("_file", "thread"))
        cls.w_temppath = cls.space.wrap(
            str(py.test.ensuretemp("fileimpl").join("concurrency.txt")))
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


class AppTestFile25:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=("_file", ))
        cls.w_temppath = cls.space.wrap(
            str(py.test.ensuretemp("fileimpl").join("foo.txt")))
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

def test_flush_at_exit():
    from pypy import conftest
    from pypy.tool.option import make_config, make_objspace
    from pypy.tool.udir import udir

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
