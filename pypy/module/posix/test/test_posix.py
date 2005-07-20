from pypy.rpython.test.test_llinterp import interpret
from pypy.tool.udir import udir 
import os, posix

def setup_module(module):
    testf = udir.join('test.txt')
    testfile = testf.open('w')
    testfile.write('This is a test')
    testfile.close()
    module.path = testf.strpath

def test_open():
    def f():
        ff = posix.open(path,posix.O_RDONLY,0777)
        return ff
    func = interpret(f,[])
    assert type(func) == int

def test_dup():
    def ff(fi):
        g = posix.dup(fi)
        return g
    fi = os.open(path,os.O_RDONLY,0755)
    g = interpret(ff,[fi])
    assert os.fstat(g) == os.fstat(fi)
    
def test_fstat():
    def fo(fi):
        g = posix.fstat(fi)
        return g
    fi = os.open(path,os.O_RDONLY,0777)
    func = interpret(fo,[fi])
    stat = os.fstat(fi)
    for i in range(len(stat)):
        stat0 = getattr(func, 'item%d' % i)
        assert stat0 == stat[i]
            
def test_lseek():
    def f(fi,pos):
        posix.lseek(fi,pos,0)
    fi = os.open(path,os.O_RDONLY,0777)
    func = interpret(f,[fi,5]) 
    res = os.read(fi,2)
    assert res =='is'

def test_isatty():
    def f(fi):
        posix.isatty(fi)
    fi = os.open(path,os.O_RDONLY,0777)
    func = interpret(f,[fi])
    assert not func
    os.close(fi)
    func = interpret(f,[fi])
    assert not func

def test_getcwd():
    def f():
        return posix.getcwd()
    res = interpret(f,[])
    cwd = os.getcwd()
    print res.chars,cwd
    assert ''.join([x for x in res.chars]) == cwd

def test_write():
    def f(fi):
        text = 'This is a test'
        return posix.write(fi,text)
    fi = os.open(path,os.O_WRONLY,0777)
    text = 'This is a test'
    func = interpret(f,[fi])
    os.close(fi)
    fi = os.open(path,os.O_RDONLY,0777)
    res = os.read(fi,20)
    assert res == text

def test_read():
    def f(fi,len):
        return posix.read(fi,len)
    fi = os.open(path,os.O_WRONLY,0777)
    text = 'This is a test'
    os.write(fi,text)
    os.close(fi)
    fi = os.open(path,os.O_RDONLY,0777)
    res = interpret(f,[fi,20])
    assert ''.join([x for x in res.chars]) == text

def test_close():
    def f(fi):
        return posix.close(fi)
    fi = os.open(path,os.O_WRONLY,0777)
    text = 'This is a test'
    os.write(fi,text)
    res = interpret(f,[fi])
    raises( OSError(), os.fstat(fi))

def test_ftruncate():
    def f(fi,len):
        posix.ftruncate(fi,len)
    fi = os.open(path,os.O_RDWR,0777)
    func = interpret(f,[fi,6]) 
    assert os.fstat(fi).st_size == 6
    
