
# -*- coding: utf-8 -*-

from __future__ import with_statement
from pypy.objspace.std import StdObjSpace
from pypy.tool.udir import udir
from pypy.conftest import gettestobjspace
from pypy.tool.autopath import pypydir
from pypy.rpython.module.ll_os import RegisterOs
import os
import py
import sys
import signal

def setup_module(mod):
    if os.name != 'nt':
        mod.space = gettestobjspace(usemodules=['posix', 'fcntl'])
    else:
        # On windows, os.popen uses the subprocess module
        mod.space = gettestobjspace(usemodules=['posix', '_rawffi', 'thread'])
    mod.path = udir.join('posixtestfile.txt')
    mod.path.write("this is a test")
    mod.path2 = udir.join('test_posix2-')
    pdir = udir.ensure('posixtestdir', dir=True)
    pdir.join('file1').write("test1")
    os.chmod(str(pdir.join('file1')), 0600)
    pdir.join('file2').write("test2")
    pdir.join('another_longer_file_name').write("test3")
    mod.pdir = pdir
    unicode_dir = udir.ensure('fi\xc5\x9fier.txt', dir=True)
    unicode_dir.join('somefile').write('who cares?')
    mod.unicode_dir = unicode_dir

    # in applevel tests, os.stat uses the CPython os.stat.
    # Be sure to return times with full precision
    # even when running on top of CPython 2.4.
    os.stat_float_times(True)

    # Initialize sys.filesystemencoding
    space.call_method(space.getbuiltinmodule('sys'), 'getfilesystemencoding')

def need_sparse_files():
    if sys.platform == 'darwin':
        py.test.skip("no sparse files on default Mac OS X file system")
    if os.name == 'nt':
        py.test.skip("no sparse files on Windows")

GET_POSIX = "(): import %s as m ; return m" % os.name

class AppTestPosix:
    def setup_class(cls):
        cls.space = space
        cls.w_posix = space.appexec([], GET_POSIX)
        cls.w_path = space.wrap(str(path))
        cls.w_path2 = space.wrap(str(path2))
        cls.w_pdir = space.wrap(str(pdir))
        try:
            cls.w_unicode_dir = space.wrap(
                str(unicode_dir).decode(sys.getfilesystemencoding()))
        except UnicodeDecodeError:
            # filesystem encoding is not good enough
            cls.w_unicode_dir = space.w_None
        if hasattr(os, 'getuid'):
            cls.w_getuid = space.wrap(os.getuid())
            cls.w_geteuid = space.wrap(os.geteuid())
        if hasattr(os, 'getgid'):
            cls.w_getgid = space.wrap(os.getgid())
        if hasattr(os, 'getgroups'):
            cls.w_getgroups = space.newlist([space.wrap(e) for e in os.getgroups()])
        if hasattr(os, 'getpgid'):
            cls.w_getpgid = space.wrap(os.getpgid(os.getpid()))
        if hasattr(os, 'getsid'):
            cls.w_getsid0 = space.wrap(os.getsid(0))
        if hasattr(os, 'sysconf'):
            sysconf_name = os.sysconf_names.keys()[0]
            cls.w_sysconf_name = space.wrap(sysconf_name)
            cls.w_sysconf_value = space.wrap(os.sysconf_names[sysconf_name])
            cls.w_sysconf_result = space.wrap(os.sysconf(sysconf_name))
        cls.w_SIGABRT = space.wrap(signal.SIGABRT)
        cls.w_python = space.wrap(sys.executable)
        if hasattr(os, 'major'):
            cls.w_expected_major_12345 = space.wrap(os.major(12345))
            cls.w_expected_minor_12345 = space.wrap(os.minor(12345))
        cls.w_udir = space.wrap(str(udir))

    def setup_method(self, meth):
        if getattr(meth, 'need_sparse_files', False):
            need_sparse_files()

    def test_posix_is_pypy_s(self):
        assert self.posix.__file__

    def test_some_posix_basic_operation(self):
        path = self.path
        posix = self.posix
        fd = posix.open(path, posix.O_RDONLY, 0777)
        fd2 = posix.dup(fd)
        assert not posix.isatty(fd2)
        s = posix.read(fd, 1)
        assert s == 't'
        posix.lseek(fd, 5, 0)
        s = posix.read(fd, 1)
        assert s == 'i'
        st = posix.fstat(fd)
        posix.close(fd2)
        posix.close(fd)

        import sys, stat
        assert st[0] == st.st_mode
        assert st[1] == st.st_ino
        assert st[2] == st.st_dev
        assert st[3] == st.st_nlink
        assert st[4] == st.st_uid
        assert st[5] == st.st_gid
        assert st[6] == st.st_size
        assert st[7] == int(st.st_atime)
        assert st[8] == int(st.st_mtime)
        assert st[9] == int(st.st_ctime)

        assert stat.S_IMODE(st.st_mode) & stat.S_IRUSR
        assert stat.S_IMODE(st.st_mode) & stat.S_IWUSR
        if not sys.platform.startswith('win'):
            assert not (stat.S_IMODE(st.st_mode) & stat.S_IXUSR)

        assert st.st_size == 14
        assert st.st_nlink == 1

        #if sys.platform.startswith('linux'):
        #    # expects non-integer timestamps - it's unlikely that they are
        #    # all three integers
        #    assert ((st.st_atime, st.st_mtime, st.st_ctime) !=
        #            (st[7],       st[8],       st[9]))
        #    assert st.st_blksize * st.st_blocks >= st.st_size
        if sys.platform.startswith('linux'):
            assert hasattr(st, 'st_rdev')

    def test_stat_float_times(self):
        path = self.path
        posix = self.posix
        current = posix.stat_float_times()
        assert current is True
        try:
            posix.stat_float_times(True)
            st = posix.stat(path)
            assert isinstance(st.st_mtime, float)
            assert st[7] == int(st.st_atime)

            posix.stat_float_times(False)
            st = posix.stat(path)
            assert isinstance(st.st_mtime, (int, long))
            assert st[7] == st.st_atime
        finally:
            posix.stat_float_times(current)

    def test_stat_result(self):
        st = self.posix.stat_result((0, 0, 0, 0, 0, 0, 0, 41, 42.1, 43))
        assert st.st_atime == 41
        assert st.st_mtime == 42.1
        assert st.st_ctime == 43

    def test_stat_lstat(self):
        import stat
        st = self.posix.stat(".")
        assert stat.S_ISDIR(st.st_mode)
        st = self.posix.lstat(".")
        assert stat.S_ISDIR(st.st_mode)

    def test_stat_exception(self):
        import sys, errno
        for fn in [self.posix.stat, self.posix.lstat]:
            try:
                fn("nonexistentdir/nonexistentfile")
            except OSError, e:
                assert e.errno == errno.ENOENT
                assert e.filename == "nonexistentdir/nonexistentfile"
                # On Windows, when the parent directory does not exist,
                # the winerror is 3 (cannot find the path specified)
                # instead of 2 (cannot find the file specified)
                if sys.platform == 'win32':
                    assert isinstance(e, WindowsError)
                    assert e.winerror == 3

    def test_pickle(self):
        import pickle, os
        st = self.posix.stat(os.curdir)
        print type(st).__module__
        s = pickle.dumps(st)
        print repr(s)
        new = pickle.loads(s)
        assert new == st
        assert type(new) is type(st)

    def test_open_exception(self):
        posix = self.posix
        try:
            posix.open('qowieuqwoeiu', 0, 0)
        except OSError, e:
            assert e.filename == 'qowieuqwoeiu'
        else:
            assert 0

    def test_filename_exception(self):
        for fname in ['unlink', 'remove',
                      'chdir', 'mkdir', 'rmdir',
                      'listdir', 'readlink',
                      'chroot']:
            if hasattr(self.posix, fname):
                func = getattr(self.posix, fname)
                try:
                    func('qowieuqw/oeiu')
                except OSError, e:
                    assert e.filename == 'qowieuqw/oeiu'
                else:
                    assert 0

    def test_chmod_exception(self):
        try:
            self.posix.chmod('qowieuqw/oeiu', 0)
        except OSError, e:
            assert e.filename == 'qowieuqw/oeiu'
        else:
            assert 0

    def test_chown_exception(self):
        if hasattr(self.posix, 'chown'):
            try:
                self.posix.chown('qowieuqw/oeiu', 0, 0)
            except OSError, e:
                assert e.filename == 'qowieuqw/oeiu'
            else:
                assert 0

    def test_utime_exception(self):
        for arg in [None, (0, 0)]:
            try:
                self.posix.utime('qowieuqw/oeiu', arg)
            except OSError, e:
                assert e.filename == 'qowieuqw/oeiu'
            else:
                assert 0

    def test_functions_raise_error(self):
        def ex(func, *args):
            try:
                func(*args)
            except OSError:
                pass
            else:
                raise AssertionError("%s(%s) did not raise" %(
                                     func.__name__,
                                     ", ".join([str(x) for x in args])))
        UNUSEDFD = 123123
        ex(self.posix.open, "qweqwe", 0, 0)
        ex(self.posix.lseek, UNUSEDFD, 123, 0)
        #apparently not posix-required: ex(self.posix.isatty, UNUSEDFD)
        ex(self.posix.read, UNUSEDFD, 123)
        ex(self.posix.write, UNUSEDFD, "x")
        ex(self.posix.close, UNUSEDFD)
        #UMPF cpython raises IOError ex(self.posix.ftruncate, UNUSEDFD, 123)
        ex(self.posix.fstat, UNUSEDFD)
        ex(self.posix.stat, "qweqwehello")
        # how can getcwd() raise?
        ex(self.posix.dup, UNUSEDFD)

    def test_fdopen(self):
        import errno
        path = self.path
        posix = self.posix
        fd = posix.open(path, posix.O_RDONLY, 0777)
        f = posix.fdopen(fd, "r")
        f.close()

        # Ensure that fcntl is not faked
        try:
            import fcntl
        except ImportError:
            pass
        else:
            assert fcntl.__file__.endswith('pypy/module/fcntl')
        exc = raises(OSError, posix.fdopen, fd)
        assert exc.value.errno == errno.EBADF

    def test_fdopen_hackedbuiltins(self):
        "Same test, with __builtins__.file removed"
        _file = __builtins__.file
        __builtins__.file = None
        try:
            path = self.path
            posix = self.posix
            fd = posix.open(path, posix.O_RDONLY, 0777)
            f = posix.fdopen(fd, "r")
            f.close()
        finally:
            __builtins__.file = _file

    def test_getcwd(self):
        assert isinstance(self.posix.getcwd(), str)
        assert isinstance(self.posix.getcwdu(), unicode)
        assert self.posix.getcwd() == self.posix.getcwdu()

    def test_listdir(self):
        pdir = self.pdir
        posix = self.posix
        result = posix.listdir(pdir)
        result.sort()
        assert result == ['another_longer_file_name',
                          'file1',
                          'file2']

    def test_listdir_unicode(self):
        unicode_dir = self.unicode_dir
        if unicode_dir is None:
            skip("encoding not good enough")
        posix = self.posix
        result = posix.listdir(unicode_dir)
        result.sort()
        assert result == [u'somefile']
        assert type(result[0]) is unicode

    def test_access(self):
        pdir = self.pdir + '/file1'
        posix = self.posix

        assert posix.access(pdir, posix.R_OK)
        assert posix.access(pdir, posix.W_OK)
        import sys
        if sys.platform != "win32":
            assert not posix.access(pdir, posix.X_OK)


    def test_times(self):
        """
        posix.times() should return a five-tuple giving float-representations
        (seconds, effectively) of the four fields from the underlying struct
        tms and the return value.
        """
        result = self.posix.times()
        assert isinstance(result, tuple)
        assert len(result) == 5
        for value in result:
            assert isinstance(value, float)


    def test_strerror(self):
        assert isinstance(self.posix.strerror(0), str)
        assert isinstance(self.posix.strerror(1), str)

    if hasattr(__import__(os.name), "fork"):
        def test_fork(self):
            os = self.posix
            pid = os.fork()
            if pid == 0:   # child
                os._exit(4)
            pid1, status1 = os.waitpid(pid, 0)
            assert pid1 == pid
            assert os.WIFEXITED(status1)
            assert os.WEXITSTATUS(status1) == 4
        pass # <- please, inspect.getsource(), don't crash


    if hasattr(__import__(os.name), "openpty"):
        def test_openpty(self):
            os = self.posix
            master_fd, slave_fd = os.openpty()
            assert isinstance(master_fd, int)
            assert isinstance(slave_fd, int)
            os.write(slave_fd, 'x\n')
            data = os.read(master_fd, 100)
            assert data.startswith('x')

    if hasattr(__import__(os.name), "forkpty"):
        def test_forkpty(self):
            import sys
            os = self.posix
            childpid, master_fd = os.forkpty()
            assert isinstance(childpid, int)
            assert isinstance(master_fd, int)
            if childpid == 0:
                data = os.read(0, 100)
                if data.startswith('abc'):
                    os._exit(42)
                else:
                    os._exit(43)
            os.write(master_fd, 'abc\n')
            _, status = os.waitpid(childpid, 0)
            assert status >> 8 == 42

    if hasattr(__import__(os.name), "execv"):
        def test_execv(self):
            os = self.posix
            if not hasattr(os, "fork"):
                skip("Need fork() to test execv()")
            pid = os.fork()
            if pid == 0:
                os.execv("/usr/bin/env", ["env", "python", "-c", "open('onefile', 'w').write('1')"])
            os.waitpid(pid, 0)
            assert open("onefile").read() == "1"
            os.unlink("onefile")

        def test_execv_raising(self):
            os = self.posix
            raises(OSError, 'os.execv("saddsadsadsadsa", ["saddsadsasaddsa"])')

        def test_execv_no_args(self):
            os = self.posix
            raises(ValueError, os.execv, "notepad", [])

        def test_execv_raising2(self):
            os = self.posix
            for n in 3, [3, "a"]:
                try:
                    os.execv("xxx", n)
                except TypeError,t:
                    assert str(t) == "execv() arg 2 must be an iterable of strings"
                else:
                    py.test.fail("didn't raise")

        def test_execv_unicode(self):
            os = self.posix
            import sys
            if not hasattr(os, "fork"):
                skip("Need fork() to test execv()")
            pid = os.fork()
            if pid == 0:
                os.execv(u"/bin/sh", ["sh", "-c",
                                      u"echo caf\xe9 \u1234 > onefile"])
            os.waitpid(pid, 0)
            output = u"caf\xe9 \u1234\n".encode(sys.getfilesystemencoding())
            assert open("onefile").read() == output
            os.unlink("onefile")

        def test_execve(self):
            os = self.posix
            if not hasattr(os, "fork"):
                skip("Need fork() to test execve()")
            pid = os.fork()
            if pid == 0:
                os.execve("/usr/bin/env", ["env", "python", "-c", "import os; open('onefile', 'w').write(os.environ['ddd'])"], {'ddd':'xxx'})
            os.waitpid(pid, 0)
            assert open("onefile").read() == "xxx"
            os.unlink("onefile")

        def test_execve_unicode(self):
            os = self.posix
            import sys
            if not hasattr(os, "fork"):
                skip("Need fork() to test execve()")
            pid = os.fork()
            if pid == 0:
                os.execve(u"/bin/sh", ["sh", "-c",
                                      u"echo caf\xe9 \u1234 > onefile"],
                          {'ddd': 'xxx'})
            os.waitpid(pid, 0)
            output = u"caf\xe9 \u1234\n".encode(sys.getfilesystemencoding())
            assert open("onefile").read() == output
            os.unlink("onefile")
        pass # <- please, inspect.getsource(), don't crash

    if hasattr(__import__(os.name), "spawnv"):
        def test_spawnv(self):
            os = self.posix
            import sys
            print self.python
            ret = os.spawnv(os.P_WAIT, self.python,
                            ['python', '-c', 'raise(SystemExit(42))'])
            assert ret == 42

    def test_popen(self):
        os = self.posix
        for i in range(5):
            stream = os.popen('echo 1')
            res = stream.read()
            assert res == '1\n'
            assert stream.close() is None

    if hasattr(__import__(os.name), '_getfullpathname'):
        def test__getfullpathname(self):
            # nt specific
            posix = self.posix
            import os
            sysdrv = os.getenv("SystemDrive", "C:")
            # just see if it does anything
            path = sysdrv + 'hubber'
            assert os.sep in posix._getfullpathname(path)

    def test_utime(self):
        os = self.posix
        from os.path import join
        # XXX utimes & float support
        path = join(self.pdir, "test_utime.txt")
        fh = open(path, "w")
        fh.write("x")
        fh.close()
        from time import time, sleep
        t0 = time()
        sleep(1.1)
        os.utime(path, None)
        assert os.stat(path).st_atime > t0
        os.utime(path, (int(t0), int(t0)))
        assert int(os.stat(path).st_atime) == int(t0)

    def test_utime_raises(self):
        os = self.posix
        raises(TypeError, "os.utime('xxx', 3)")
        raises(OSError, "os.utime('somefilewhichihopewouldneverappearhere', None)")

    for name in RegisterOs.w_star:
        if hasattr(os, name):
            values = [0, 1, 127, 128, 255]
            code = py.code.Source("""
            def test_wstar(self):
                os = self.posix
                %s
            """ % "\n    ".join(["assert os.%s(%d) == %d" % (name, value,
                             getattr(os, name)(value)) for value in values]))
            d = {}
            exec code.compile() in d
            locals()['test_' + name] = d['test_wstar']

    if hasattr(os, 'WIFSIGNALED'):
        def test_wifsignaled(self):
            os = self.posix
            assert os.WIFSIGNALED(0) == False
            assert os.WIFSIGNALED(1) == True

    if hasattr(os, 'uname'):
        def test_os_uname(self):
            os = self.posix
            res = os.uname()
            assert len(res) == 5
            for i in res:
                assert isinstance(i, str)
            assert isinstance(res, tuple)

    if hasattr(os, 'getuid'):
        def test_os_getuid(self):
            os = self.posix
            assert os.getuid() == self.getuid
            assert os.geteuid() == self.geteuid

    if hasattr(os, 'setuid'):
        def test_os_setuid_error(self):
            os = self.posix
            raises(OverflowError, os.setuid, -2**31-1)
            raises(OverflowError, os.setuid, 2**32)

    if hasattr(os, 'getgid'):
        def test_os_getgid(self):
            os = self.posix
            assert os.getgid() == self.getgid

    if hasattr(os, 'getgroups'):
        def test_os_getgroups(self):
            os = self.posix
            assert os.getgroups() == self.getgroups

    if hasattr(os, 'getpgid'):
        def test_os_getpgid(self):
            os = self.posix
            assert os.getpgid(os.getpid()) == self.getpgid
            raises(OSError, os.getpgid, 1234567)

    if hasattr(os, 'setgid'):
        def test_os_setgid_error(self):
            os = self.posix
            raises(OverflowError, os.setgid, -2**31-1)
            raises(OverflowError, os.setgid, 2**32)

    if hasattr(os, 'getsid'):
        def test_os_getsid(self):
            os = self.posix
            assert os.getsid(0) == self.getsid0
            raises(OSError, os.getsid, -100000)

    if hasattr(os, 'sysconf'):
        def test_os_sysconf(self):
            os = self.posix
            assert os.sysconf(self.sysconf_value) == self.sysconf_result
            assert os.sysconf(self.sysconf_name) == self.sysconf_result
            assert os.sysconf_names[self.sysconf_name] == self.sysconf_value

        def test_os_sysconf_error(self):
            os = self.posix
            raises(ValueError, os.sysconf, "!@#$%!#$!@#")

    if hasattr(os, 'fpathconf'):
        def test_os_fpathconf(self):
            os = self.posix
            assert os.fpathconf(1, "PC_PIPE_BUF") >= 128
            raises(OSError, os.fpathconf, -1, "PC_PIPE_BUF")
            raises(ValueError, os.fpathconf, 1, "##")

    if hasattr(os, 'wait'):
        def test_os_wait(self):
            os = self.posix
            exit_status = 0x33

            if not hasattr(os, "fork"):
                skip("Need fork() to test wait()")
            if hasattr(os, "waitpid") and hasattr(os, "WNOHANG"):
                try:
                    while os.waitpid(-1, os.WNOHANG)[0]:
                        pass
                except OSError:  # until we get "No child processes", hopefully
                    pass
            child = os.fork()
            if child == 0: # in child
                os._exit(exit_status)
            else:
                pid, status = os.wait()
                assert child == pid
                assert os.WIFEXITED(status)
                assert os.WEXITSTATUS(status) == exit_status

    if hasattr(os, 'getloadavg'):
        def test_os_getloadavg(self):
            os = self.posix
            l0, l1, l2 = os.getloadavg()
            assert type(l0) is float and l0 >= 0.0
            assert type(l1) is float and l0 >= 0.0
            assert type(l2) is float and l0 >= 0.0

    if hasattr(os, 'major'):
        def test_major_minor(self):
            os = self.posix
            assert os.major(12345) == self.expected_major_12345
            assert os.minor(12345) == self.expected_minor_12345
            assert os.makedev(self.expected_major_12345,
                              self.expected_minor_12345) == 12345

    if hasattr(os, 'fsync'):
        def test_fsync(self):
            os = self.posix
            f = open(self.path2, "w")
            try:
                fd = f.fileno()
                os.fsync(fd)
                os.fsync(long(fd))
                os.fsync(f)     # <- should also work with a file, or anything
            finally:            #    with a fileno() method
                f.close()
            raises(OSError, os.fsync, fd)
            raises(ValueError, os.fsync, -1)

    if hasattr(os, 'fdatasync'):
        def test_fdatasync(self):
            os = self.posix
            f = open(self.path2, "w")
            try:
                fd = f.fileno()
                os.fdatasync(fd)
            finally:
                f.close()
            raises(OSError, os.fdatasync, fd)
            raises(ValueError, os.fdatasync, -1)

    if hasattr(os, 'fchdir'):
        def test_fchdir(self):
            os = self.posix
            localdir = os.getcwd()
            try:
                os.mkdir(self.path2 + 'dir')
                fd = os.open(self.path2 + 'dir', os.O_RDONLY)
                try:
                    os.fchdir(fd)
                    mypath = os.getcwd()
                finally:
                    os.close(fd)
                assert mypath.endswith('test_posix2-dir')
                raises(OSError, os.fchdir, fd)
                raises(ValueError, os.fchdir, -1)
            finally:
                os.chdir(localdir)

    def test_largefile(self):
        os = self.posix
        fd = os.open(self.path2 + 'test_largefile', os.O_RDWR | os.O_CREAT, 0666)
        os.ftruncate(fd, 10000000000L)
        res = os.lseek(fd, 9900000000L, 0)
        assert res == 9900000000L
        res = os.lseek(fd, -5000000000L, 1)
        assert res == 4900000000L
        res = os.lseek(fd, -5200000000L, 2)
        assert res == 4800000000L
        os.close(fd)

        st = os.stat(self.path2 + 'test_largefile')
        assert st.st_size == 10000000000L
    test_largefile.need_sparse_files = True

    def test_write_buffer(self):
        os = self.posix
        fd = os.open(self.path2 + 'test_write_buffer', os.O_RDWR | os.O_CREAT, 0666)
        def writeall(s):
            while s:
                count = os.write(fd, s)
                assert count > 0
                s = s[count:]
        writeall('hello, ')
        writeall(buffer('world!\n'))
        res = os.lseek(fd, 0, 0)
        assert res == 0
        data = ''
        while True:
            s = os.read(fd, 100)
            if not s:
                break
            data += s
        assert data == 'hello, world!\n'
        os.close(fd)

    def test_write_unicode(self):
        os = self.posix
        fd = os.open(self.path2 + 'test_write_unicode', os.O_RDWR | os.O_CREAT, 0666)
        os.write(fd, u'X')
        raises(UnicodeEncodeError, os.write, fd, u'\xe9')
        os.lseek(fd, 0, 0)
        data = os.read(fd, 2)
        assert data == 'X'
        os.close(fd)

    if hasattr(__import__(os.name), "fork"):
        def test_abort(self):
            os = self.posix
            pid = os.fork()
            if pid == 0:
                os.abort()
            pid1, status1 = os.waitpid(pid, 0)
            assert pid1 == pid
            assert os.WIFSIGNALED(status1)
            assert os.WTERMSIG(status1) == self.SIGABRT
        pass # <- please, inspect.getsource(), don't crash

    def test_closerange(self):
        os = self.posix
        if not hasattr(os, 'closerange'):
            skip("missing os.closerange()")
        fds = [os.open(self.path + str(i), os.O_CREAT|os.O_WRONLY, 0777)
               for i in range(15)]
        fds.sort()
        start = fds.pop()
        stop = start + 1
        while len(fds) > 3 and fds[-1] == start - 1:
            start = fds.pop()
        os.closerange(start, stop)
        for fd in fds:
            os.close(fd)     # should not have been closed
        for fd in range(start, stop):
            raises(OSError, os.fstat, fd)   # should have been closed

    if hasattr(os, 'chown'):
        def test_chown(self):
            os = self.posix
            os.unlink(self.path)
            raises(OSError, os.chown, self.path, os.getuid(), os.getgid())
            f = open(self.path, "w")
            f.write("this is a test")
            f.close()
            os.chown(self.path, os.getuid(), os.getgid())

    if hasattr(os, 'lchown'):
        def test_lchown(self):
            os = self.posix
            os.unlink(self.path)
            raises(OSError, os.lchown, self.path, os.getuid(), os.getgid())
            os.symlink('foobar', self.path)
            os.lchown(self.path, os.getuid(), os.getgid())

    if hasattr(os, 'mkfifo'):
        def test_mkfifo(self):
            os = self.posix
            os.mkfifo(self.path2 + 'test_mkfifo', 0666)
            st = os.lstat(self.path2 + 'test_mkfifo')
            import stat
            assert stat.S_ISFIFO(st.st_mode)

    if hasattr(os, 'mknod'):
        def test_mknod(self):
            import stat
            os = self.posix
            # os.mknod() may require root priviledges to work at all
            try:
                # not very useful: os.mknod() without specifying 'mode'
                os.mknod(self.path2 + 'test_mknod-1')
            except OSError, e:
                skip("os.mknod(): got %r" % (e,))
            st = os.lstat(self.path2 + 'test_mknod-1')
            assert stat.S_ISREG(st.st_mode)
            # os.mknod() with S_IFIFO
            os.mknod(self.path2 + 'test_mknod-2', 0600 | stat.S_IFIFO)
            st = os.lstat(self.path2 + 'test_mknod-2')
            assert stat.S_ISFIFO(st.st_mode)

        def test_mknod_with_ifchr(self):
            # os.mknod() with S_IFCHR
            # -- usually requires root priviledges --
            os = self.posix
            if hasattr(os.lstat('.'), 'st_rdev'):
                import stat
                try:
                    os.mknod(self.path2 + 'test_mknod-3', 0600 | stat.S_IFCHR,
                             0x105)
                except OSError, e:
                    skip("os.mknod() with S_IFCHR: got %r" % (e,))
                else:
                    st = os.lstat(self.path2 + 'test_mknod-3')
                    assert stat.S_ISCHR(st.st_mode)
                    assert st.st_rdev == 0x105

    if hasattr(os, 'nice') and hasattr(os, 'fork') and hasattr(os, 'waitpid'):
        def test_nice(self):
            os = self.posix
            myprio = os.nice(0)
            #
            pid = os.fork()
            if pid == 0:    # in the child
                res = os.nice(3)
                os._exit(res)
            #
            pid1, status1 = os.waitpid(pid, 0)
            assert pid1 == pid
            assert os.WIFEXITED(status1)
            assert os.WEXITSTATUS(status1) == myprio + 3

    if hasattr(os, 'symlink'):
        def test_symlink(self):
            posix = self.posix
            unicode_dir = self.unicode_dir
            if unicode_dir is None:
                skip("encoding not good enough")
            dest = u"%s/file.txt" % unicode_dir
            posix.symlink(u"%s/somefile" % unicode_dir, dest)
            with open(dest) as f:
                data = f.read()
                assert data == "who cares?"

    try:
        os.getlogin()
    except (AttributeError, OSError):
        pass
    else:
        def test_getlogin(self):
            assert isinstance(self.posix.getlogin(), str)
            # How else could we test that getlogin is properly
            # working?

    def test_tmpfile(self):
        os = self.posix
        f = os.tmpfile()
        f.write("xxx")
        f.flush()
        f.seek(0, 0)
        assert isinstance(f, file)
        assert f.read() == 'xxx'

    def test_tmpnam(self):
        import stat, os
        s1 = os.tmpnam()
        s2 = os.tmpnam()
        assert s1 != s2
        def isdir(s):
            try:
                return stat.S_ISDIR(os.stat(s).st_mode)
            except OSError:
                return -1
        assert isdir(s1) == -1
        assert isdir(s2) == -1
        assert isdir(os.path.dirname(s1)) == 1
        assert isdir(os.path.dirname(s2)) == 1

    def test_tempnam(self):
        import stat, os
        for dir in [None, self.udir]:
            for prefix in [None, 'foobar']:
                s1 = os.tempnam(dir, prefix)
                s2 = os.tempnam(dir, prefix)
                assert s1 != s2
                def isdir(s):
                    try:
                        return stat.S_ISDIR(os.stat(s).st_mode)
                    except OSError:
                        return -1
                assert isdir(s1) == -1
                assert isdir(s2) == -1
                assert isdir(os.path.dirname(s1)) == 1
                assert isdir(os.path.dirname(s2)) == 1
                if dir:
                    assert os.path.dirname(s1) == dir
                    assert os.path.dirname(s2) == dir
                assert os.path.basename(s1).startswith(prefix or 'tmp')
                assert os.path.basename(s2).startswith(prefix or 'tmp')

    def test_tmpnam_warning(self):
        import warnings, os
        #
        def f_tmpnam_warning(): os.tmpnam()    # a single line
        #
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            f_tmpnam_warning()
            assert len(w) == 1
            assert issubclass(w[-1].category, RuntimeWarning)
            assert "potential security risk" in str(w[-1].message)
            # check that the warning points to the call to os.tmpnam(),
            # not to some code inside app_posix.py
            assert w[-1].lineno == f_tmpnam_warning.func_code.co_firstlineno


class AppTestEnvironment(object):
    def setup_class(cls):
        cls.space = space
        cls.w_posix = space.appexec([], "(): import %s as m ; return m" % os.name)
        cls.w_os = space.appexec([], "(): import os; return os")
        cls.w_path = space.wrap(str(path))

    def test_environ(self):
        posix = self.posix
        os = self.os
        assert posix.environ['PATH']
        del posix.environ['PATH']
        def fn(): posix.environ['PATH']
        raises(KeyError, fn)

    if hasattr(__import__(os.name), "unsetenv"):
        def test_unsetenv_nonexisting(self):
            os = self.os
            os.unsetenv("XYZABC") #does not raise
            try:
                os.environ["ABCABC"]
            except KeyError:
                pass
            else:
                raise AssertionError("did not raise KeyError")
            os.environ["ABCABC"] = "1"
            assert os.environ["ABCABC"] == "1"
            os.unsetenv("ABCABC")
            cmd = '''python -c "import os, sys; sys.exit(int('ABCABC' in os.environ))" '''
            res = os.system(cmd)
            assert res == 0

class AppTestPosixUnicode:

    def setup_class(cls):
        cls.space = space
        cls.w_posix = space.appexec([], GET_POSIX)
        if py.test.config.option.runappdirect:
            # Can't change encoding
            try:
                u"ą".encode(sys.getfilesystemencoding())
            except UnicodeEncodeError:
                py.test.skip("encoding not good enough")
        else:
            cls.save_fs_encoding = space.sys.filesystemencoding
            space.sys.filesystemencoding = "utf-8"

    def teardown_class(cls):
        try:
            cls.space.sys.filesystemencoding = cls.save_fs_encoding
        except AttributeError:
            pass

    def test_stat_unicode(self):
        # test that passing unicode would not raise UnicodeDecodeError
        try:
            self.posix.stat(u"ą")
        except OSError:
            pass

    def test_open_unicode(self):
        # Ensure passing unicode doesn't raise UnicodeEncodeError
        try:
            self.posix.open(u"ą", self.posix.O_WRONLY)
        except OSError:
            pass

    def test_remove_unicode(self):
        # See 2 above ;)
        try:
            self.posix.remove(u"ą")
        except OSError:
            pass

class AppTestUnicodeFilename:
    def setup_class(cls):
        ufilename = (unicode(udir.join('test_unicode_filename_')) +
                     u'\u65e5\u672c.txt') # "Japan"
        try:
            f = file(ufilename, 'w')
        except UnicodeEncodeError:
            py.test.skip("encoding not good enough")
        f.write("test")
        f.close()
        cls.space = space
        cls.w_filename = space.wrap(ufilename)
        cls.w_posix = space.appexec([], GET_POSIX)

    def test_open(self):
        fd = self.posix.open(self.filename, self.posix.O_RDONLY)
        try:
            content = self.posix.read(fd, 50)
        finally:
            self.posix.close(fd)
        assert content == "test"


class TestPexpect(object):
    # XXX replace with AppExpectTest class as soon as possible
    def setup_class(cls):
        try:
            import pexpect
        except ImportError:
            py.test.skip("pexpect not found")

    def _spawn(self, *args, **kwds):
        import pexpect
        print 'SPAWN:', args, kwds
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv):
        py_py = py.path.local(pypydir).join('bin', 'py.py')
        return self._spawn(sys.executable, [str(py_py)] + argv)

    def test_ttyname(self):
        source = py.code.Source("""
        import os, sys
        assert os.ttyname(sys.stdin.fileno())
        print 'ok!'
        """)
        f = udir.join("test_ttyname.py")
        f.write(source)
        child = self.spawn([str(f)])
        child.expect('ok!')
