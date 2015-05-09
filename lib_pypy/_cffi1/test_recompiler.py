import sys, os, py
from cffi import FFI, VerificationError
from _cffi1 import recompiler
from _cffi1.udir import udir


def check_type_table(input, expected_output, included=None):
    ffi = FFI()
    if included:
        ffi1 = FFI()
        ffi1.cdef(included)
        ffi.include(ffi1)
    ffi.cdef(input)
    recomp = recompiler.Recompiler(ffi, 'testmod')
    recomp.collect_type_table()
    assert ''.join(map(str, recomp.cffi_types)) == expected_output

def verify(ffi, module_name, *args, **kwds):
    kwds.setdefault('undef_macros', ['NDEBUG'])
    return recompiler.verify(ffi, '_CFFI_' + module_name, *args, **kwds)


def test_type_table_func():
    check_type_table("double sin(double);",
                     "(FUNCTION 1)(PRIMITIVE 14)(FUNCTION_END 0)")
    check_type_table("float sin(double);",
                     "(FUNCTION 3)(PRIMITIVE 14)(FUNCTION_END 0)(PRIMITIVE 13)")
    check_type_table("float sin(void);",
                     "(FUNCTION 2)(FUNCTION_END 0)(PRIMITIVE 13)")
    check_type_table("double sin(float); double cos(float);",
                     "(FUNCTION 3)(PRIMITIVE 13)(FUNCTION_END 0)(PRIMITIVE 14)")
    check_type_table("double sin(float); double cos(double);",
                     "(FUNCTION 1)(PRIMITIVE 14)(FUNCTION_END 0)"   # cos
                     "(FUNCTION 1)(PRIMITIVE 13)(FUNCTION_END 0)")  # sin
    check_type_table("float sin(double); float cos(float);",
                     "(FUNCTION 4)(PRIMITIVE 14)(FUNCTION_END 0)"   # sin
                     "(FUNCTION 4)(PRIMITIVE 13)(FUNCTION_END 0)")  # cos

def test_type_table_use_noop_for_repeated_args():
    check_type_table("double sin(double *, double *);",
                     "(FUNCTION 4)(POINTER 4)(NOOP 1)(FUNCTION_END 0)"
                     "(PRIMITIVE 14)")
    check_type_table("double sin(double *, double *, double);",
                     "(FUNCTION 3)(POINTER 3)(NOOP 1)(PRIMITIVE 14)"
                     "(FUNCTION_END 0)")

def test_type_table_dont_use_noop_for_primitives():
    check_type_table("double sin(double, double);",
                     "(FUNCTION 1)(PRIMITIVE 14)(PRIMITIVE 14)(FUNCTION_END 0)")

def test_type_table_funcptr_as_argument():
    check_type_table("int sin(double(float));",
                     "(FUNCTION 6)(PRIMITIVE 13)(FUNCTION_END 0)"
                     "(FUNCTION 7)(POINTER 0)(FUNCTION_END 0)"
                     "(PRIMITIVE 14)(PRIMITIVE 7)")

def test_type_table_variadic_function():
    check_type_table("int sin(int, ...);",
                     "(FUNCTION 1)(PRIMITIVE 7)(FUNCTION_END 1)(POINTER 0)")

def test_type_table_array():
    check_type_table("int a[100];",
                     "(PRIMITIVE 7)(ARRAY 0)(None 100)")

def test_type_table_typedef():
    check_type_table("typedef int foo_t;",
                     "(PRIMITIVE 7)")

def test_type_table_prebuilt_type():
    check_type_table("int32_t f(void);",
                     "(FUNCTION 2)(FUNCTION_END 0)(PRIMITIVE 21)")

def test_type_table_struct_opaque():
    check_type_table("struct foo_s;",
                     "(STRUCT_UNION 0)")

def test_type_table_struct():
    check_type_table("struct foo_s { int a; long b; };",
                     "(PRIMITIVE 7)(PRIMITIVE 9)(STRUCT_UNION 0)")

def test_type_table_union():
    check_type_table("union foo_u { int a; long b; };",
                     "(PRIMITIVE 7)(PRIMITIVE 9)(STRUCT_UNION 0)")

def test_type_table_struct_used():
    check_type_table("struct foo_s { int a; long b; }; int f(struct foo_s*);",
                     "(FUNCTION 3)(POINTER 5)(FUNCTION_END 0)"
                     "(PRIMITIVE 7)(PRIMITIVE 9)"
                     "(STRUCT_UNION 0)")

def test_type_table_anonymous_struct_with_typedef():
    check_type_table("typedef struct { int a; long b; } foo_t;",
                     "(STRUCT_UNION 0)(PRIMITIVE 7)(PRIMITIVE 9)")

def test_type_table_enum():
    check_type_table("enum foo_e { AA, BB, ... };",
                     "(ENUM 0)")

def test_type_table_include_1():
    check_type_table("foo_t sin(foo_t);",
                     "(FUNCTION 1)(PRIMITIVE 14)(FUNCTION_END 0)",
                     included="typedef double foo_t;")

def test_type_table_include_2():
    check_type_table("struct foo_s *sin(struct foo_s *);",
                     "(FUNCTION 1)(POINTER 3)(FUNCTION_END 0)(STRUCT_UNION 0)",
                     included="struct foo_s { int x, y; };")


def test_math_sin():
    import math
    ffi = FFI()
    ffi.cdef("float sin(double); double cos(double);")
    lib = verify(ffi, 'test_math_sin', '#include <math.h>')
    assert lib.cos(1.43) == math.cos(1.43)

def test_repr_lib():
    ffi = FFI()
    lib = verify(ffi, 'test_repr_lib', '')
    assert repr(lib) == "<Lib object for '_CFFI_test_repr_lib'>"

def test_funcarg_ptr():
    ffi = FFI()
    ffi.cdef("int foo(int *);")
    lib = verify(ffi, 'test_funcarg_ptr', 'int foo(int *p) { return *p; }')
    assert lib.foo([-12345]) == -12345

def test_funcres_ptr():
    ffi = FFI()
    ffi.cdef("int *foo(void);")
    lib = verify(ffi, 'test_funcres_ptr',
                 'int *foo(void) { static int x=-12345; return &x; }')
    assert lib.foo()[0] == -12345

def test_global_var_array():
    ffi = FFI()
    ffi.cdef("int a[100];")
    lib = verify(ffi, 'test_global_var_array', 'int a[100] = { 9999 };')
    lib.a[42] = 123456
    assert lib.a[42] == 123456
    assert lib.a[0] == 9999

def test_verify_typedef():
    ffi = FFI()
    ffi.cdef("typedef int **foo_t;")
    lib = verify(ffi, 'test_verify_typedef', 'typedef int **foo_t;')
    assert ffi.sizeof("foo_t") == ffi.sizeof("void *")

def test_verify_typedef_dotdotdot():
    ffi = FFI()
    ffi.cdef("typedef ... foo_t;")
    verify(ffi, 'test_verify_typedef_dotdotdot', 'typedef int **foo_t;')

def test_verify_typedef_star_dotdotdot():
    ffi = FFI()
    ffi.cdef("typedef ... *foo_t;")
    verify(ffi, 'test_verify_typedef_star_dotdotdot', 'typedef int **foo_t;')

def test_global_var_int():
    ffi = FFI()
    ffi.cdef("int a, b, c;")
    lib = verify(ffi, 'test_global_var_int', 'int a = 999, b, c;')
    assert lib.a == 999
    lib.a -= 1001
    assert lib.a == -2
    lib.a = -2147483648
    assert lib.a == -2147483648
    py.test.raises(OverflowError, "lib.a = 2147483648")
    py.test.raises(OverflowError, "lib.a = -2147483649")
    lib.b = 525      # try with the first access being in setattr, too
    assert lib.b == 525
    py.test.raises(AttributeError, "del lib.a")
    py.test.raises(AttributeError, "del lib.c")
    py.test.raises(AttributeError, "del lib.foobarbaz")

def test_macro():
    ffi = FFI()
    ffi.cdef("#define FOOBAR ...")
    lib = verify(ffi, 'test_macro', "#define FOOBAR (-6912)")
    assert lib.FOOBAR == -6912
    py.test.raises(AttributeError, "lib.FOOBAR = 2")

def test_macro_check_value():
    # the value '-0x80000000' in C sources does not have a clear meaning
    # to me; it appears to have a different effect than '-2147483648'...
    # Moreover, on 32-bits, -2147483648 is actually equal to
    # -2147483648U, which in turn is equal to 2147483648U and so positive.
    vals = ['42', '-42', '0x80000000', '-2147483648',
            '0', '9223372036854775809ULL',
            '-9223372036854775807LL']
    if sys.maxsize <= 2**32:
        vals.remove('-2147483648')
    ffi = FFI()
    cdef_lines = ['#define FOO_%d_%d %s' % (i, j, vals[i])
                  for i in range(len(vals))
                  for j in range(len(vals))]
    ffi.cdef('\n'.join(cdef_lines))

    verify_lines = ['#define FOO_%d_%d %s' % (i, j, vals[j])  # [j], not [i]
                    for i in range(len(vals))
                    for j in range(len(vals))]
    lib = verify(ffi, 'test_macro_check_value_ok',
                 '\n'.join(verify_lines))
    #
    for j in range(len(vals)):
        c_got = int(vals[j].replace('U', '').replace('L', ''), 0)
        c_compiler_msg = str(c_got)
        if c_got > 0:
            c_compiler_msg += ' (0x%x)' % (c_got,)
        #
        for i in range(len(vals)):
            attrname = 'FOO_%d_%d' % (i, j)
            if i == j:
                x = getattr(lib, attrname)
                assert x == c_got
            else:
                e = py.test.raises(ffi.error, getattr, lib, attrname)
                assert str(e.value) == (
                    "the C compiler says '%s' is equal to "
                    "%s, but the cdef disagrees" % (attrname, c_compiler_msg))

def test_constant():
    ffi = FFI()
    ffi.cdef("static const int FOOBAR;")
    lib = verify(ffi, 'test_constant', "#define FOOBAR (-6912)")
    assert lib.FOOBAR == -6912
    py.test.raises(AttributeError, "lib.FOOBAR = 2")

def test_constant_nonint():
    ffi = FFI()
    ffi.cdef("static const double FOOBAR;")
    lib = verify(ffi, 'test_constant_nonint', "#define FOOBAR (-6912.5)")
    assert lib.FOOBAR == -6912.5
    py.test.raises(AttributeError, "lib.FOOBAR = 2")

def test_constant_ptr():
    ffi = FFI()
    ffi.cdef("static double *const FOOBAR;")
    lib = verify(ffi, 'test_constant_ptr', "#define FOOBAR NULL")
    assert lib.FOOBAR == ffi.NULL
    assert ffi.typeof(lib.FOOBAR) == ffi.typeof("double *")

def test_dir():
    ffi = FFI()
    ffi.cdef("int ff(int); int aa; static const int my_constant;")
    lib = verify(ffi, 'test_dir', """
        #define my_constant  (-45)
        int aa;
        int ff(int x) { return x+aa; }
    """)
    lib.aa = 5
    assert dir(lib) == ['aa', 'ff', 'my_constant']

def test_verify_opaque_struct():
    ffi = FFI()
    ffi.cdef("struct foo_s;")
    lib = verify(ffi, 'test_verify_opaque_struct', "struct foo_s;")
    assert ffi.typeof("struct foo_s").cname == "struct foo_s"

def test_verify_opaque_union():
    ffi = FFI()
    ffi.cdef("union foo_s;")
    lib = verify(ffi, 'test_verify_opaque_union', "union foo_s;")
    assert ffi.typeof("union foo_s").cname == "union foo_s"

def test_verify_struct():
    ffi = FFI()
    ffi.cdef("""struct foo_s { int b; short a; ...; };
                struct bar_s { struct foo_s *f; };""")
    lib = verify(ffi, 'test_verify_struct',
                 """struct foo_s { short a; int b; };
                    struct bar_s { struct foo_s *f; };""")
    ffi.typeof("struct bar_s *")
    p = ffi.new("struct foo_s *", {'a': -32768, 'b': -2147483648})
    assert p.a == -32768
    assert p.b == -2147483648
    py.test.raises(OverflowError, "p.a -= 1")
    py.test.raises(OverflowError, "p.b -= 1")
    q = ffi.new("struct bar_s *", {'f': p})
    assert q.f == p
    #
    assert ffi.offsetof("struct foo_s", "a") == 0
    assert ffi.offsetof("struct foo_s", "b") == 4
    assert ffi.offsetof(u"struct foo_s", u"b") == 4
    #
    py.test.raises(TypeError, ffi.addressof, p)
    assert ffi.addressof(p[0]) == p
    assert ffi.typeof(ffi.addressof(p[0])) is ffi.typeof("struct foo_s *")
    assert ffi.typeof(ffi.addressof(p, "b")) is ffi.typeof("int *")
    assert ffi.addressof(p, "b")[0] == p.b

def test_verify_exact_field_offset():
    ffi = FFI()
    ffi.cdef("""struct foo_s { int b; short a; };""")
    lib = verify(ffi, 'test_verify_exact_field_offset',
                 """struct foo_s { short a; int b; };""")
    e = py.test.raises(ffi.error, ffi.new, "struct foo_s *", [])    # lazily
    assert str(e.value) == ("struct foo_s: wrong offset for field 'b' (cdef "
                       'says 0, but C compiler says 4). fix it or use "...;" '
                       "in the cdef for struct foo_s to make it flexible")

def test_type_caching():
    ffi1 = FFI(); ffi1.cdef("struct foo_s;")
    ffi2 = FFI(); ffi2.cdef("struct foo_s;")    # different one!
    lib1 = verify(ffi1, 'test_type_caching_1', 'struct foo_s;')
    lib2 = verify(ffi2, 'test_type_caching_2', 'struct foo_s;')
    # shared types
    assert ffi1.typeof("long") is ffi2.typeof("long")
    assert ffi1.typeof("long**") is ffi2.typeof("long * *")
    assert ffi1.typeof("long(*)(int, ...)") is ffi2.typeof("long(*)(int, ...)")
    # non-shared types
    assert ffi1.typeof("struct foo_s") is not ffi2.typeof("struct foo_s")
    assert ffi1.typeof("struct foo_s *") is not ffi2.typeof("struct foo_s *")
    assert ffi1.typeof("struct foo_s*(*)()") is not (
        ffi2.typeof("struct foo_s*(*)()"))
    assert ffi1.typeof("void(*)(struct foo_s*)") is not (
        ffi2.typeof("void(*)(struct foo_s*)"))

def test_verify_enum():
    ffi = FFI()
    ffi.cdef("""enum e1 { B1, A1, ... }; enum e2 { B2, A2, ... };""")
    lib = verify(ffi, 'test_verify_enum',
                 "enum e1 { A1, B1, C1=%d };" % sys.maxsize +
                 "enum e2 { A2, B2, C2 };")
    ffi.typeof("enum e1")
    ffi.typeof("enum e2")
    assert lib.A1 == 0
    assert lib.B1 == 1
    assert lib.A2 == 0
    assert lib.B2 == 1
    assert ffi.sizeof("enum e1") == ffi.sizeof("long")
    assert ffi.sizeof("enum e2") == ffi.sizeof("int")
    assert repr(ffi.cast("enum e1", 0)) == "<cdata 'enum e1' 0: A1>"

def test_duplicate_enum():
    ffi = FFI()
    ffi.cdef("enum e1 { A1, ... }; enum e2 { A1, ... };")
    py.test.raises(VerificationError, verify, ffi, 'test_duplicate_enum',
                    "enum e1 { A1 }; enum e2 { B1 };")

def test_dotdotdot_length_of_array_field():
    ffi = FFI()
    ffi.cdef("struct foo_s { int a[...]; int b[...]; };")
    verify(ffi, 'test_dotdotdot_length_of_array_field',
           "struct foo_s { int a[42]; int b[11]; };")
    assert ffi.sizeof("struct foo_s") == (42 + 11) * 4
    p = ffi.new("struct foo_s *")
    assert p.a[41] == p.b[10] == 0
    py.test.raises(IndexError, "p.a[42]")
    py.test.raises(IndexError, "p.b[11]")

def test_dotdotdot_global_array():
    ffi = FFI()
    ffi.cdef("int aa[...]; int bb[...];")
    lib = verify(ffi, 'test_dotdotdot_global_array',
                 "int aa[41]; int bb[12];")
    assert ffi.sizeof(lib.aa) == 41 * 4
    assert ffi.sizeof(lib.bb) == 12 * 4
    assert lib.aa[40] == lib.bb[11] == 0
    py.test.raises(IndexError, "lib.aa[41]")
    py.test.raises(IndexError, "lib.bb[12]")

def test_misdeclared_field_1():
    ffi = FFI()
    ffi.cdef("struct foo_s { int a[5]; };")
    verify(ffi, 'test_misdeclared_field_1',
           "struct foo_s { int a[6]; };")
    assert ffi.sizeof("struct foo_s") == 24  # found by the actual C code
    p = ffi.new("struct foo_s *")
    # lazily build the fields and boom:
    e = py.test.raises(ffi.error, "p.a")
    assert str(e.value).startswith("struct foo_s: wrong size for field 'a' "
                                   "(cdef says 20, but C compiler says 24)")

def test_open_array_in_struct():
    ffi = FFI()
    ffi.cdef("struct foo_s { int b; int a[]; };")
    verify(ffi, 'test_open_array_in_struct',
           "struct foo_s { int b; int a[]; };")
    assert ffi.sizeof("struct foo_s") == 4
    p = ffi.new("struct foo_s *", [5, [10, 20, 30]])
    assert p.a[2] == 30

def test_math_sin_type():
    ffi = FFI()
    ffi.cdef("double sin(double);")
    lib = verify(ffi, 'test_math_sin_type', '#include <math.h>')
    # 'lib.sin' is typed as a <built-in method> object on lib
    assert ffi.typeof(lib.sin).cname == "double(*)(double)"
    # 'x' is another <built-in method> object on lib, made very indirectly
    x = type(lib).__dir__.__get__(lib)
    py.test.raises(TypeError, ffi.typeof, x)

def test_verify_anonymous_struct_with_typedef():
    ffi = FFI()
    ffi.cdef("typedef struct { int a; long b; ...; } foo_t;")
    verify(ffi, 'test_verify_anonymous_struct_with_typedef',
           "typedef struct { long b; int hidden, a; } foo_t;")
    p = ffi.new("foo_t *", {'b': 42})
    assert p.b == 42
    assert repr(p).startswith("<cdata 'foo_t *' ")

def test_verify_anonymous_struct_with_star_typedef():
    ffi = FFI()
    ffi.cdef("typedef struct { int a; long b; } *foo_t;")
    verify(ffi, 'test_verify_anonymous_struct_with_star_typedef',
           "typedef struct { int a; long b; } *foo_t;")
    p = ffi.new("foo_t", {'b': 42})
    assert p.b == 42

def test_verify_anonymous_enum_with_typedef():
    ffi = FFI()
    ffi.cdef("typedef enum { AA, ... } e1;")
    lib = verify(ffi, 'test_verify_anonymous_enum_with_typedef1',
                 "typedef enum { BB, CC, AA } e1;")
    assert lib.AA == 2
    assert ffi.sizeof("e1") == ffi.sizeof("int")
    assert repr(ffi.cast("e1", 2)) == "<cdata 'e1' 2: AA>"
    #
    ffi = FFI()
    ffi.cdef("typedef enum { AA=%d } e1;" % sys.maxsize)
    lib = verify(ffi, 'test_verify_anonymous_enum_with_typedef2',
                 "typedef enum { AA=%d } e1;" % sys.maxsize)
    assert lib.AA == sys.maxsize
    assert ffi.sizeof("e1") == ffi.sizeof("long")

def test_unique_types():
    CDEF = "struct foo_s; union foo_u; enum foo_e { AA };"
    ffi1 = FFI(); ffi1.cdef(CDEF); verify(ffi1, "test_unique_types_1", CDEF)
    ffi2 = FFI(); ffi2.cdef(CDEF); verify(ffi2, "test_unique_types_2", CDEF)
    #
    assert ffi1.typeof("char") is ffi2.typeof("char ")
    assert ffi1.typeof("long") is ffi2.typeof("signed long int")
    assert ffi1.typeof("double *") is ffi2.typeof("double*")
    assert ffi1.typeof("int ***") is ffi2.typeof(" int * * *")
    assert ffi1.typeof("int[]") is ffi2.typeof("signed int[]")
    assert ffi1.typeof("signed int*[17]") is ffi2.typeof("int *[17]")
    assert ffi1.typeof("void") is ffi2.typeof("void")
    assert ffi1.typeof("int(*)(int,int)") is ffi2.typeof("int(*)(int,int)")
    #
    # these depend on user-defined data, so should not be shared
    for name in ["struct foo_s",
                 "union foo_u *",
                 "enum foo_e",
                 "struct foo_s *(*)()",
                 "void(*)(struct foo_s *)",
                 "struct foo_s *(*[5])[8]",
                 ]:
        assert ffi1.typeof(name) is not ffi2.typeof(name)
    # sanity check: twice 'ffi1'
    assert ffi1.typeof("struct foo_s*") is ffi1.typeof("struct foo_s *")

def test_module_name_in_package():
    ffi = FFI()
    ffi.cdef("int foo(int);")
    recompiler.recompile(ffi, "test_module_name_in_package.mymod",
                         "int foo(int x) { return x + 32; }",
                         tmpdir=str(udir))
    old_sys_path = sys.path[:]
    try:
        package_dir = udir.join('test_module_name_in_package')
        assert os.path.isdir(str(package_dir))
        assert len(os.listdir(str(package_dir))) > 0
        package_dir.join('__init__.py').write('')
        #
        sys.path.insert(0, str(udir))
        import test_module_name_in_package.mymod
        assert test_module_name_in_package.mymod.lib.foo(10) == 42
    finally:
        sys.path[:] = old_sys_path

def test_bad_size_of_global_1():
    ffi = FFI()
    ffi.cdef("short glob;")
    lib = verify(ffi, "test_bad_size_of_global_1", "long glob;")
    py.test.raises(ffi.error, "lib.glob")

def test_bad_size_of_global_2():
    ffi = FFI()
    ffi.cdef("int glob[10];")
    lib = verify(ffi, "test_bad_size_of_global_2", "int glob[9];")
    e = py.test.raises(ffi.error, "lib.glob")
    assert str(e.value) == ("global variable 'glob' should be 40 bytes "
                            "according to the cdef, but is actually 36")

def test_unspecified_size_of_global():
    ffi = FFI()
    ffi.cdef("int glob[];")
    lib = verify(ffi, "test_unspecified_size_of_global", "int glob[10];")
    lib.glob    # does not crash

def test_include_1():
    ffi1 = FFI()
    ffi1.cdef("typedef double foo_t;")
    verify(ffi1, "test_include_1_parent", "typedef double foo_t;")
    ffi = FFI()
    ffi.include(ffi1)
    ffi.cdef("foo_t ff1(foo_t);")
    lib = verify(ffi, "test_include_1", "double ff1(double x) { return 42.5; }")
    assert lib.ff1(0) == 42.5

def test_include_1b():
    ffi1 = FFI()
    ffi1.cdef("int foo1(int);")
    verify(ffi1, "test_include_1b_parent", "int foo1(int x) { return x + 10; }")
    ffi = FFI()
    ffi.include(ffi1)
    ffi.cdef("int foo2(int);")
    lib = verify(ffi, "test_include_1b", "int foo2(int x) { return x - 5; }")
    assert lib.foo2(42) == 37
    assert lib.foo1(42) == 52

def test_include_2():
    ffi1 = FFI()
    ffi1.cdef("struct foo_s { int x, y; };")
    verify(ffi1, "test_include_2_parent", "struct foo_s { int x, y; };")
    ffi = FFI()
    ffi.include(ffi1)
    ffi.cdef("struct foo_s *ff2(struct foo_s *);")
    lib = verify(ffi, "test_include_2",
                 "struct foo_s { int x, y; }; //usually from a #include\n"
                 "struct foo_s *ff2(struct foo_s *p) { p->y++; return p; }")
    p = ffi.new("struct foo_s *")
    p.y = 41
    q = lib.ff2(p)
    assert q == p
    assert p.y == 42

def test_include_3():
    ffi1 = FFI()
    ffi1.cdef("typedef short sshort_t;")
    verify(ffi1, "test_include_3_parent", "typedef short sshort_t;")
    ffi = FFI()
    ffi.include(ffi1)
    ffi.cdef("sshort_t ff3(sshort_t);")
    lib = verify(ffi, "test_include_3",
                 "typedef short sshort_t; //usually from a #include\n"
                 "sshort_t ff3(sshort_t x) { return x + 42; }")
    assert lib.ff3(10) == 52
    assert ffi.typeof(ffi.cast("sshort_t", 42)) is ffi.typeof("short")

def test_include_4():
    ffi1 = FFI()
    ffi1.cdef("typedef struct { int x; } mystruct_t;")
    verify(ffi1, "test_include_4_parent",
           "typedef struct { int x; } mystruct_t;")
    ffi = FFI()
    ffi.include(ffi1)
    ffi.cdef("mystruct_t *ff4(mystruct_t *);")
    lib = verify(ffi, "test_include_4",
           "typedef struct {int x; } mystruct_t; //usually from a #include\n"
           "mystruct_t *ff4(mystruct_t *p) { p->x += 42; return p; }")
    p = ffi.new("mystruct_t *", [10])
    q = lib.ff4(p)
    assert q == p
    assert p.x == 52

def test_include_5():
    py.test.xfail("also fails in 0.9.3")
    ffi1 = FFI()
    ffi1.cdef("typedef struct { int x; } *mystruct_p;")
    verify(ffi1, "test_include_5_parent",
           "typedef struct { int x; } *mystruct_p;")
    ffi = FFI()
    ffi.include(ffi1)
    ffi.cdef("mystruct_p ff5(mystruct_p);")
    lib = verify(ffi, "test_include_5",
           "typedef struct {int x; } *mystruct_p; //usually from a #include\n"
           "mystruct_p ff5(mystruct_p p) { p->x += 42; return p; }")
    p = ffi.new("mystruct_p", [10])
    q = lib.ff5(p)
    assert q == p
    assert p.x == 52

def test_include_6():
    ffi1 = FFI()
    ffi1.cdef("typedef ... mystruct_t;")
    verify(ffi1, "test_include_6_parent",
           "typedef struct _mystruct_s mystruct_t;")
    ffi = FFI()
    ffi.include(ffi1)
    ffi.cdef("mystruct_t *ff6(void); int ff6b(mystruct_t *);")
    lib = verify(ffi, "test_include_6",
           "typedef struct _mystruct_s mystruct_t; //usually from a #include\n"
           "struct _mystruct_s { int x; };\n"
           "static mystruct_t result_struct = { 42 };\n"
           "mystruct_t *ff6(void) { return &result_struct; }\n"
           "int ff6b(mystruct_t *p) { return p->x; }")
    p = lib.ff6()
    assert ffi.cast("int *", p)[0] == 42
    assert lib.ff6b(p) == 42

def test_include_7():
    ffi1 = FFI()
    ffi1.cdef("typedef ... mystruct_t;\n"
              "int ff7b(mystruct_t *);")
    verify(ffi1, "test_include_7_parent",
           "typedef struct { int x; } mystruct_t;\n"
           "int ff7b(mystruct_t *p) { return p->x; }")
    ffi = FFI()
    ffi.include(ffi1)
    ffi.cdef("mystruct_t *ff7(void);")
    lib = verify(ffi, "test_include_7",
           "typedef struct { int x; } mystruct_t; //usually from a #include\n"
           "static mystruct_t result_struct = { 42 };"
           "mystruct_t *ff7(void) { return &result_struct; }")
    p = lib.ff7()
    assert ffi.cast("int *", p)[0] == 42
    assert lib.ff7b(p) == 42

def test_unicode_libraries():
    try:
        unicode
    except NameError:
        py.test.skip("for python 2.x")
    #
    import math
    lib_m = "m"
    if sys.platform == 'win32':
        #there is a small chance this fails on Mingw via environ $CC
        import distutils.ccompiler
        if distutils.ccompiler.get_default_compiler() == 'msvc':
            lib_m = 'msvcrt'
    ffi = FFI()
    ffi.cdef(unicode("float sin(double); double cos(double);"))
    lib = verify(ffi, 'test_math_sin_unicode', unicode('#include <math.h>'),
                 libraries=[unicode(lib_m)])
    assert lib.cos(1.43) == math.cos(1.43)
