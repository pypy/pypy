import os, math
import errno
import stat
from py.builtin import sorted
from pypy.tool import udir
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin
from pypy.rpython.module.test.test_ll_time import BaseTestTime as llBaseTestTime

class BaseTestBuiltin(BaseTestRbuiltin):

    def test_os_flags(self):
        from pypy.translator.oosupport.support import NT_OS
        def fn():
            return os.O_CREAT
        assert self.interpret(fn, []) == NT_OS['O_CREAT']

    def test_os_read_hibytes(self):
        """
        Test that we read in characters with the high bit set correctly
        This can be a problem on JVM or CLI, where we use unicode strings to
        encode byte arrays!
        """
        tmpfile = str(udir.udir.join("os_read_hibytes.txt"))
        def chrs2int(b):
            assert len(b) == 4
            first = ord(b[0]) # big endian
            if first & 0x80 != 0:
                first = first - 0x100
            return first << 24 | ord(b[1]) << 16 | ord(b[2]) << 8 | ord(b[3])
        def fn():
            fd = os.open(tmpfile, os.O_RDONLY|os.O_BINARY, 0666)
            res = os.read(fd, 4)
            os.close(fd)
            return chrs2int(res)
        f = file(tmpfile, 'w')
        f.write("".join([chr(x) for x in [0x06, 0x64, 0x90, 0x00]]))
        f.close()
        assert self.interpret(fn, []) == fn()
        
    def test_os_read_binary_crlf(self):
        tmpfile = str(udir.udir.join("os_read_test"))
        def fn(flag):
            if flag:
                fd = os.open(tmpfile, os.O_RDONLY|os.O_BINARY, 0666)
            else:
                fd = os.open(tmpfile, os.O_RDONLY, 0666)
            res = os.read(fd, 4096)
            os.close(fd)
            return res
        f = file(tmpfile, 'w')
        f.write('Hello\nWorld')
        f.close()
        res = self.ll_to_string(self.interpret(fn, [True]))
        assert res == file(tmpfile, 'rb').read()
        res = self.ll_to_string(self.interpret(fn, [False]))
        assert res == file(tmpfile, 'r').read()

    def test_os_dup_oo(self):
        tmpdir = str(udir.udir.join("os_dup_oo"))
        def fn():
            fd = os.open(tmpdir, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0777)
            os.write(fd, "hello world")
            fd2 = os.dup(fd)
            os.write(fd2, " (dupped)")
            os.close(fd)
            try:
                os.write(fd2, " (uh oh)")
            except OSError, e:
                return e.errno
            return -1
        assert self.interpret(fn, []) == 5 # EIO
        assert file(tmpdir).read() == 'hello world (dupped)'

    # the following tests can't be executed with gencli because they
    # returns file descriptors, and cli code is executed in another
    # process. Instead of those, there are new tests that opens and
    # write to a file all in the same process.
    def test_os_dup(self):
        pass
    def test_os_write(self):
        pass
    def test_os_write_single_char(self):
        pass
    def test_os_open(self):
        pass

    def test_os_open_write(self):
        tmpdir = str(udir.udir.join("os_write_test"))
        def fn():
            fd = os.open(tmpdir, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0777)            
            os.write(fd, "hello world")
            os.close(fd)
        self.interpret(fn, [])
        assert file(tmpdir).read() == 'hello world'

    def test_os_write_magic(self):
        MAGIC = 62061 | (ord('\r')<<16) | (ord('\n')<<24)
        tmpfile = str(udir.udir.join("os_write_test"))
        def long2str(x):
            a = x & 0xff
            x >>= 8
            b = x & 0xff
            x >>= 8
            c = x & 0xff
            x >>= 8
            d = x & 0xff
            return chr(a) + chr(b) + chr(c) + chr(d)
        def fn(magic):
            fd = os.open(tmpfile, os.O_BINARY|os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0777)
            os.write(fd, long2str(magic))
            os.close(fd)
        self.interpret(fn, [MAGIC])
        contents = file(tmpfile, 'rb').read()
        assert contents == long2str(MAGIC)

    def test_os_stat(self):
        def fn(flag):
            if flag:
                return os.stat('.')[0]
            else:
                return os.stat('.').st_mode
        mode = self.interpret(fn, [0])
        assert stat.S_ISDIR(mode)
        mode = self.interpret(fn, [1])
        assert stat.S_ISDIR(mode)
        
    ACCESS_FLAGS = [os.F_OK, os.R_OK, os.W_OK, os.X_OK]
    
    def test_os_access(self):
        def create_fn(filenm):
            return lambda flag: os.access(filenm, flag)
        def try_file(filenm):
            for flag in self.ACCESS_FLAGS:
                print filenm, flag
                fn = create_fn(filenm)
                act = self.interpret(fn, [flag])
                assert act == fn(flag)
        assert not os.access('some_file_that_does_not_exist', os.F_OK) # shouldn't exist
        try_file('some_file_that_does_not_exist')
        try_file('.')
        
        open('some_file_that_DID_not_exist', 'w').close()
        os.chmod('some_file_that_DID_not_exist', 0)
        assert os.access('some_file_that_DID_not_exist', os.F_OK) # should exist now
        assert not os.access('some_file_that_DID_not_exist', os.W_OK) # should not be writable
        try_file('some_file_that_DID_not_exist')
        os.remove('some_file_that_DID_not_exist')

    #def test_os_access_allowed(self):
    #    def fn(flag):
    #        return os.access('.', flag)
    #    for flag in self.ACCESS_FLAGS:
    #        print flag
    #        act = self.interpret(fn, [flag])
    #        assert act == fn(flag)
    #
    #def test_os_access_denied(self):
    #    
    #    def fn(flag):
    #        return os.access('/', flag)
    #    for flag in self.ACCESS_FLAGS:
    #        act = self.interpret(fn, [flag])
    #        assert act == fn(flag)

    def test_os_stat_oserror(self):
        def fn():
            return os.stat('/directory/unlikely/to/exists')[0]
        self.interpret_raises(OSError, fn, [])

    def test_os_strerror(self):
        def fn():
            return os.strerror(errno.ENOTDIR)
        res = self.ll_to_string(self.interpret(fn, []))
        # XXX assert something about res

    def test_environ(self):
        def fn():
            os.environ['PYPY_TEST_ENVIRON'] = '42'
            return os.environ['PYPY_TEST_ENVIRON']
        assert self.interpret(fn, []) == '42'

    def test_environ_items(self):
        def fn():
            env = os.environ.items()
            env2 = []
            for key in os.environ.keys():
                env2.append((key, os.environ[key]))
            assert env == env2
        self.interpret(fn, [])

    def test_os_listdir(self):
        def fn():
            return os.listdir('.')
        res = self.ll_to_list(self.interpret(fn, []))
        res = [self.ll_to_string(s) for s in res]
        res.sort()
        assert res == sorted(os.listdir('.'))

    # XXX: remember to test ll_os_readlink and ll_os_pipe as soon as
    # they are implemented

    def test_math_modf(self):
        def fn(x):
            return math.modf(x)
        for x in (.5, 1, 1.5):
            for y in (1, -1):
                act_res = self.interpret(fn, [x*y])
                exp_res = math.modf(x*y)
                assert act_res.item0 == exp_res[0]
                assert act_res.item1 == exp_res[1]


    def test_rffi_primitive(self):
        from pypy.rpython.lltypesystem import rffi, lltype
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        eci = ExternalCompilationInfo(
            includes = ['ctype.h']
        )
        tolower = rffi.llexternal('tolower', [lltype.Signed], lltype.Signed,
                                  compilation_info=eci,
                                  oo_primitive='tolower')
        assert tolower._ptr._obj.oo_primitive == 'tolower'

        def fn(n):
            return tolower(n)
        res = self.interpret(fn, [ord('A')])
        assert res == ord('a')


class BaseTestTime(llBaseTestTime):

    def test_time_clock(self):
        import time
        def f():
            return time.clock(), time.clock(), time.clock()
        res = self.interpret(f, [])
        t1, t2, t3 = self.ll_to_tuple(res)
        assert 0 <= t1 <= t2 <= t3
