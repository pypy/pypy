import py
import sys, os, time
import struct
import subprocess

from pypy.rpython.lltypesystem import rffi
from pypy.translator.interactive import Translation
from pypy.translator.sandbox.sandlib import read_message, write_message
from pypy.translator.sandbox.sandlib import write_exception

def expect(f, g, fnname, args, result, resulttype=None):
    msg = read_message(f, timeout=10.0)
    assert msg == fnname
    msg = read_message(f, timeout=10.0)
    assert msg == args
    if isinstance(result, Exception):
        write_exception(g, result)
    else:
        write_message(g, 0)
        write_message(g, result, resulttype)
        g.flush()

def compile(f, gc='ref'):
    t = Translation(f, backend='c', standalone=True, sandbox=True, gc=gc)
    return str(t.compile())


def test_open_dup():
    def entry_point(argv):
        fd = os.open("/tmp/foobar", os.O_RDONLY, 0777)
        assert fd == 77
        fd2 = os.dup(fd)
        assert fd2 == 78
        return 0

    exe = compile(entry_point)
    g, f = os.popen2(exe, "t", 0)
    expect(f, g, "ll_os.ll_os_open", ("/tmp/foobar", os.O_RDONLY, 0777), 77)
    expect(f, g, "ll_os.ll_os_dup",  (77,), 78)
    g.close()
    tail = f.read()
    f.close()
    assert tail == ""

def test_read_write():
    def entry_point(argv):
        fd = os.open("/tmp/foobar", os.O_RDONLY, 0777)
        assert fd == 77
        res = os.read(fd, 123)
        assert res == "he\x00llo"
        count = os.write(fd, "world\x00!\x00")
        assert count == 42
        os.close(fd)
        return 0

    exe = compile(entry_point)
    g, f = os.popen2(exe, "t", 0)
    expect(f, g, "ll_os.ll_os_open",  ("/tmp/foobar", os.O_RDONLY, 0777), 77)
    expect(f, g, "ll_os.ll_os_read",  (77, 123), "he\x00llo")
    expect(f, g, "ll_os.ll_os_write", (77, "world\x00!\x00"), 42)
    expect(f, g, "ll_os.ll_os_close", (77,), None)
    g.close()
    tail = f.read()
    f.close()
    assert tail == ""

def test_dup2_access():
    def entry_point(argv):
        os.dup2(34, 56)
        y = os.access("spam", 77)
        return 1 - y

    exe = compile(entry_point)
    g, f = os.popen2(exe, "t", 0)
    expect(f, g, "ll_os.ll_os_dup2",   (34, 56), None)
    expect(f, g, "ll_os.ll_os_access", ("spam", 77), True)
    g.close()
    tail = f.read()
    f.close()
    assert tail == ""

def test_stat_ftruncate():
    from pypy.translator.sandbox.sandlib import RESULTTYPE_STATRESULT
    from pypy.rlib.rarithmetic import r_longlong
    r0x12380000007 = r_longlong(0x12380000007)

    def entry_point(argv):
        st = os.stat("somewhere")
        os.ftruncate(st.st_mode, st.st_size)  # nonsense, just to see outside
        return 0

    exe = compile(entry_point)
    g, f = os.popen2(exe, "t", 0)
    st = os.stat_result((55, 0, 0, 0, 0, 0, 0x12380000007, 0, 0, 0))
    expect(f, g, "ll_os.ll_os_stat", ("somewhere",), st,
           resulttype = RESULTTYPE_STATRESULT)
    expect(f, g, "ll_os.ll_os_ftruncate", (55, 0x12380000007), None)
    g.close()
    tail = f.read()
    f.close()
    assert tail == ""

def test_time():
    def entry_point(argv):
        t = time.time()
        os.dup(int(t*1000))
        return 0

    exe = compile(entry_point)
    g, f = os.popen2(exe, "t", 0)
    expect(f, g, "ll_time.ll_time_time", (), 3.141592)
    expect(f, g, "ll_os.ll_os_dup", (3141,), 3)
    g.close()
    tail = f.read()
    f.close()
    assert tail == ""

def test_oserror():
    def entry_point(argv):
        try:
            os.stat("somewhere")
        except OSError, e:
            os.close(e.errno)    # nonsense, just to see outside
        return 0

    exe = compile(entry_point)
    g, f = os.popen2(exe, "t", 0)
    expect(f, g, "ll_os.ll_os_stat", ("somewhere",), OSError(6321, "egg"))
    expect(f, g, "ll_os.ll_os_close", (6321,), None)
    g.close()
    tail = f.read()
    f.close()
    assert tail == ""

def test_hybrid_gc():
    def entry_point(argv):
        l = []
        for i in range(int(argv[1])):
            l.append("x" * int(argv[2]))
        return int(len(l) > 1000)

    exe = compile(entry_point, gc='hybrid')
    pipe = subprocess.Popen([exe, '10', '10000'], stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    g = pipe.stdin
    f = pipe.stdout
    expect(f, g, "ll_os.ll_os_getenv", ("PYPY_GENERATIONGC_NURSERY",), None)
    #if sys.platform.startswith('linux'):
    #    expect(f, g, "ll_os.ll_os_open", ("/proc/cpuinfo", 0, 420),
    #           OSError(5232, "xyz"))
    expect(f, g, "ll_os.ll_os_getenv", ("PYPY_GC_DEBUG",), None)
    g.close()
    tail = f.read()
    f.close()
    assert tail == ""
    rescode = pipe.wait()
    assert rescode == 0

def test_segfault_1():
    class A:
        def __init__(self, m):
            self.m = m
    def g(m):
        if m < 10:
            return None
        return A(m)
    def entry_point(argv):
        x = g(len(argv))
        return int(x.m)

    exe = compile(entry_point)
    g, f, e = os.popen3(exe, "t", 0)
    g.close()
    tail = f.read()
    f.close()
    assert tail == ""
    errors = e.read()
    e.close()
    assert 'Invalid RPython operation' in errors

def test_segfault_2():
    py.test.skip("hum, this is one example, but we need to be very careful")
    class Base:
        pass
    class A(Base):
        def __init__(self, m):
            self.m = m
        def getm(self):
            return self.m
    class B(Base):
        def __init__(self, a):
            self.a = a
    def g(m):
        a = A(m)
        if m < 10:
            a = B(a)
        return a
    def entry_point(argv):
        x = g(len(argv))
        os.write(2, str(x.getm()))
        return 0

    exe = compile(entry_point)
    g, f, e = os.popen3(exe, "t", 0)
    g.close()
    tail = f.read(23)
    f.close()
    assert tail == ""    # and not ll_os.ll_os_write
    errors = e.read()
    e.close()
    assert '...think what kind of errors to get...' in errors

def test_safe_alloc():
    from pypy.rlib.rmmap import alloc, free

    def entry_point(argv):
        one = alloc(1024)
        free(one, 1024)
        return 0

    exe = compile(entry_point)
    pipe = subprocess.Popen([exe], stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    g = pipe.stdin
    f = pipe.stdout
    g.close()
    tail = f.read()
    f.close()
    assert tail == ""
    rescode = pipe.wait()
    assert rescode == 0

def test_unsafe_mmap():
    py.test.skip("Since this stuff is unimplemented, it won't work anyway "
                 "however, the day it starts working, it should pass test")
    from pypy.rlib.rmmap import mmap

    def entry_point(argv):
        try:
            res = mmap(0, 1024)
        except OSError:
            return 0
        return 1

    exe = compile(entry_point)
    pipe = subprocess.Popen([exe], stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    g = pipe.stdin
    f = pipe.stdout
    expect(f, g, "mmap", ARGS, OSError(1, "xyz"))
    g.close()
    tail = f.read()
    f.close()
    assert tail == ""
    rescode = pipe.wait()
    assert rescode == 0

class TestPrintedResults:

    def run(self, entry_point, args, expected):
        exe = compile(entry_point)
        from pypy.translator.sandbox.sandlib import SimpleIOSandboxedProc
        proc = SimpleIOSandboxedProc([exe] + args)
        output, error = proc.communicate()
        assert error == ''
        assert output == expected

    def test_safefuncs(self):
        import math
        def entry_point(argv):
            a = float(argv[1])
            print int(math.floor(a - 0.2)),
            print int(math.ceil(a)),
            print int(100.0 * math.sin(a)),
            mantissa, exponent = math.frexp(a)
            print int(100.0 * mantissa), exponent,
            fracpart, intpart = math.modf(a)
            print int(100.0 * fracpart), int(intpart),
            print
            return 0
        self.run(entry_point, ["3.011"], "2 4 13 75 2 1 3\n")

    def test_safefuncs_exception(self):
        import math
        def entry_point(argv):
            a = float(argv[1])
            x = math.log(a)
            print int(x * 100.0)
            try:
                math.log(-a)
            except ValueError:
                print 'as expected, got a ValueError'
            else:
                print 'did not get a ValueError!'
            return 0
        self.run(entry_point, ["3.011"], "110\nas expected, got a ValueError\n")

    def test_os_path_safe(self):
        def entry_point(argv):
            print os.path.join('tmp', argv[1])
            return 0
        self.run(entry_point, ["spam"], os.path.join("tmp", "spam")+'\n')
