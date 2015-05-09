import py
py.test.skip("later")

from cffi1 import FFI
import math


def test_cdef_struct():
    ffi = FFI()
    ffi.cdef("struct foo_s { int a, b; };")
    assert ffi.sizeof("struct foo_s") == 8

def test_cdef_union():
    ffi = FFI()
    ffi.cdef("union foo_s { int a, b; };")
    assert ffi.sizeof("union foo_s") == 4

def test_cdef_struct_union():
    ffi = FFI()
    ffi.cdef("union bar_s { int a; }; struct foo_s { int b; };")
    assert ffi.sizeof("union bar_s") == 4
    assert ffi.sizeof("struct foo_s") == 4

def test_cdef_struct_typename_1():
    ffi = FFI()
    ffi.cdef("typedef struct { int a; } t1; typedef struct { t1* m; } t2;")
    assert ffi.sizeof("t2") == ffi.sizeof("void *")
    assert ffi.sizeof("t1") == 4

def test_cdef_struct_typename_2():
    ffi = FFI()
    ffi.cdef("typedef struct { int a; } *p1; typedef struct { p1 m; } *p2;")
    p2 = ffi.new("p2")
    assert ffi.sizeof(p2[0]) == ffi.sizeof("void *")
    assert ffi.sizeof(p2[0].m) == ffi.sizeof("void *")

def test_cdef_struct_anon_1():
    ffi = FFI()
    ffi.cdef("typedef struct { int a; } t1; struct foo_s { t1* m; };")
    assert ffi.sizeof("struct foo_s") == ffi.sizeof("void *")

def test_cdef_struct_anon_2():
    ffi = FFI()
    ffi.cdef("typedef struct { int a; } *p1; struct foo_s { p1 m; };")
    assert ffi.sizeof("struct foo_s") == ffi.sizeof("void *")

def test_cdef_struct_anon_3():
    ffi = FFI()
    ffi.cdef("typedef struct { int a; } **pp; struct foo_s { pp m; };")
    assert ffi.sizeof("struct foo_s") == ffi.sizeof("void *")

def test_math_sin():
    ffi = FFI()
    ffi.cdef("double sin(double);")
    m = ffi.dlopen('m')
    x = m.sin(1.23)
    assert x == math.sin(1.23)
