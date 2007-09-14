import py

from pypy.conftest import gettestobjspace

class AppTestFile(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=("_file", ))
        cls.w_temppath = cls.space.wrap(
            str(py.test.ensuretemp("fileimpl").join("foo.txt")))

    def test_simple(self):
        import _file
        f = _file.file(self.temppath, "w")
        f.write("foo")
        f.close()
        f = _file.file(self.temppath, "r")
        raises(TypeError, f.read, None)
        try:
            s = f.read()
            assert s == "foo"
        finally:
            f.close()

    def test_readline(self):
        import _file
        f = _file.file(self.temppath, "w")
        try:
            f.write("foo\nbar\n")
        finally:
            f.close()
        f = _file.file(self.temppath, "r")
        raises(TypeError, f.readline, None)
        try:
            s = f.readline()
            assert s == "foo\n"
            s = f.readline()
            assert s == "bar\n"
        finally:
            f.close()

    def test_readlines(self):
        import _file
        f = _file.file(self.temppath, "w")
        try:
            f.write("foo\nbar\n")
        finally:
            f.close()
        f = _file.file(self.temppath, "r")
        raises(TypeError, f.readlines, None)
        try:
            s = f.readlines()
            assert s == ["foo\n", "bar\n"]
        finally:
            f.close()


    def test_fdopen(self):
        import _file, os
        f = _file.file(self.temppath, "w")
        try:
            f.write("foo")
        finally:
            f.close()
        fd = os.open(self.temppath, os.O_WRONLY | os.O_CREAT)
        f2 = _file.file.fdopen(fd, "a")
        f2.seek(0, 2)
        f2.write("bar")
        f2.close()
        # don't close fd, will get a whining __del__
        f = _file.file(self.temppath, "r")
        try:
            s = f.read()
            assert s == "foobar"
        finally:
            f.close()

    def test_badmode(self):
        import _file
        raises(IOError, _file.file, "foo", "bar")

    def test_wraposerror(self):
        import _file
        raises(IOError, _file.file, "hopefully/not/existant.bar")

    def test_correct_file_mode(self):
        import _file, os
        f = _file.file(self.temppath, "w")
        umask = os.umask(18)
        os.umask(umask)
        try:
            f.write("foo")
        finally:
            f.close()
        assert oct(os.stat(self.temppath).st_mode & 0777 | umask) == oct(0666)

    def test_newlines(self):
        import _file, os
        f = _file.file(self.temppath, "wb")
        f.write("\r\n")
        assert f.newlines is None
        f.close()
        f = _file.file(self.temppath, "rU")
        res = f.read()
        assert res == "\n"
        assert f.newlines == "\r\n"

    def test_unicode(self):
        import _file, os
        f = _file.file(self.temppath, "w")
        f.write(u"hello\n")
        f.close()
        f = _file.file(self.temppath, "r")
        res = f.read()
        assert res == "hello\n"
        assert type(res) is str
        f.close()

class AppTestConcurrency(object):
    # these tests only really make sense on top of a translated pypy-c,
    # because on top of py.py the inner calls to os.write() don't
    # release our object space's GIL.
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=("_file", "thread"))
        cls.w_temppath = cls.space.wrap(
            str(py.test.ensuretemp("fileimpl").join("concurrency.txt")))

    def test_concurrent_writes(self):
        # check that f.write() is atomic
        import thread, _file, time
        f = _file.file(self.temppath, "w+b")
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
