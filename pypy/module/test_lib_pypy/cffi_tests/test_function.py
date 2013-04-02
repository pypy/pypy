import py
from cffi import FFI
import math, os, sys
import ctypes.util
from cffi.backend_ctypes import CTypesBackend
from pypy.module.test_lib_pypy.cffi_tests.udir import udir

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class FdWriteCapture(object):
    """xxx limited to capture at most 512 bytes of output, according
    to the Posix manual."""

    def __init__(self, capture_fd=1):   # stdout, by default
        self.capture_fd = capture_fd

    def __enter__(self):
        self.read_fd, self.write_fd = os.pipe()
        self.copy_fd = os.dup(self.capture_fd)
        os.dup2(self.write_fd, self.capture_fd)
        return self

    def __exit__(self, *args):
        os.dup2(self.copy_fd, self.capture_fd)
        os.close(self.copy_fd)
        os.close(self.write_fd)
        self._value = os.read(self.read_fd, 512)
        os.close(self.read_fd)

    def getvalue(self):
        return self._value


class TestFunction(object):
    Backend = CTypesBackend

    def test_sin(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            double sin(double x);
        """)
        m = ffi.dlopen("m")
        x = m.sin(1.23)
        assert x == math.sin(1.23)

    def test_sinf(self):
        if sys.platform == 'win32':
            py.test.skip("no 'sinf'")
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            float sinf(float x);
        """)
        m = ffi.dlopen("m")
        x = m.sinf(1.23)
        assert type(x) is float
        assert x != math.sin(1.23)    # rounding effects
        assert abs(x - math.sin(1.23)) < 1E-6

    def test_sin_no_return_value(self):
        # check that 'void'-returning functions work too
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            void sin(double x);
        """)
        m = ffi.dlopen("m")
        x = m.sin(1.23)
        assert x is None

    def test_dlopen_filename(self):
        path = ctypes.util.find_library("m")
        if not path:
            py.test.skip("libm not found")
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            double cos(double x);
        """)
        m = ffi.dlopen(path)
        x = m.cos(1.23)
        assert x == math.cos(1.23)

        m = ffi.dlopen(os.path.basename(path))
        x = m.cos(1.23)
        assert x == math.cos(1.23)

    def test_dlopen_flags(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            double cos(double x);
        """)
        m = ffi.dlopen("m", ffi.RTLD_LAZY | ffi.RTLD_LOCAL)
        x = m.cos(1.23)
        assert x == math.cos(1.23)

    def test_tlsalloc(self):
        if sys.platform != 'win32':
            py.test.skip("win32 only")
        if self.Backend is CTypesBackend:
            py.test.skip("ctypes complains on wrong calling conv")
        ffi = FFI(backend=self.Backend())
        ffi.cdef("long TlsAlloc(void); int TlsFree(long);")
        lib = ffi.dlopen('KERNEL32.DLL')
        x = lib.TlsAlloc()
        assert x != 0
        y = lib.TlsFree(x)
        assert y != 0

    def test_puts(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            int puts(const char *);
            int fflush(void *);
        """)
        ffi.C = ffi.dlopen(None)
        ffi.C.puts   # fetch before capturing, for easier debugging
        with FdWriteCapture() as fd:
            ffi.C.puts(b"hello")
            ffi.C.puts(b"  world")
            ffi.C.fflush(ffi.NULL)
        res = fd.getvalue()
        assert res == b'hello\n  world\n'

    def test_puts_without_const(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            int puts(char *);
            int fflush(void *);
        """)
        ffi.C = ffi.dlopen(None)
        ffi.C.puts   # fetch before capturing, for easier debugging
        with FdWriteCapture() as fd:
            ffi.C.puts(b"hello")
            ffi.C.puts(b"  world")
            ffi.C.fflush(ffi.NULL)
        res = fd.getvalue()
        assert res == b'hello\n  world\n'

    def test_fputs(self):
        if not sys.platform.startswith('linux'):
            py.test.skip("probably no symbol 'stdout' in the lib")
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            int fputs(const char *, void *);
            void *stdout, *stderr;
        """)
        ffi.C = ffi.dlopen(None)
        with FdWriteCapture(2) as fd:
            ffi.C.fputs(b"hello from stderr\n", ffi.C.stderr)
        res = fd.getvalue()
        assert res == b'hello from stderr\n'

    def test_vararg(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
           int printf(const char *format, ...);
           int fflush(void *);
        """)
        ffi.C = ffi.dlopen(None)
        with FdWriteCapture() as fd:
            ffi.C.printf(b"hello with no arguments\n")
            ffi.C.printf(b"hello, %s!\n", ffi.new("char[]", b"world"))
            ffi.C.printf(ffi.new("char[]", b"hello, %s!\n"),
                         ffi.new("char[]", b"world2"))
            ffi.C.printf(b"hello int %d long %ld long long %lld\n",
                         ffi.cast("int", 42),
                         ffi.cast("long", 84),
                         ffi.cast("long long", 168))
            ffi.C.printf(b"hello %p\n", ffi.NULL)
            ffi.C.fflush(ffi.NULL)
        res = fd.getvalue()
        if sys.platform == 'win32':
            NIL = b"00000000"
        elif sys.platform.startswith(('linux', 'gnu')):
            NIL = b"(nil)"
        else:
            NIL = b"0x0"    # OS/X at least
        assert res == (b"hello with no arguments\n"
                       b"hello, world!\n"
                       b"hello, world2!\n"
                       b"hello int 42 long 84 long long 168\n"
                       b"hello " + NIL + b"\n")

    def test_must_specify_type_of_vararg(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
           int printf(const char *format, ...);
        """)
        ffi.C = ffi.dlopen(None)
        e = py.test.raises(TypeError, ffi.C.printf, b"hello %d\n", 42)
        assert str(e.value) == ("argument 2 passed in the variadic part "
                                "needs to be a cdata object (got int)")

    def test_function_has_a_c_type(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            int puts(const char *);
        """)
        ffi.C = ffi.dlopen(None)
        fptr = ffi.C.puts
        assert ffi.typeof(fptr) == ffi.typeof("int(*)(const char*)")
        if self.Backend is CTypesBackend:
            assert repr(fptr).startswith("<cdata 'int puts(char *)' 0x")

    def test_function_pointer(self):
        ffi = FFI(backend=self.Backend())
        def cb(charp):
            assert repr(charp).startswith("<cdata 'char *' 0x")
            return 42
        fptr = ffi.callback("int(*)(const char *txt)", cb)
        assert fptr != ffi.callback("int(*)(const char *)", cb)
        assert repr(fptr) == "<cdata 'int(*)(char *)' calling %r>" % (cb,)
        res = fptr(b"Hello")
        assert res == 42
        #
        ffi.cdef("""
            int puts(const char *);
            int fflush(void *);
        """)
        ffi.C = ffi.dlopen(None)
        fptr = ffi.cast("int(*)(const char *txt)", ffi.C.puts)
        assert fptr == ffi.C.puts
        assert repr(fptr).startswith("<cdata 'int(*)(char *)' 0x")
        with FdWriteCapture() as fd:
            fptr(b"world")
            ffi.C.fflush(ffi.NULL)
        res = fd.getvalue()
        assert res == b'world\n'

    def test_callback_returning_void(self):
        ffi = FFI(backend=self.Backend())
        for returnvalue in [None, 42]:
            def cb():
                return returnvalue
            fptr = ffi.callback("void(*)(void)", cb)
            old_stderr = sys.stderr
            try:
                sys.stderr = StringIO()
                returned = fptr()
                printed = sys.stderr.getvalue()
            finally:
                sys.stderr = old_stderr
            assert returned is None
            if returnvalue is None:
                assert printed == ''
            else:
                assert "None" in printed

    def test_passing_array(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            int strlen(char[]);
        """)
        ffi.C = ffi.dlopen(None)
        p = ffi.new("char[]", b"hello")
        res = ffi.C.strlen(p)
        assert res == 5

    def test_write_variable(self):
        if not sys.platform.startswith('linux'):
            py.test.skip("probably no symbol 'stdout' in the lib")
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            int puts(const char *);
            void *stdout, *stderr;
        """)
        ffi.C = ffi.dlopen(None)
        pout = ffi.C.stdout
        perr = ffi.C.stderr
        assert repr(pout).startswith("<cdata 'void *' 0x")
        assert repr(perr).startswith("<cdata 'void *' 0x")
        with FdWriteCapture(2) as fd:     # capturing stderr
            ffi.C.stdout = perr
            try:
                ffi.C.puts(b"hello!") # goes to stdout, which is equal to stderr now
            finally:
                ffi.C.stdout = pout
        res = fd.getvalue()
        assert res == b"hello!\n"

    def test_strchr(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            char *strchr(const char *s, int c);
        """)
        ffi.C = ffi.dlopen(None)
        p = ffi.new("char[]", b"hello world!")
        q = ffi.C.strchr(p, ord('w'))
        assert ffi.string(q) == b"world!"

    def test_function_with_struct_argument(self):
        if sys.platform == 'win32':
            py.test.skip("no 'inet_ntoa'")
        if (self.Backend is CTypesBackend and
            '__pypy__' in sys.builtin_module_names):
            py.test.skip("ctypes limitation on pypy")
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            struct in_addr { unsigned int s_addr; };
            char *inet_ntoa(struct in_addr in);
        """)
        ffi.C = ffi.dlopen(None)
        ina = ffi.new("struct in_addr *", [0x04040404])
        a = ffi.C.inet_ntoa(ina[0])
        assert ffi.string(a) == b'4.4.4.4'

    def test_function_typedef(self):
        py.test.skip("using really obscure C syntax")
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            typedef double func_t(double);
            func_t sin;
        """)
        m = ffi.dlopen("m")
        x = m.sin(1.23)
        assert x == math.sin(1.23)

    def test_fputs_custom_FILE(self):
        if self.Backend is CTypesBackend:
            py.test.skip("FILE not supported with the ctypes backend")
        filename = str(udir.join('fputs_custom_FILE'))
        ffi = FFI(backend=self.Backend())
        ffi.cdef("int fputs(const char *, FILE *);")
        C = ffi.dlopen(None)
        with open(filename, 'wb') as f:
            f.write(b'[')
            C.fputs(b"hello from custom file", f)
            f.write(b'][')
            C.fputs(b"some more output", f)
            f.write(b']')
        with open(filename, 'rb') as f:
            res = f.read()
        assert res == b'[hello from custom file][some more output]'

    def test_constants_on_lib(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""enum foo_e { AA, BB, CC=5, DD };
                    typedef enum { EE=-5, FF } some_enum_t;""")
        lib = ffi.dlopen(None)
        assert lib.AA == 0
        assert lib.BB == 1
        assert lib.CC == 5
        assert lib.DD == 6
        assert lib.EE == -5
        assert lib.FF == -4
