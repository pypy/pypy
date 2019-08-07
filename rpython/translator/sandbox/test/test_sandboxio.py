import py
import sys, os, time, errno, select, math
import struct
import subprocess
import signal

from rpython.rtyper.lltypesystem import rffi
from rpython.translator.interactive import Translation
from rpython.translator.sandbox.sandboxio import SandboxedIO, Ptr

if 0:#hasattr(signal, 'alarm'):
    _orig_read_message = read_message

    def _timed_out(*args):
        raise EOFError("timed out waiting for data")

    def read_message(f):
        signal.signal(signal.SIGALRM, _timed_out)
        signal.alarm(20)
        try:
            return _orig_read_message(f)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, signal.SIG_DFL)

class OUT(object):
    def __init__(self, raw):
        self.raw = raw

class RAW(object):
    def __init__(self, raw):
        self.raw = raw

class ARG(object):
    def __init__(self, index):
        self.index = index

class MALLOC_FREE(object):
    def __init__(self, raw):
        self.raw = raw

ANY = object()
NULL = object()
EMPTY_ENVIRON = object()
_NO_RESULT = object()

def expect(sandio, fnname, expected_args, result=_NO_RESULT, errno=_NO_RESULT):
    msg, args = sandio.read_message()
    assert msg == fnname
    assert len(args) == len(expected_args)
    for arg, expected_arg in zip(args, expected_args):
        if type(expected_arg) is bytes:
            assert type(arg) is Ptr
            arg_str = sandio.read_charp(arg, len(expected_arg) + 100)
            assert arg_str == expected_arg
        elif type(expected_arg) is OUT:
            assert type(arg) is Ptr
            sandio.write_buffer(arg, expected_arg.raw)
        elif type(expected_arg) is RAW:
            assert type(arg) is Ptr
            arg_str = sandio.read_buffer(arg, len(expected_arg.raw))
            assert arg_str == expected_arg.raw
        elif expected_arg is ANY:
            pass
        elif expected_arg is NULL:
            assert type(arg) is Ptr
            assert arg.addr == 0
        else:
            assert arg == expected_arg
    if errno is not _NO_RESULT:
        sandio.set_errno(errno)
    if result is not _NO_RESULT:
        if type(result) is ARG:
            result = args[result.index]
        if result is EMPTY_ENVIRON:
            result = sandio.malloc("\x00" * 16)
        if type(result) is MALLOC_FREE:
            ptr = sandio.malloc(result.raw)
            sandio.write_result(ptr)
            sandio.free(ptr)
        else:
            sandio.write_result(result)

def expect_done(sandio):
    with py.test.raises(EOFError):
        sandio.read_message()
    assert sandio.popen.wait() == 0   # exit code 0
    sandio.close()

def expect_failure(sandio, expected_error_text):
    h, _, _ = select.select([sandio.popen.stdout, sandio.popen.stderr], [], [])
    assert sandio.popen.stderr in h
    error_text = sandio.popen.stderr.read()
    assert expected_error_text in error_text
    assert sandio.popen.wait() != 0   # exit code != 0
    sandio.close()

def compile(f, gc='ref', **kwds):
    t = Translation(f, backend='c', sandbox=True, gc=gc,
                    check_str_without_nul=True, **kwds)
    return str(t.compile())

def run_in_subprocess(exe, *args):
    popen = subprocess.Popen([exe] + list(args), stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    return SandboxedIO(popen)

def test_open_dup():
    def entry_point(argv):
        fd = os.open("/tmp/foobar", os.O_RDONLY, 0777)
        assert fd == 77
        fd2 = os.dup(fd)
        assert fd2 == 78
        return 0

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe)
    expect(sandio, "open(pii)i", ("/tmp/foobar", os.O_RDONLY, 0777), 77)
    expect(sandio, "dup(i)i", (77,), 78)
    expect_done(sandio)

def test_open_dup_rposix():
    from rpython.rlib import rposix
    def entry_point(argv):
        fd = rposix.open("/tmp/foobar", os.O_RDONLY, 0777)
        assert fd == 77
        fd2 = rposix.dup(fd)
        assert fd2 == 78
        return 0

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe)
    expect(sandio, "open(pii)i", ("/tmp/foobar", os.O_RDONLY, 0777), 77)
    expect(sandio, "dup(i)i",  (77,), 78)
    expect_done(sandio)

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
    sandio = run_in_subprocess(exe)
    expect(sandio, "open(pii)i", ("/tmp/foobar", os.O_RDONLY, 0777), 77)
    expect(sandio, "read(ipi)i", (77, OUT("he\x00llo"), 123), len("he\x00llo"))
    sz = len("world\x00!\x00")
    expect(sandio, "write(ipi)i", (77, RAW("world\x00!\x00"), sz), 42)
    expect(sandio, "close(i)i", (77,), 0)
    expect_done(sandio)

def test_dup2_access():
    def entry_point(argv):
        os.dup2(34, 56)
        y = os.access("spam", 77)
        return 1 - y

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe)
    expect(sandio, "dup2(ii)i",   (34, 56), 0)
    expect(sandio, "access(pi)i", ("spam", 77), 0)
    expect_done(sandio)

@py.test.mark.skip()
def test_stat_ftruncate():
    from rpython.translator.sandbox.sandlib import RESULTTYPE_STATRESULT
    from rpython.rlib.rarithmetic import r_longlong
    r0x12380000007 = r_longlong(0x12380000007)

    if not hasattr(os, 'ftruncate'):
        py.test.skip("posix only")

    def entry_point(argv):
        st = os.stat("somewhere")
        os.ftruncate(st.st_mode, st.st_size)  # nonsense, just to see outside
        return 0

    exe = compile(entry_point)
    g, f = run_in_subprocess(exe)
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
        os.dup(int(t))
        return 0

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe)
    expect(sandio, "gettimeofday(pp)i", (ANY, ANY), -1, errno=errno.ENOSYS)
    expect(sandio, "time(p)i", (NULL,), 314159)
    expect(sandio, "dup(i)i", (314159,), 3)
    expect_done(sandio)

def test_getcwd():
    def entry_point(argv):
        t = os.getcwd()
        os.open(t, os.O_RDONLY, 0777)
        return 0

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe)
    expect(sandio, "getcwd(pi)p", (OUT("/tmp/foo/bar"), ANY), ARG(0))
    expect(sandio, "open(pii)i", ("/tmp/foo/bar", os.O_RDONLY, 0777), 77)
    expect_done(sandio)

def test_oserror():
    def entry_point(argv):
        try:
            os.stat("somewhere")
        except OSError as e:
            os.close(e.errno)    # nonsense, just to see outside
        return 0

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe)
    expect(sandio, "stat64(pp)i", ("somewhere", ANY), -1, errno=6321)
    expect(sandio, "close(i)i", (6321,), 0)
    expect_done(sandio)

def test_getenv():
    def entry_point(argv):
        s = os.environ["FOOBAR"]
        os.open(s, 0, 0)
        return 0

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe)
    expect(sandio, "getenv(p)p", ("FOOBAR",), MALLOC_FREE("tmp_foo_bar"))
    expect(sandio, "open(pii)i", ("tmp_foo_bar", 0, 0), 0)
    expect_done(sandio)

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
    sandio = run_in_subprocess(exe)
    expect_failure(sandio, 'Invalid RPython operation')

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
    from rpython.rlib.rmmap import alloc, free

    def entry_point(argv):
        one = alloc(1024)
        free(one, 1024)
        return 0

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe)
    expect_done(sandio)

def test_unsafe_mmap():
    py.test.skip("Since this stuff is unimplemented, it won't work anyway "
                 "however, the day it starts working, it should pass test")
    from rpython.rlib.rmmap import mmap

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

def test_environ_items():
    def entry_point(argv):
        print os.environ.items()
        return 0

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe)
    expect(sandio, "get_environ()p", (), EMPTY_ENVIRON)
    expect(sandio, "write(ipi)i", (1, RAW("[]\n"), 3), 3)
    expect_done(sandio)

def test_safefuncs():
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

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe, "3.011")
    out = "2 4 13 75 2 1 3\n"
    expect(sandio, "write(ipi)i", (1, RAW(out), len(out)), len(out))
    expect_done(sandio)

def test_safefuncs_exception():
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

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe, "3.011")
    out = "110\n"
    expect(sandio, "write(ipi)i", (1, RAW(out), len(out)), len(out))
    out = "as expected, got a ValueError\n"
    expect(sandio, "write(ipi)i", (1, RAW(out), len(out)), len(out))
    expect_done(sandio)

def test_os_path_safe():
    def entry_point(argv):
        print os.path.join('tmp', argv[1])
        return 0

    exe = compile(entry_point)
    sandio = run_in_subprocess(exe, "spam")
    out = os.path.join("tmp", "spam") + '\n'
    expect(sandio, "write(ipi)i", (1, RAW(out), len(out)), len(out))
    expect_done(sandio)
