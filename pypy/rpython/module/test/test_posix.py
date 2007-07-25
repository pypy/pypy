import py
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.tool.udir import udir
import os
exec 'import %s as posix' % os.name

def setup_module(module):
    testf = udir.join('test.txt')
    module.path = testf.strpath

class BaseTestPosix(BaseRtypingTest):

    def setup_method(self, meth):
        # prepare/restore the file before each test
        testfile = open(path, 'wb')
        testfile.write('This is a test')
        testfile.close()

    def test_open(self):
        def f():
            ff = posix.open(path,posix.O_RDONLY,0777)
            return ff
        func = self.interpret(f,[])
        assert type(func) == int

    def test_fstat(self):
        def fo(fi):
            g = posix.fstat(fi)
            return g
        fi = os.open(path,os.O_RDONLY,0777)
        func = self.interpret(fo,[fi])
        stat = os.fstat(fi)
        for i in range(len(stat)):
            stat0 = getattr(func, 'item%d' % i)
            assert stat0 == stat[i]

    def test_lseek(self):
        def f(fi,pos):
            posix.lseek(fi,pos,0)
        fi = os.open(path,os.O_RDONLY,0777)
        func = self.interpret(f,[fi,5]) 
        res = os.read(fi,2)
        assert res =='is'

    def test_isatty(self):
        def f(fi):
            posix.isatty(fi)
        fi = os.open(path,os.O_RDONLY,0777)
        func = self.interpret(f,[fi])
        assert not func
        os.close(fi)
        func = self.interpret(f,[fi])
        assert not func

    def test_getcwd(self):
        def f():
            return posix.getcwd()
        res = self.interpret(f,[])
        cwd = os.getcwd()
        #print res.chars,cwd
        assert self.ll_to_string(res) == cwd

    def test_write(self):
        def f(fi):
            text = 'This is a test'
            return posix.write(fi,text)
        fi = os.open(path,os.O_WRONLY,0777)
        text = 'This is a test'
        func = self.interpret(f,[fi])
        os.close(fi)
        fi = os.open(path,os.O_RDONLY,0777)
        res = os.read(fi,20)
        assert res == text

    def test_read(self):
        def f(fi,len):
            return posix.read(fi,len)
        fi = os.open(path,os.O_WRONLY,0777)
        text = 'This is a test'
        os.write(fi,text)
        os.close(fi)
        fi = os.open(path,os.O_RDONLY,0777)
        res = self.interpret(f,[fi,20])
        assert self.ll_to_string(res) == text

    def test_close(self):
        def f(fi):
            return posix.close(fi)
        fi = os.open(path,os.O_WRONLY,0777)
        text = 'This is a test'
        os.write(fi,text)
        res = self.interpret(f,[fi])
        raises( OSError, os.fstat, fi)

    def test_ftruncate(self):
        def f(fi,len):
            posix.ftruncate(fi,len)
        fi = os.open(path,os.O_RDWR,0777)
        func = self.interpret(f,[fi,6]) 
        assert os.fstat(fi).st_size == 6

    def test_getuid(self):
        def f():
            return os.getuid()
        assert self.interpret(f, []) == f()

if not hasattr(os, 'ftruncate'):
    del BaseTestPosix.test_ftruncate

class TestLLtype(BaseTestPosix, LLRtypeMixin):
    if hasattr(os, 'uname'):
        def test_os_uname(self):
            py.test.skip("Cannot do it (yet) because ll2ctypes cannot handle str -> fixedsizearray")
            #from pypy.translator.c.test.test_genc import compile
            for num in range(5):
                def fun():
                    return os.uname()[num]
                #fn = compile(fun, [])
                assert self.interpret(fun, []) == os.uname()[num]

class TestOOtype(BaseTestPosix, OORtypeMixin):
    pass

