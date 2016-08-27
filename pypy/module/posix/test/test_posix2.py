# -*- coding: utf-8 -*-

import os
import py
import sys
import signal

from rpython.tool.udir import udir
from pypy.tool.pytest.objspace import gettestobjspace
from rpython.translator.c.test.test_extfunc import need_sparse_files
from rpython.rlib import rposix

USEMODULES = ['binascii', 'posix', 'signal', 'struct', 'time']
# py3k os.open uses subprocess, requiring the following per platform
if os.name != 'nt':
    USEMODULES += ['fcntl', 'select', '_posixsubprocess']
else:
    USEMODULES += ['_rawffi', 'thread']

def setup_module(mod):
    mod.space = gettestobjspace(usemodules=USEMODULES)
    mod.path = udir.join('posixtestfile.txt')
    mod.path.write("this is a test")
    mod.path2 = udir.join('test_posix2-')
    pdir = udir.ensure('posixtestdir', dir=True)
    pdir.join('file1').write("test1")
    os.chmod(str(pdir.join('file1')), 0o600)
    pdir.join('file2').write("test2")
    pdir.join('another_longer_file_name').write("test3")
    mod.pdir = pdir
    bytes_dir = udir.ensure('fi\xc5\x9fier.txt', dir=True)
    bytes_dir.join('somefile').write('who cares?')
    bytes_dir.join('caf\xe9').write('who knows?')
    mod.bytes_dir = bytes_dir
    # an escaped surrogate
    mod.esurrogate_dir = udir.ensure('foo\x80', dir=True)

    # in applevel tests, os.stat uses the CPython os.stat.
    # Be sure to return times with full precision
    # even when running on top of CPython 2.4.
    os.stat_float_times(True)

    # Initialize sys.filesystemencoding
    # space.call_method(space.getbuiltinmodule('sys'), 'getfilesystemencoding')


GET_POSIX = "(): import %s as m ; return m" % os.name


class AppTestPosix:
    spaceconfig = {'usemodules': USEMODULES}

    def setup_class(cls):
        space = cls.space
        cls.w_runappdirect = space.wrap(cls.runappdirect)
        cls.w_posix = space.appexec([], GET_POSIX)
        cls.w_os = space.appexec([], "(): import os as m ; return m")
        cls.w_path = space.wrap(str(path))
        cls.w_path2 = space.wrap(str(path2))
        cls.w_pdir = space.wrap(str(pdir))
        cls.w_bytes_dir = space.newbytes(str(bytes_dir))
        cls.w_esurrogate_dir = space.newbytes(str(esurrogate_dir))
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
        if hasattr(os, 'confstr'):
            confstr_name = os.confstr_names.keys()[0]
            cls.w_confstr_name = space.wrap(confstr_name)
            cls.w_confstr_value = space.wrap(os.confstr_names[confstr_name])
            cls.w_confstr_result = space.wrap(os.confstr(confstr_name))
        cls.w_SIGABRT = space.wrap(signal.SIGABRT)
        cls.w_python = space.wrap(sys.executable)
        if hasattr(os, 'major'):
            cls.w_expected_major_12345 = space.wrap(os.major(12345))
            cls.w_expected_minor_12345 = space.wrap(os.minor(12345))
        cls.w_udir = space.wrap(str(udir))

    def setup_method(self, meth):
        if getattr(meth, 'need_sparse_files', False):
            if sys.maxsize < 2**32 and not self.runappdirect:
                # this fails because it uses ll2ctypes to call the posix
                # functions like 'open' and 'lseek', whereas a real compiled
                # C program would macro-define them to their longlong versions
                py.test.skip("emulation of files can't use "
                             "larger-than-long offsets")
            need_sparse_files()

    def test_posix_is_pypy_s(self):
        assert hasattr(self.posix, '_statfields')

    def test_some_posix_basic_operation(self):
        path = self.path
        posix = self.posix
        fd = posix.open(path, posix.O_RDONLY, 0o777)
        fd2 = posix.dup(fd)
        assert not posix.isatty(fd2)
        s = posix.read(fd, 1)
        assert s == b't'
        posix.lseek(fd, 5, 0)
        s = posix.read(fd, 1)
        assert s == b'i'
        st = posix.fstat(fd)
        assert st == posix.stat(fd)
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
            assert isinstance(st.st_mtime, int)
            assert st[7] == st.st_atime
        finally:
            posix.stat_float_times(current)

    def test_stat_result(self):
        st = self.posix.stat_result((0, 0, 0, 0, 0, 0, 0, 41, 42.1, 43))
        assert st.st_atime == 41
        assert st.st_mtime == 42.1
        assert st.st_ctime == 43
        assert repr(st).startswith(self.posix.__name__ + '.stat_result')

    def test_stat_lstat(self):
        import stat
        st = self.posix.stat(".")
        assert stat.S_ISDIR(st.st_mode)
        st = self.posix.stat(b".")
        assert stat.S_ISDIR(st.st_mode)
        st = self.posix.stat(bytearray(b"."))
        assert stat.S_ISDIR(st.st_mode)
        st = self.posix.lstat(".")
        assert stat.S_ISDIR(st.st_mode)

    def test_stat_exception(self):
        import sys
        import errno
        for fn in [self.posix.stat, self.posix.lstat]:
            exc = raises(OSError, fn, "nonexistentdir/nonexistentfile")
            assert exc.value.errno == errno.ENOENT
            assert exc.value.filename == "nonexistentdir/nonexistentfile"

        excinfo = raises(TypeError, self.posix.stat, None)
        assert "can't specify None" in str(excinfo.value)
        excinfo = raises(TypeError, self.posix.stat, 2.)
        assert "should be string, bytes or integer, not float" in str(excinfo.value)
        raises(ValueError, self.posix.stat, -1)

    if hasattr(__import__(os.name), "statvfs"):
        def test_statvfs(self):
            st = self.posix.statvfs(".")
            assert isinstance(st, self.posix.statvfs_result)
            for field in [
                'f_bsize', 'f_frsize', 'f_blocks', 'f_bfree', 'f_bavail',
                'f_files', 'f_ffree', 'f_favail', 'f_flag', 'f_namemax',
            ]:
                assert hasattr(st, field)

    def test_pickle(self):
        import pickle, os
        st = self.posix.stat(os.curdir)
        print(type(st).__module__)
        s = pickle.dumps(st)
        print(repr(s))
        new = pickle.loads(s)
        assert new == st
        assert type(new) is type(st)

    def test_open_exception(self):
        posix = self.posix
        try:
            posix.open('qowieuqwoeiu', 0, 0)
        except OSError as e:
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
                except OSError as e:
                    assert e.filename == 'qowieuqw/oeiu'
                else:
                    assert 0

    def test_chmod_exception(self):
        try:
            self.posix.chmod('qowieuqw/oeiu', 0)
        except OSError as e:
            assert e.filename == 'qowieuqw/oeiu'
        else:
            assert 0

    def test_chown_exception(self):
        if hasattr(self.posix, 'chown'):
            try:
                self.posix.chown('qowieuqw/oeiu', 0, 0)
            except OSError as e:
                assert e.filename == 'qowieuqw/oeiu'
            else:
                assert 0

    def test_utime_exception(self):
        for arg in [None, (0, 0)]:
            try:
                self.posix.utime('qowieuqw/oeiu', arg)
            except OSError as e:
                pass
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
        ex(self.posix.write, UNUSEDFD, b"x")
        ex(self.posix.close, UNUSEDFD)
        #UMPF cpython raises IOError ex(self.posix.ftruncate, UNUSEDFD, 123)
        ex(self.posix.fstat, UNUSEDFD)
        ex(self.posix.stat, "qweqwehello")
        # how can getcwd() raise?
        ex(self.posix.dup, UNUSEDFD)

    def test_getcwd(self):
        os, posix = self.os, self.posix
        assert isinstance(posix.getcwd(), str)
        cwdb = posix.getcwdb()
        os.chdir(self.esurrogate_dir)
        try:
            cwd = posix.getcwd()
            assert os.fsencode(cwd) == posix.getcwdb()
        finally:
            os.chdir(cwdb)

    def test_getcwdb(self):
        assert isinstance(self.posix.getcwdb(), bytes)

    def test_listdir(self):
        pdir = self.pdir
        posix = self.posix
        result = posix.listdir(pdir)
        result.sort()
        assert result == ['another_longer_file_name',
                          'file1',
                          'file2']

    def test_listdir_default(self):
        posix = self.posix
        assert posix.listdir() == posix.listdir('.') == posix.listdir(None)

    def test_listdir_bytes(self):
        import sys
        bytes_dir = self.bytes_dir
        posix = self.posix
        result = posix.listdir(bytes_dir)
        assert all(type(x) is bytes for x in result)
        assert b'somefile' in result
        expected = b'caf%E9' if sys.platform == 'darwin' else b'caf\xe9'
        assert expected in result

    def test_fdlistdir(self):
        posix = self.posix
        dirfd = posix.open('.', posix.O_RDONLY)
        lst1 = posix.listdir(dirfd)   # does not close dirfd
        lst2 = posix.listdir('.')
        assert lst1 == lst2
        #
        lst3 = posix.listdir(dirfd)   # rewinddir() was used
        assert lst3 == lst1
        posix.close(dirfd)

    def test_undecodable_filename(self):
        import sys
        posix = self.posix
        try:
            'caf\xe9'.encode(sys.getfilesystemencoding(), 'surrogateescape')
        except UnicodeEncodeError:
            pass # probably ascii
        else:
            assert posix.access('caf\xe9', posix.R_OK) is False
        assert posix.access(b'caf\xe9', posix.R_OK) is False
        assert posix.access('caf\udcc0', posix.R_OK) is False
        assert posix.access(b'caf\xc3', posix.R_OK) is False

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
            os.write(slave_fd, b'x\n')
            data = os.read(master_fd, 100)
            assert data.startswith(b'x')
            os.close(master_fd)
            os.close(slave_fd)

    if hasattr(__import__(os.name), "forkpty"):
        def test_forkpty(self):
            import sys
            if 'freebsd' in sys.platform:
                skip("hangs indifinitly on FreeBSD (also on CPython).")
            os = self.posix
            childpid, master_fd = os.forkpty()
            assert isinstance(childpid, int)
            assert isinstance(master_fd, int)
            if childpid == 0:
                data = os.read(0, 100)
                if data.startswith(b'abc'):
                    os._exit(42)
                else:
                    os._exit(43)
            os.write(master_fd, b'abc\n')
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
                except TypeError as t:
                    assert str(t) == "execv() arg 2 must be an iterable of strings"
                else:
                    py.test.fail("didn't raise")

        def test_execv_unicode(self):
            os = self.posix
            import sys
            if not hasattr(os, "fork"):
                skip("Need fork() to test execv()")
            try:
                output = "caf\xe9 \u1234\n".encode(sys.getfilesystemencoding())
            except UnicodeEncodeError:
                skip("encoding not good enough")
            pid = os.fork()
            if pid == 0:
                os.execv("/bin/sh", ["sh", "-c",
                                     "echo caf\xe9 \u1234 > onefile"])
            os.waitpid(pid, 0)
            assert open("onefile", "rb").read() == output
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
            try:
                output = "caf\xe9 \u1234".encode(sys.getfilesystemencoding())
            except UnicodeEncodeError:
                skip("encoding not good enough")
            t = ' abc\uDCFF'
            output += t.encode(sys.getfilesystemencoding(),
                               'surrogateescape')
            pid = os.fork()
            if pid == 0:
                os.execve("/bin/sh", ["sh", "-c",
                                      "echo caf\xe9 \u1234 $t > onefile"],
                          {'ddd': 'xxx', 't': t})
            os.waitpid(pid, 0)
            assert open("onefile", "rb").read() == output + b'\n'
            os.unlink("onefile")
        pass # <- please, inspect.getsource(), don't crash

    if hasattr(__import__(os.name), "spawnv"):
        def test_spawnv(self):
            os = self.posix
            import sys
            print(self.python)
            ret = os.spawnv(os.P_WAIT, self.python,
                            ['python', '-c', 'raise(SystemExit(42))'])
            assert ret == 42

    if hasattr(__import__(os.name), "spawnve"):
        def test_spawnve(self):
            os = self.posix
            env = {'PATH':os.environ['PATH'], 'FOOBAR': '42'}
            ret = os.spawnve(os.P_WAIT, self.python,
                             ['python', '-c',
                              "raise(SystemExit(int(__import__('os').environ['FOOBAR'])))"],
                             env)
            assert ret == 42

    def test_popen(self):
        os = self.os
        for i in range(5):
            stream = os.popen('echo 1')
            res = stream.read()
            assert res == '1\n'
            assert stream.close() is None

    def test_popen_with(self):
        os = self.os
        stream = os.popen('echo 1')
        with stream as fp:
            res = fp.read()
            assert res == '1\n'

    if hasattr(__import__(os.name), '_getfullpathname'):
        def test__getfullpathname(self):
            # nt specific
            posix = self.posix
            import os
            sysdrv = os.getenv("SystemDrive", "C:")
            # just see if it does anything
            path = sysdrv + 'hubber'
            assert os.sep in posix._getfullpathname(path)
            assert type(posix._getfullpathname(b'C:')) is bytes

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
        t1 = time()
        os.utime(path, (int(t1), int(t1)))
        assert int(os.stat(path).st_atime) == int(t1)

    def test_utime_raises(self):
        os = self.posix
        raises(TypeError, "os.utime('xxx', 3)")
        raises(OSError, "os.utime('somefilewhichihopewouldneverappearhere', None)")

    for name in rposix.WAIT_MACROS:
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
            assert res == (res.sysname, res.nodename,
                           res.release, res.version, res.machine)

    if hasattr(os, 'getuid'):
        def test_os_getuid(self):
            os = self.posix
            assert os.getuid() == self.getuid
            assert os.geteuid() == self.geteuid

    if hasattr(os, 'setuid'):
        @py.test.mark.skipif("sys.version_info < (2, 7, 4)")
        def test_os_setuid_error(self):
            os = self.posix
            raises(OverflowError, os.setuid, -2)
            raises(OverflowError, os.setuid, 2**32)
            raises(OSError, os.setuid, -1)

    if hasattr(os, 'getgid'):
        def test_os_getgid(self):
            os = self.posix
            assert os.getgid() == self.getgid

    if hasattr(os, 'getgroups'):
        def test_os_getgroups(self):
            os = self.posix
            assert os.getgroups() == self.getgroups

    if hasattr(os, 'setgroups'):
        def test_os_setgroups(self):
            os = self.posix
            raises(TypeError, os.setgroups, [2, 5, "hello"])
            try:
                os.setgroups(os.getgroups())
            except OSError:
                pass

    if hasattr(os, 'initgroups'):
        def test_os_initgroups(self):
            os = self.posix
            raises(OSError, os.initgroups, "crW2hTQC", 100)

    if hasattr(os, 'tcgetpgrp'):
        def test_os_tcgetpgrp(self):
            os = self.posix
            raises(OSError, os.tcgetpgrp, 9999)

    if hasattr(os, 'tcsetpgrp'):
        def test_os_tcsetpgrp(self):
            os = self.posix
            raises(OSError, os.tcsetpgrp, 9999, 1)

    if hasattr(os, 'getpgid'):
        def test_os_getpgid(self):
            os = self.posix
            assert os.getpgid(os.getpid()) == self.getpgid
            raises(OSError, os.getpgid, 1234567)

    if hasattr(os, 'setgid'):
        @py.test.mark.skipif("sys.version_info < (2, 7, 4)")
        def test_os_setgid_error(self):
            os = self.posix
            raises(OverflowError, os.setgid, -2)
            raises(OverflowError, os.setgid, 2**32)
            raises(OSError, os.setgid, -1)
            raises(OSError, os.setgid, 2**32-1)

    if hasattr(os, 'getsid'):
        def test_os_getsid(self):
            os = self.posix
            assert os.getsid(0) == self.getsid0
            raises(OSError, os.getsid, -100000)

    if hasattr(os, 'getresuid'):
        def test_os_getresuid(self):
            os = self.posix
            res = os.getresuid()
            assert len(res) == 3

    if hasattr(os, 'getresgid'):
        def test_os_getresgid(self):
            os = self.posix
            res = os.getresgid()
            assert len(res) == 3

    if hasattr(os, 'setresuid'):
        def test_os_setresuid(self):
            os = self.posix
            a, b, c = os.getresuid()
            os.setresuid(a, b, c)

    if hasattr(os, 'setresgid'):
        def test_os_setresgid(self):
            os = self.posix
            a, b, c = os.getresgid()
            os.setresgid(a, b, c)

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

    if hasattr(os, 'pathconf'):
        def test_os_pathconf(self):
            os = self.posix
            assert os.pathconf("/tmp", "PC_NAME_MAX") >= 31
            # Linux: the following gets 'No such file or directory'
            raises(OSError, os.pathconf, "", "PC_PIPE_BUF")
            raises(ValueError, os.pathconf, "/tmp", "##")

    if hasattr(os, 'confstr'):
        def test_os_confstr(self):
            os = self.posix
            assert os.confstr(self.confstr_value) == self.confstr_result
            assert os.confstr(self.confstr_name) == self.confstr_result
            assert os.confstr_names[self.confstr_name] == self.confstr_value

        def test_os_confstr_error(self):
            os = self.posix
            raises(ValueError, os.confstr, "!@#$%!#$!@#")

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
            raises((ValueError, OverflowError), os.major, -1)

    if hasattr(os, 'fsync'):
        def test_fsync(self):
            os = self.posix
            f = open(self.path2, "w")
            try:
                fd = f.fileno()
                os.fsync(fd)
                os.fsync(f)     # <- should also work with a file, or anything
            finally:            #    with a fileno() method
                f.close()
            try:
                # May not raise anything with a buggy libc (or eatmydata)
                os.fsync(fd)
            except OSError:
                pass
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
            try:
                # May not raise anything with a buggy libc (or eatmydata)
                os.fdatasync(fd)
            except OSError:
                pass
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
        fd = os.open(self.path2 + 'test_largefile',
                     os.O_RDWR | os.O_CREAT, 0o666)
        os.ftruncate(fd, 10000000000)
        res = os.lseek(fd, 9900000000, 0)
        assert res == 9900000000
        res = os.lseek(fd, -5000000000, 1)
        assert res == 4900000000
        res = os.lseek(fd, -5200000000, 2)
        assert res == 4800000000
        os.close(fd)

        st = os.stat(self.path2 + 'test_largefile')
        assert st.st_size == 10000000000
    test_largefile.need_sparse_files = True

    def test_write_buffer(self):
        os = self.posix
        fd = os.open(self.path2 + 'test_write_buffer',
                     os.O_RDWR | os.O_CREAT, 0o666)
        def writeall(s):
            while s:
                count = os.write(fd, s)
                assert count > 0
                s = s[count:]
        writeall(b'hello, ')
        writeall(memoryview(b'world!\n'))
        res = os.lseek(fd, 0, 0)
        assert res == 0
        data = b''
        while True:
            s = os.read(fd, 100)
            if not s:
                break
            data += s
        assert data == b'hello, world!\n'
        os.close(fd)

    def test_write_unicode(self):
        os = self.posix
        fd = os.open(self.path2 + 'test_write_unicode',
                     os.O_RDWR | os.O_CREAT, 0o666)
        raises(TypeError, os.write, fd, 'X')
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
        fds = [os.open(self.path + str(i), os.O_CREAT|os.O_WRONLY, 0o777)
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

    if hasattr(os, 'fchown'):
        def test_fchown(self):
            os = self.posix
            f = open(self.path, "w")
            os.fchown(f.fileno(), os.getuid(), os.getgid())
            f.close()

    if hasattr(os, 'chmod'):
        def test_chmod(self):
            import sys
            os = self.posix
            os.unlink(self.path)
            raises(OSError, os.chmod, self.path, 0o600)
            f = open(self.path, "w")
            f.write("this is a test")
            f.close()
            if sys.platform == 'win32':
                os.chmod(self.path, 0o400)
                assert (os.stat(self.path).st_mode & 0o600) == 0o400
            else:
                os.chmod(self.path, 0o200)
                assert (os.stat(self.path).st_mode & 0o777) == 0o200

    if hasattr(os, 'fchmod'):
        def test_fchmod(self):
            os = self.posix
            f = open(self.path, "w")
            os.fchmod(f.fileno(), 0o200)
            assert (os.fstat(f.fileno()).st_mode & 0o777) == 0o200
            f.close()
            assert (os.stat(self.path).st_mode & 0o777) == 0o200

    if hasattr(os, 'mkfifo'):
        def test_mkfifo(self):
            os = self.posix
            os.mkfifo(self.path2 + 'test_mkfifo', 0o666)
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
            except OSError as e:
                skip("os.mknod(): got %r" % (e,))
            st = os.lstat(self.path2 + 'test_mknod-1')
            assert stat.S_ISREG(st.st_mode)
            # os.mknod() with S_IFIFO
            os.mknod(self.path2 + 'test_mknod-2', 0o600 | stat.S_IFIFO)
            st = os.lstat(self.path2 + 'test_mknod-2')
            assert stat.S_ISFIFO(st.st_mode)

        def test_mknod_with_ifchr(self):
            # os.mknod() with S_IFCHR
            # -- usually requires root priviledges --
            os = self.posix
            if hasattr(os.lstat('.'), 'st_rdev'):
                import stat
                try:
                    os.mknod(self.path2 + 'test_mknod-3', 0o600 | stat.S_IFCHR,
                             0x105)
                except OSError as e:
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
            bytes_dir = self.bytes_dir
            if bytes_dir is None:
                skip("encoding not good enough")
            dest = bytes_dir + b"/file.txt"
            posix.symlink(bytes_dir + b"/somefile", dest)
            with open(dest) as f:
                data = f.read()
                assert data == "who cares?"

        # XXX skip test if dir_fd is unsupported
        def test_symlink_fd(self):
            posix = self.posix
            bytes_dir = self.bytes_dir
            f = posix.open(bytes_dir, posix.O_RDONLY)
            try:
                posix.symlink('somefile', 'somelink', dir_fd=f)
                assert (posix.readlink(bytes_dir + '/somelink'.encode()) ==
                        'somefile'.encode())
            finally:
                posix.close(f)
                posix.unlink(bytes_dir + '/somelink'.encode())

    if hasattr(os, 'ftruncate'):
        def test_truncate(self):
            posix = self.posix
            dest = self.path2

            def mkfile(dest, size=4):
                with open(dest, 'wb') as f:
                    f.write(b'd' * size)

            # Check invalid inputs
            mkfile(dest)
            raises(OSError, posix.truncate, dest, -1)
            with open(dest, 'rb') as f:  # f is read-only so cannot be truncated
                raises(OSError, posix.truncate, f.fileno(), 1)
            raises(TypeError, posix.truncate, dest, None)
            raises(TypeError, posix.truncate, None, None)

            # Truncate via file descriptor
            mkfile(dest)
            with open(dest, 'wb') as f:
                posix.truncate(f.fileno(), 1)
            assert 1 == posix.stat(dest).st_size

            # Truncate via filename
            mkfile(dest)
            posix.truncate(dest, 1)
            assert 1 == posix.stat(dest).st_size

    try:
        os.getlogin()
    except (AttributeError, OSError):
        pass
    else:
        def test_getlogin(self):
            assert isinstance(self.posix.getlogin(), str)
            # How else could we test that getlogin is properly
            # working?

    def test_has_kill(self):
        import os
        assert hasattr(os, 'kill')

    def test_pipe_flush(self):
        ffd, gfd = self.posix.pipe()
        f = self.os.fdopen(ffd, 'r')
        g = self.os.fdopen(gfd, 'w')
        g.write('he')
        g.flush()
        x = f.read(1)
        assert x == 'h'
        f.flush()
        x = f.read(1)
        assert x == 'e'

    def test_urandom(self):
        os = self.posix
        s = os.urandom(5)
        assert isinstance(s, bytes)
        assert len(s) == 5
        for x in range(50):
            if s != os.urandom(5):
                break
        else:
            assert False, "urandom() always returns the same string"
            # Or very unlucky

    if hasattr(os, 'startfile'):
        def test_startfile(self):
            if not self.runappdirect:
                skip("should not try to import cffi at app-level")
            startfile = self.posix.startfile
            for t1 in [str, unicode]:
                for t2 in [str, unicode]:
                    e = raises(WindowsError, startfile, t1("\\"), t2("close"))
                    assert e.value.args[0] == 1155
                    assert e.value.args[1] == (
                        "No application is associated with the "
                        "specified file for this operation")
                    if len(e.value.args) > 2:
                        assert e.value.args[2] == t1("\\")
            #
            e = raises(WindowsError, startfile, "\\foo\\bar\\baz")
            assert e.value.args[0] == 2
            assert e.value.args[1] == (
                "The system cannot find the file specified")
            if len(e.value.args) > 2:
                assert e.value.args[2] == "\\foo\\bar\\baz"

    def test_device_encoding(self):
        import sys
        encoding = self.posix.device_encoding(sys.stdout.fileno())
        # just ensure it returns something reasonable
        assert encoding is None or type(encoding) is str

    if os.name == 'nt':
        def test__getfileinformation(self):
            import os
            path = os.path.join(self.pdir, 'file1')
            with open(path) as fp:
                info = self.posix._getfileinformation(fp.fileno())
            assert len(info) == 3
            assert all(isinstance(obj, int) for obj in info)

        def test__getfinalpathname(self):
            import os
            path = os.path.join(self.pdir, 'file1')
            try:
                result = self.posix._getfinalpathname(path)
            except NotImplementedError:
                skip("_getfinalpathname not supported on this platform")
            assert os.path.exists(result)

    def test_rtld_constants(self):
        # check presence of major RTLD_* constants
        self.posix.RTLD_LAZY
        self.posix.RTLD_NOW
        self.posix.RTLD_GLOBAL
        self.posix.RTLD_LOCAL


class AppTestEnvironment(object):
    def setup_class(cls):
        cls.w_path = space.wrap(str(path))

    def test_environ(self):
        import sys, posix
        environ = posix.environ
        item_type = str if sys.platform.startswith('win') else bytes
        for k, v in environ.items():
            assert type(k) is item_type
            assert type(v) is item_type
        name = next(iter(environ))
        assert environ[name] is not None
        del environ[name]
        raises(KeyError, lambda: environ[name])

    @py.test.mark.dont_track_allocations('putenv intentionally keeps strings alive')
    def test_environ_nonascii(self):
        import sys, os
        name, value = 'PYPY_TEST_日本', 'foobar日本'
        if not sys.platform == 'win32':
            fsencoding = sys.getfilesystemencoding()
            for s in name, value:
                try:
                    s.encode(fsencoding, 'surrogateescape')
                except UnicodeEncodeError:
                    skip("Requires %s.encode(sys.getfilesystemencoding(), "
                         "'surogateescape') to succeed (or win32)" % ascii(s))

        os.environ[name] = value
        assert os.environ[name] == value
        assert os.getenv(name) == value
        del os.environ[name]
        assert os.environ.get(name) is None
        assert os.getenv(name) is None

    if hasattr(__import__(os.name), "unsetenv"):
        def test_unsetenv_nonexisting(self):
            import os
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

@py.test.fixture
def check_fsencoding(space, pytestconfig):
    if pytestconfig.getvalue('runappdirect'):
        fsencoding = sys.getfilesystemencoding()
    else:
        fsencoding = space.sys.filesystemencoding
    try:
        u"ą".encode(fsencoding)
    except UnicodeEncodeError:
        py.test.skip("encoding not good enough")

@py.test.mark.usefixtures('check_fsencoding')
class AppTestPosixUnicode:
    def test_stat_unicode(self):
        # test that passing unicode would not raise UnicodeDecodeError
        import posix
        try:
            posix.stat(u"ą")
        except OSError:
            pass

    def test_open_unicode(self):
        # Ensure passing unicode doesn't raise UnicodeEncodeError
        import posix
        try:
            posix.open(u"ą", posix.O_WRONLY)
        except OSError:
            pass

    def test_remove_unicode(self):
        # See 2 above ;)
        import posix
        try:
            posix.remove(u"ą")
        except OSError:
            pass


class AppTestUnicodeFilename:
    def setup_class(cls):
        ufilename = (unicode(udir.join('test_unicode_filename_')) +
                     '\u65e5\u672c.txt') # "Japan"
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
        assert content == b"test"


class AppTestFdVariants:
    # Tests variant functions which also accept file descriptors,
    # dir_fd and follow_symlinks.
    def test_have_functions(self):
        import os
        assert os.stat in os.supports_fd  # fstat() is supported everywhere
        if os.name != 'nt':
            assert os.chdir in os.supports_fd  # fchdir()
        else:
            assert os.chdir not in os.supports_fd
        if os.name == 'posix':
            assert os.open in os.supports_dir_fd  # openat()

