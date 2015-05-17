import py
from rpython.tool.udir import udir
from pypy.interpreter.gateway import interp2app


class AppTestRecompilerPython:
    spaceconfig = dict(usemodules=['_cffi_backend'])

    def setup_class(cls):
        try:
            from cffi import FFI           # <== the system one, which
            from cffi import recompiler    # needs to be at least cffi 1.0.0
            from cffi import ffiplatform
        except ImportError:
            py.test.skip("system cffi module not found or older than 1.0.0")
        SRC = """
        #define FOOBAR (-42)
        static const int FOOBAZ = -43;
        #define BIGPOS 420000000000L
        #define BIGNEG -420000000000L
        int add42(int x) { return x + 42; }
        int globalvar42 = 1234;
        struct foo_s;
        typedef struct bar_s { int x; signed char a[]; } bar_t;
        enum foo_e { AA, BB, CC };

        void init_test_re_python(void) { }      /* windows hack */
        void PyInit__test_re_python(void) { }   /* windows hack */
        """
        tmpdir = udir.join('test_re_python')
        tmpdir.ensure(dir=1)
        c_file = tmpdir.join('_test_re_python.c')
        c_file.write(SRC)
        ext = ffiplatform.get_extension(str(c_file), '_test_re_python',
                                        export_symbols=['add42', 'globalvar42'])
        outputfilename = ffiplatform.compile(str(tmpdir), ext)
        #mod.extmod = outputfilename
        #mod.tmpdir = tmpdir
        #
        ffi = FFI()
        ffi.cdef("""
        #define FOOBAR -42
        static const int FOOBAZ = -43;
        #define BIGPOS 420000000000L
        #define BIGNEG -420000000000L
        int add42(int);
        int globalvar42;
        struct foo_s;
        typedef struct bar_s { int x; signed char a[]; } bar_t;
        enum foo_e { AA, BB, CC };
        """)
        ffi.set_source('re_python_pysrc', None)
        ffi.emit_python_code(str(tmpdir.join('re_python_pysrc.py')))
        #mod.original_ffi = ffi
        #
        space = cls.space
        space.appexec([space.wrap(str(tmpdir))], """(path):
            import _cffi_backend     # force it to be initialized
            import sys
            sys.path.insert(0, path)
        """)


    def test_constant(self):
        from re_python_pysrc import ffi
        assert ffi.integer_const('FOOBAR') == -42
        assert ffi.integer_const('FOOBAZ') == -43

    def test_large_constant():
        from re_python_pysrc import ffi
        assert ffi.integer_const('BIGPOS') == 420000000000
        assert ffi.integer_const('BIGNEG') == -420000000000

    def test_function():
        import _cffi_backend
        from re_python_pysrc import ffi
        lib = ffi.dlopen(extmod)
        assert lib.add42(-10) == 32
        assert type(lib.add42) is _cffi_backend.FFI.CData

    def test_dlclose():
        import _cffi_backend
        from re_python_pysrc import ffi
        lib = ffi.dlopen(extmod)
        ffi.dlclose(lib)
        e = py.test.raises(ffi.error, ffi.dlclose, lib)
        assert str(e.value) == (
            "library '%s' is already closed or was not created with ffi.dlopen()"
            % (extmod,))

    def test_constant_via_lib():
        from re_python_pysrc import ffi
        lib = ffi.dlopen(extmod)
        assert lib.FOOBAR == -42
        assert lib.FOOBAZ == -43

    def test_opaque_struct():
        from re_python_pysrc import ffi
        ffi.cast("struct foo_s *", 0)
        py.test.raises(TypeError, ffi.new, "struct foo_s *")

    def test_nonopaque_struct():
        from re_python_pysrc import ffi
        for p in [ffi.new("struct bar_s *", [5, b"foobar"]),
                  ffi.new("bar_t *", [5, b"foobar"])]:
            assert p.x == 5
            assert p.a[0] == ord('f')
            assert p.a[5] == ord('r')

    def test_enum():
        from re_python_pysrc import ffi
        assert ffi.integer_const("BB") == 1
        e = ffi.cast("enum foo_e", 2)
        assert ffi.string(e) == "CC"

    def test_include_1():
        sub_ffi = FFI()
        sub_ffi.cdef("static const int k2 = 121212;")
        sub_ffi.include(original_ffi)
        assert 'macro FOOBAR' in original_ffi._parser._declarations
        assert 'macro FOOBAZ' in original_ffi._parser._declarations
        sub_ffi.set_source('re_python_pysrc', None)
        sub_ffi.emit_python_code(str(tmpdir.join('_re_include_1.py')))
        #
        from _re_include_1 import ffi
        assert ffi.integer_const('FOOBAR') == -42
        assert ffi.integer_const('FOOBAZ') == -43
        assert ffi.integer_const('k2') == 121212
        lib = ffi.dlopen(extmod)     # <- a random unrelated library would be fine
        assert lib.FOOBAR == -42
        assert lib.FOOBAZ == -43
        assert lib.k2 == 121212
        #
        p = ffi.new("bar_t *", [5, b"foobar"])
        assert p.a[4] == ord('a')

    def test_global_var():
        from re_python_pysrc import ffi
        lib = ffi.dlopen(extmod)
        assert lib.globalvar42 == 1234
        p = ffi.addressof(lib, 'globalvar42')
        lib.globalvar42 += 5
        assert p[0] == 1239
        p[0] -= 1
        assert lib.globalvar42 == 1238

    def test_rtld_constants():
        from re_python_pysrc import ffi
        ffi.RTLD_NOW    # check that we have the attributes
        ffi.RTLD_LAZY
        ffi.RTLD_GLOBAL
