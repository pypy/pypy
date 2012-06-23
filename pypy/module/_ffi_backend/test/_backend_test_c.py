# ____________________________________________________________

def size_of_int():
    BInt = new_primitive_type("int")
    return sizeof(BInt)

def size_of_long():
    BLong = new_primitive_type("long")
    return sizeof(BLong)

def size_of_ptr():
    BInt = new_primitive_type("int")
    BPtr = new_pointer_type(BInt)
    return sizeof(BPtr)


def find_and_load_library(name):
    import ctypes.util
    path = ctypes.util.find_library(name)
    return load_library(path)

def test_load_library():
    x = find_and_load_library('c')
    assert repr(x).startswith("<clibrary '")

def test_nonstandard_integer_types():
    d = nonstandard_integer_types()
    assert type(d) is dict
    assert 'char' not in d
    assert d['size_t'] in (0x1004, 0x1008)
    assert d['size_t'] == d['ssize_t'] + 0x1000

def test_new_primitive_type():
    py.test.raises(KeyError, new_primitive_type, "foo")
    p = new_primitive_type("signed char")
    assert repr(p) == "<ctype 'signed char'>"

def test_cast_to_signed_char():
    p = new_primitive_type("signed char")
    x = cast(p, -65 + 17*256)
    assert repr(x) == "<cdata 'signed char'>"
    assert repr(type(x)) == "<type '_ffi_backend.CData'>"
    assert int(x) == -65
    x = cast(p, -66 + (1<<199)*256)
    assert repr(x) == "<cdata 'signed char'>"
    assert int(x) == -66
    assert (x == cast(p, -66)) is False
    assert (x != cast(p, -66)) is True
    q = new_primitive_type("short")
    assert (x == cast(q, -66)) is False
    assert (x != cast(q, -66)) is True

def test_sizeof_type():
    py.test.raises(TypeError, sizeof, 42.5)
    p = new_primitive_type("short")
    assert sizeof(p) == 2

def test_integer_types():
    for name in ['signed char', 'short', 'int', 'long', 'long long']:
        p = new_primitive_type(name)
        size = sizeof(p)
        min = -(1 << (8*size-1))
        max = (1 << (8*size-1)) - 1
        assert int(cast(p, min)) == min
        assert int(cast(p, max)) == max
        assert int(cast(p, min - 1)) == max
        assert int(cast(p, max + 1)) == min
        assert long(cast(p, min - 1)) == max
    for name in ['char', 'short', 'int', 'long', 'long long']:
        p = new_primitive_type('unsigned ' + name)
        size = sizeof(p)
        max = (1 << (8*size)) - 1
        assert int(cast(p, 0)) == 0
        assert int(cast(p, max)) == max
        assert int(cast(p, -1)) == max
        assert int(cast(p, max + 1)) == 0
        assert long(cast(p, -1)) == max

def test_no_float_on_int_types():
    p = new_primitive_type('long')
    py.test.raises(TypeError, float, cast(p, 42))

def test_float_types():
    INF = 1E200 * 1E200
    for name in ["float", "double"]:
        p = new_primitive_type(name)
        assert bool(cast(p, 0))
        assert bool(cast(p, INF))
        assert bool(cast(p, -INF))
        assert int(cast(p, -150)) == -150
        assert int(cast(p, 61.91)) == 61
        assert long(cast(p, 61.91)) == 61L
        assert type(int(cast(p, 61.91))) is int
        assert type(int(cast(p, 1E22))) is long
        assert type(long(cast(p, 61.91))) is long
        assert type(long(cast(p, 1E22))) is long
        py.test.raises(OverflowError, int, cast(p, INF))
        py.test.raises(OverflowError, int, cast(p, -INF))
        assert float(cast(p, 1.25)) == 1.25
        assert float(cast(p, INF)) == INF
        assert float(cast(p, -INF)) == -INF
        if name == "float":
            assert float(cast(p, 1.1)) != 1.1     # rounding error
            assert float(cast(p, 1E200)) == INF   # limited range

        assert cast(p, -1.1) != cast(p, -1.1)
        assert repr(float(cast(p, -0.0))) == '-0.0'
        assert float(cast(p, '\x09')) == 9.0
        assert float(cast(p, True)) == 1.0
        assert float(cast(p, None)) == 0.0

def test_character_type():
    p = new_primitive_type("char")
    assert bool(cast(p, '\x00'))
    assert cast(p, '\x00') != cast(p, -17*256)
    assert int(cast(p, 'A')) == 65
    assert long(cast(p, 'A')) == 65L
    assert type(int(cast(p, 'A'))) is int
    assert type(long(cast(p, 'A'))) is long
    assert str(cast(p, 'A')) == 'A'

def test_pointer_type():
    p = new_primitive_type("int")
    assert repr(p) == "<ctype 'int'>"
    p = new_pointer_type(p)
    assert repr(p) == "<ctype 'int *'>"
    p = new_pointer_type(p)
    assert repr(p) == "<ctype 'int * *'>"
    p = new_pointer_type(p)
    assert repr(p) == "<ctype 'int * * *'>"

def test_pointer_to_int():
    BInt = new_primitive_type("int")
    py.test.raises(TypeError, newp, BInt, None)
    BPtr = new_pointer_type(BInt)
    p = newp(BPtr, None)
    assert repr(p) == "<cdata 'int *' owning %d bytes>" % size_of_int()
    p = newp(BPtr, 5000)
    assert repr(p) == "<cdata 'int *' owning %d bytes>" % size_of_int()
    q = cast(BPtr, p)
    assert repr(q) == "<cdata 'int *'>"
    assert p == q
    assert hash(p) == hash(q)

def test_pointer_to_pointer():
    BInt = new_primitive_type("int")
    BPtr = new_pointer_type(BInt)
    BPtrPtr = new_pointer_type(BPtr)
    p = newp(BPtrPtr, None)
    assert repr(p) == "<cdata 'int * *' owning %d bytes>" % size_of_ptr()

def test_reading_pointer_to_int():
    BInt = new_primitive_type("int")
    BPtr = new_pointer_type(BInt)
    p = newp(BPtr, None)
    assert p[0] == 0
    p = newp(BPtr, 5000)
    assert p[0] == 5000
    py.test.raises(IndexError, "p[1]")
    py.test.raises(IndexError, "p[-1]")

def test_reading_pointer_to_float():
    BFloat = new_primitive_type("float")
    py.test.raises(TypeError, newp, BFloat, None)
    BPtr = new_pointer_type(BFloat)
    p = newp(BPtr, None)
    assert p[0] == 0.0 and type(p[0]) is float
    p = newp(BPtr, 1.25)
    assert p[0] == 1.25 and type(p[0]) is float
    p = newp(BPtr, 1.1)
    assert p[0] != 1.1 and abs(p[0] - 1.1) < 1E-5   # rounding errors

def test_cast_float_to_int():
    for type in ["int", "unsigned int", "long", "unsigned long",
                 "long long", "unsigned long long"]:
        p = new_primitive_type(type)
        assert int(cast(p, 4.2)) == 4
        py.test.raises(TypeError, newp, new_pointer_type(p), 4.2)

def test_reading_pointer_to_char():
    BChar = new_primitive_type("char")
    py.test.raises(TypeError, newp, BChar, None)
    BPtr = new_pointer_type(BChar)
    p = newp(BPtr, None)
    assert p[0] == '\x00'
    p = newp(BPtr, 'A')
    assert p[0] == 'A'
    py.test.raises(TypeError, newp, BPtr, 65)
    py.test.raises(TypeError, newp, BPtr, "foo")

def test_hash_differences():
    BChar = new_primitive_type("char")
    BInt = new_primitive_type("int")
    BFloat = new_primitive_type("float")
    assert (hash(cast(BChar, 'A')) !=
            hash(cast(BInt, 65)))
    assert hash(cast(BFloat, 65)) != hash(65.0)

def test_array_type():
    p = new_primitive_type("int")
    assert repr(p) == "<ctype 'int'>"
    #
    py.test.raises(TypeError, new_array_type, new_pointer_type(p), "foo")
    py.test.raises(ValueError, new_array_type, new_pointer_type(p), -42)
    #
    p1 = new_array_type(new_pointer_type(p), None)
    assert repr(p1) == "<ctype 'int[]'>"
    py.test.raises(ValueError, new_array_type, new_pointer_type(p1), 42)
    #
    p1 = new_array_type(new_pointer_type(p), 42)
    p2 = new_array_type(new_pointer_type(p1), 25)
    assert repr(p2) == "<ctype 'int[25][42]'>"
    p2 = new_array_type(new_pointer_type(p1), None)
    assert repr(p2) == "<ctype 'int[][42]'>"
    #
    py.test.raises(OverflowError,
                   new_array_type, new_pointer_type(p), sys.maxint+1)
    py.test.raises(OverflowError,
                   new_array_type, new_pointer_type(p), sys.maxint // 3)

def test_array_instance():
    LENGTH = 14242
    p = new_primitive_type("int")
    p1 = new_array_type(new_pointer_type(p), LENGTH)
    a = newp(p1, None)
    assert repr(a) == "<cdata 'int[%d]' owning %d bytes>" % (
        LENGTH, LENGTH * size_of_int())
    assert len(a) == LENGTH
    for i in range(LENGTH):
        assert a[i] == 0
    py.test.raises(IndexError, "a[LENGTH]")
    py.test.raises(IndexError, "a[-1]")
    for i in range(LENGTH):
        a[i] = i * i + 1
    for i in range(LENGTH):
        assert a[i] == i * i + 1
    e = py.test.raises(IndexError, "a[LENGTH+100] = 500")
    assert ('(expected %d < %d)' % (LENGTH+100, LENGTH)) in str(e.value)

def test_array_of_unknown_length_instance():
    p = new_primitive_type("int")
    p1 = new_array_type(new_pointer_type(p), None)
    py.test.raises(TypeError, newp, p1, None)
    py.test.raises(ValueError, newp, p1, -42)
    a = newp(p1, 42)
    assert len(a) == 42
    for i in range(42):
        a[i] -= i
    for i in range(42):
        assert a[i] == -i
    py.test.raises(IndexError, "a[42]")
    py.test.raises(IndexError, "a[-1]")
    py.test.raises(IndexError, "a[42] = 123")
    py.test.raises(IndexError, "a[-1] = 456")

def test_array_of_unknown_length_instance_with_initializer():
    p = new_primitive_type("int")
    p1 = new_array_type(new_pointer_type(p), None)
    a = newp(p1, range(42))
    assert len(a) == 42
    a = newp(p1, tuple(range(142)))
    assert len(a) == 142

def test_array_initializer():
    p = new_primitive_type("int")
    p1 = new_array_type(new_pointer_type(p), None)
    a = newp(p1, range(100, 142))
    for i in range(42):
        assert a[i] == 100 + i
    #
    p2 = new_array_type(new_pointer_type(p), 43)
    a = newp(p2, tuple(range(100, 142)))
    for i in range(42):
        assert a[i] == 100 + i
    assert a[42] == 0      # extra uninitialized item

def test_array_add():
    p = new_primitive_type("int")
    p1 = new_array_type(new_pointer_type(p), 5)    # int[5]
    p2 = new_array_type(new_pointer_type(p1), 3)   # int[3][5]
    a = newp(p2, [range(n, n+5) for n in [100, 200, 300]])
    assert repr(a) == "<cdata 'int[3][5]' owning %d bytes>" % (
        3*5*size_of_int(),)
    assert repr(a + 0) == "<cdata 'int(*)[5]'>"
    assert repr(a[0]) == "<cdata 'int[5]'>"
    assert repr((a + 0)[0]) == "<cdata 'int[5]'>"
    assert repr(a[0] + 0) == "<cdata 'int *'>"
    assert type(a[0][0]) is int
    assert type((a[0] + 0)[0]) is int

def test_cast_primitive_from_cdata():
    p = new_primitive_type("int")
    n = cast(p, cast(p, -42))
    assert int(n) == -42
    #
    p = new_primitive_type("unsigned int")
    n = cast(p, cast(p, 42))
    assert int(n) == 42
    #
    p = new_primitive_type("long long")
    n = cast(p, cast(p, -(1<<60)))
    assert int(n) == -(1<<60)
    #
    p = new_primitive_type("unsigned long long")
    n = cast(p, cast(p, 1<<63))
    assert int(n) == 1<<63
    #
    p = new_primitive_type("float")
    n = cast(p, cast(p, 42.5))
    assert float(n) == 42.5
    #
    p = new_primitive_type("char")
    n = cast(p, cast(p, "A"))
    assert str(n) == "A"

def test_new_primitive_from_cdata():
    p = new_primitive_type("int")
    p1 = new_pointer_type(p)
    n = newp(p1, cast(p, -42))
    assert n[0] == -42
    #
    p = new_primitive_type("unsigned int")
    p1 = new_pointer_type(p)
    n = newp(p1, cast(p, 42))
    assert n[0] == 42
    #
    p = new_primitive_type("float")
    p1 = new_pointer_type(p)
    n = newp(p1, cast(p, 42.5))
    assert n[0] == 42.5
    #
    p = new_primitive_type("char")
    p1 = new_pointer_type(p)
    n = newp(p1, cast(p, "A"))
    assert n[0] == "A"

def test_cast_between_pointers():
    BIntP = new_pointer_type(new_primitive_type("int"))
    BIntA = new_array_type(BIntP, None)
    a = newp(BIntA, [40, 41, 42, 43, 44])
    BShortP = new_pointer_type(new_primitive_type("short"))
    b = cast(BShortP, a)
    c = cast(BIntP, b)
    assert c[3] == 43
    BLongLong = new_primitive_type("long long")
    d = cast(BLongLong, c)
    e = cast(BIntP, d)
    assert e[3] == 43
    f = cast(BIntP, int(d))
    assert f[3] == 43
    #
    for null in [0, None]:
        b = cast(BShortP, null)
        assert not b
        c = cast(BIntP, b)
        assert not c
        assert int(cast(BLongLong, c)) == 0

def test_alignof():
    BInt = new_primitive_type("int")
    assert alignof(BInt) == sizeof(BInt)
    BPtr = new_pointer_type(BInt)
    assert alignof(BPtr) == sizeof(BPtr)
    BArray = new_array_type(BPtr, None)
    assert alignof(BArray) == alignof(BInt)

def test_new_struct_type():
    BStruct = new_struct_type("foo")
    assert repr(BStruct) == "<ctype 'struct foo'>"
    BPtr = new_pointer_type(BStruct)
    assert repr(BPtr) == "<ctype 'struct foo *'>"

def test_new_union_type():
    BUnion = new_union_type("foo")
    assert repr(BUnion) == "<ctype 'union foo'>"
    BPtr = new_pointer_type(BUnion)
    assert repr(BPtr) == "<ctype 'union foo *'>"

def test_complete_struct():
    BLong = new_primitive_type("long")
    BChar = new_primitive_type("char")
    BShort = new_primitive_type("short")
    BStruct = new_struct_type("foo")
    assert _getfields(BStruct) is None
    complete_struct_or_union(BStruct, [('a1', BLong, -1),
                                       ('a2', BChar, -1),
                                       ('a3', BShort, -1)])
    d = _getfields(BStruct)
    assert len(d) == 3
    assert d[0][0] == 'a1'
    assert d[0][1].type is BLong
    assert d[0][1].offset == 0
    assert d[0][1].bitshift == -1
    assert d[0][1].bitsize == -1
    assert d[1][0] == 'a2'
    assert d[1][1].type is BChar
    assert d[1][1].offset == sizeof(BLong)
    assert d[1][1].bitshift == -1
    assert d[1][1].bitsize == -1
    assert d[2][0] == 'a3'
    assert d[2][1].type is BShort
    assert d[2][1].offset == sizeof(BLong) + sizeof(BShort)
    assert d[2][1].bitshift == -1
    assert d[2][1].bitsize == -1
    assert sizeof(BStruct) == 2 * sizeof(BLong)
    assert alignof(BStruct) == alignof(BLong)

def test_complete_union():
    BLong = new_primitive_type("long")
    BChar = new_primitive_type("char")
    BUnion = new_union_type("foo")
    assert _getfields(BUnion) is None
    complete_struct_or_union(BUnion, [('a1', BLong, -1),
                                      ('a2', BChar, -1)])
    d = _getfields(BUnion)
    assert len(d) == 2
    assert d[0][0] == 'a1'
    assert d[0][1].type is BLong
    assert d[0][1].offset == 0
    assert d[1][0] == 'a2'
    assert d[1][1].type is BChar
    assert d[1][1].offset == 0
    assert sizeof(BUnion) == sizeof(BLong)
    assert alignof(BUnion) == alignof(BLong)

def test_struct_instance():
    BInt = new_primitive_type("int")
    BStruct = new_struct_type("foo")
    BStructPtr = new_pointer_type(BStruct)
    p = cast(BStructPtr, None)
    py.test.raises(AttributeError, "p.a1")    # opaque
    complete_struct_or_union(BStruct, [('a1', BInt, -1),
                                       ('a2', BInt, -1)])
    p = newp(BStructPtr, None)
    s = p[0]
    assert s.a1 == 0
    s.a2 = 123
    assert s.a1 == 0
    assert s.a2 == 123
    py.test.raises(OverflowError, "s.a1 = sys.maxint+1")
    assert s.a1 == 0
    py.test.raises(AttributeError, "p.foobar")
    py.test.raises(AttributeError, "s.foobar")

def test_struct_pointer():
    BInt = new_primitive_type("int")
    BStruct = new_struct_type("foo")
    BStructPtr = new_pointer_type(BStruct)
    complete_struct_or_union(BStruct, [('a1', BInt, -1),
                                       ('a2', BInt, -1)])
    p = newp(BStructPtr, None)
    assert p.a1 == 0      # read/write via the pointer (C equivalent: '->')
    p.a2 = 123
    assert p.a1 == 0
    assert p.a2 == 123

def test_struct_init_list():
    BInt = new_primitive_type("int")
    BStruct = new_struct_type("foo")
    BStructPtr = new_pointer_type(BStruct)
    complete_struct_or_union(BStruct, [('a1', BInt, -1),
                                       ('a2', BInt, -1),
                                       ('a3', BInt, -1)])
    s = newp(BStructPtr, [123, 456])
    assert s.a1 == 123
    assert s.a2 == 456
    assert s.a3 == 0

def test_array_in_struct():
    BInt = new_primitive_type("int")
    BStruct = new_struct_type("foo")
    BArrayInt5 = new_array_type(new_pointer_type(BInt), 5)
    complete_struct_or_union(BStruct, [('a1', BArrayInt5, -1)])
    s = newp(new_pointer_type(BStruct), [[20, 24, 27, 29, 30]])
    assert s.a1[2] == 27
    assert repr(s.a1) == "<cdata 'int[5]'>"

def test_offsetof():
    BInt = new_primitive_type("int")
    BStruct = new_struct_type("foo")
    py.test.raises(TypeError, offsetof, BInt, "abc")
    py.test.raises(TypeError, offsetof, BStruct, "abc")
    complete_struct_or_union(BStruct, [('abc', BInt, -1), ('def', BInt, -1)])
    assert offsetof(BStruct, 'abc') == 0
    assert offsetof(BStruct, 'def') == size_of_int()
    py.test.raises(KeyError, offsetof, BStruct, "ghi")

def test_function_type():
    BInt = new_primitive_type("int")
    BFunc = new_function_type((BInt, BInt), BInt, False)
    assert repr(BFunc) == "<ctype 'int(*)(int, int)'>"
    BFunc2 = new_function_type((), BFunc, False)
    assert repr(BFunc2) == "<ctype 'int(*(*)())(int, int)'>"

def test_function_type_taking_struct():
    BChar = new_primitive_type("char")
    BShort = new_primitive_type("short")
    BStruct = new_struct_type("foo")
    complete_struct_or_union(BStruct, [('a1', BChar, -1),
                                       ('a2', BShort, -1)])
    BFunc = new_function_type((BStruct,), BShort, False)
    assert repr(BFunc) == "<ctype 'short(*)(struct foo)'>"

def test_function_void_result():
    BVoid = new_void_type()
    BInt = new_primitive_type("int")
    BFunc = new_function_type((BInt, BInt), BVoid, False)
    assert repr(BFunc) == "<ctype 'void(*)(int, int)'>"

def test_call_function_0():
    BSignedChar = new_primitive_type("signed char")
    BFunc0 = new_function_type((BSignedChar, BSignedChar), BSignedChar, False)
    f = cast(BFunc0, _testfunc(0))
    assert f(40, 2) == 42
    assert f(-100, -100) == -200 + 256
    py.test.raises(OverflowError, f, 128, 0)
    py.test.raises(OverflowError, f, 0, 128)

def test_call_function_1():
    BInt = new_primitive_type("int")
    BLong = new_primitive_type("long")
    BFunc1 = new_function_type((BInt, BLong), BLong, False)
    f = cast(BFunc1, _testfunc(1))
    assert f(40, 2) == 42
    assert f(-100, -100) == -200
    int_max = (1 << (8*size_of_int()-1)) - 1
    long_max = (1 << (8*size_of_long()-1)) - 1
    if int_max == long_max:
        assert f(int_max, 1) == - int_max - 1
    else:
        assert f(int_max, 1) == int_max + 1

def test_call_function_2():
    BLongLong = new_primitive_type("long long")
    BFunc2 = new_function_type((BLongLong, BLongLong), BLongLong, False)
    f = cast(BFunc2, _testfunc(2))
    longlong_max = (1 << (8*sizeof(BLongLong)-1)) - 1
    assert f(longlong_max - 42, 42) == longlong_max
    assert f(43, longlong_max - 42) == - longlong_max - 1

def test_call_function_3():
    BFloat = new_primitive_type("float")
    BDouble = new_primitive_type("double")
    BFunc3 = new_function_type((BFloat, BDouble), BDouble, False)
    f = cast(BFunc3, _testfunc(3))
    assert f(1.25, 5.1) == 1.25 + 5.1     # exact
    res = f(1.3, 5.1)
    assert res != 6.4 and abs(res - 6.4) < 1E-5    # inexact

def test_call_function_4():
    BFloat = new_primitive_type("float")
    BDouble = new_primitive_type("double")
    BFunc4 = new_function_type((BFloat, BDouble), BFloat, False)
    f = cast(BFunc4, _testfunc(4))
    res = f(1.25, 5.1)
    assert res != 6.35 and abs(res - 6.35) < 1E-5    # inexact

def test_call_function_5():
    BVoid = new_void_type()
    BFunc5 = new_function_type((), BVoid, False)
    f = cast(BFunc5, _testfunc(5))
    f()   # did not crash

def test_call_function_6():
    BInt = new_primitive_type("int")
    BIntPtr = new_pointer_type(BInt)
    BFunc6 = new_function_type((BIntPtr,), BIntPtr, False)
    f = cast(BFunc6, _testfunc(6))
    x = newp(BIntPtr, 42)
    res = f(x)
    assert typeof(res) is BIntPtr
    assert res[0] == 42 - 1000
    #
    BIntArray = new_array_type(BIntPtr, None)
    BFunc6bis = new_function_type((BIntArray,), BIntPtr, False)
    f = cast(BFunc6bis, _testfunc(6))
    #
    py.test.raises(TypeError, f, [142])
    #
    x = newp(BIntArray, [242])
    res = f(x)
    assert typeof(res) is BIntPtr
    assert res[0] == 242 - 1000

def test_call_function_7():
    BChar = new_primitive_type("char")
    BShort = new_primitive_type("short")
    BStruct = new_struct_type("foo")
    BStructPtr = new_pointer_type(BStruct)
    complete_struct_or_union(BStruct, [('a1', BChar, -1),
                                       ('a2', BShort, -1)])
    BFunc7 = new_function_type((BStruct,), BShort, False)
    f = cast(BFunc7, _testfunc(7))
    res = f({'a1': 'A', 'a2': -4042})
    assert res == -4042 + ord('A')
    #
    x = newp(BStructPtr, {'a1': 'A', 'a2': -4042})
    res = f(x[0])
    assert res == -4042 + ord('A')

def test_call_function_9():
    BInt = new_primitive_type("int")
    BFunc9 = new_function_type((BInt,), BInt, True)    # vararg
    f = cast(BFunc9, _testfunc(9))
    assert f(0) == 0
    assert f(1, cast(BInt, 42)) == 42
    assert f(2, cast(BInt, 40), cast(BInt, 2)) == 42
    py.test.raises(TypeError, f, 1, 42)

def test_new_charp():
    BChar = new_primitive_type("char")
    BCharP = new_pointer_type(BChar)
    BCharA = new_array_type(BCharP, None)
    x = newp(BCharA, 42)
    assert len(x) == 42
    x = newp(BCharA, "foobar")
    assert len(x) == 7

def test_load_and_call_function():
    BChar = new_primitive_type("char")
    BCharP = new_pointer_type(BChar)
    BLong = new_primitive_type("long")
    BFunc = new_function_type((BCharP,), BLong, False)
    ll = find_and_load_library('c')
    strlen = ll.load_function(BFunc, "strlen")
    input = newp(new_array_type(BCharP, None), "foobar")
    assert strlen(input) == 6
    #
    assert strlen("foobarbaz") == 9

def test_read_variable():
    if sys.platform == 'win32':
        py.test.skip("untested")
    BVoidP = new_pointer_type(new_void_type())
    ll = find_and_load_library('c')
    stderr = ll.read_variable(BVoidP, "stderr")
    assert stderr == cast(BVoidP, _testfunc(8))

def test_write_variable():
    if sys.platform == 'win32':
        py.test.skip("untested")
    BVoidP = new_pointer_type(new_void_type())
    ll = find_and_load_library('c')
    stderr = ll.read_variable(BVoidP, "stderr")
    ll.write_variable(BVoidP, "stderr", None)
    assert ll.read_variable(BVoidP, "stderr") is None
    ll.write_variable(BVoidP, "stderr", stderr)
    assert ll.read_variable(BVoidP, "stderr") == stderr

def test_callback():
    BInt = new_primitive_type("int")
    def make_callback():
        def cb(n):
            return n + 1
        BFunc = new_function_type((BInt,), BInt, False)
        return callback(BFunc, cb)    # 'cb' and 'BFunc' go out of scope
    f = make_callback()
    assert f(-142) == -141

def test_a_lot_of_callbacks():
    BInt = new_primitive_type("int")
    def make_callback(m):
        def cb(n):
            return n + m
        BFunc = new_function_type((BInt,), BInt, False)
        return callback(BFunc, cb)    # 'cb' and 'BFunc' go out of scope
    #
    flist = [make_callback(i) for i in range(10000)]
    for i, f in enumerate(flist):
        assert f(-142) == -142 + i

def test_enum_type():
    BEnum = new_enum_type("foo", (), ())
    assert repr(BEnum) == "<ctype 'enum foo'>"
    assert _getfields(BEnum) == []
    #
    BEnum = new_enum_type("foo", ('def', 'c', 'ab'), (0, 1, -20))
    assert _getfields(BEnum) == [(-20, 'ab'), (0, 'def'), (1, 'c')]

def test_cast_to_enum():
    BEnum = new_enum_type("foo", ('def', 'c', 'ab'), (0, 1, -20))
    e = cast(BEnum, 0)
    assert repr(e) == "<cdata 'enum foo'>"
    assert str(e) == 'def'
    assert str(cast(BEnum, -20)) == 'ab'
    assert str(cast(BEnum, 'c')) == 'c'
    assert int(cast(BEnum, 'c')) == 1
    assert int(cast(BEnum, 'def')) == 0
    assert int(cast(BEnum, -242 + 2**128)) == -242
    assert str(cast(BEnum, -242 + 2**128)) == '#-242'
    assert str(cast(BEnum, '#-20')) == 'ab'

def test_enum_in_struct():
    BEnum = new_enum_type("foo", ('def', 'c', 'ab'), (0, 1, -20))
    BStruct = new_struct_type("bar")
    BStructPtr = new_pointer_type(BStruct)
    complete_struct_or_union(BStruct, [('a1', BEnum, -1)])
    p = newp(BStructPtr, [-20])
    assert p.a1 == "ab"
    p = newp(BStructPtr, ["c"])
    assert p.a1 == "c"
    e = py.test.raises(TypeError, newp, BStructPtr, [None])
    assert "must be a str or int, not NoneType" in str(e.value)

def test_struct_with_bitfields():
    BLong = new_primitive_type("long")
    BStruct = new_struct_type("foo")
    LONGBITS = 8 * sizeof(BLong)
    complete_struct_or_union(BStruct, [('a1', BLong, 1),
                                       ('a2', BLong, 2),
                                       ('a3', BLong, 3),
                                       ('a4', BLong, LONGBITS - 5)])
    d = _getfields(BStruct)
    assert d[0][1].offset == d[1][1].offset == d[2][1].offset == 0
    assert d[3][1].offset == sizeof(BLong)
    assert d[0][1].bitshift == 0
    assert d[0][1].bitsize == 1
    assert d[1][1].bitshift == 1
    assert d[1][1].bitsize == 2
    assert d[2][1].bitshift == 3
    assert d[2][1].bitsize == 3
    assert d[3][1].bitshift == 0
    assert d[3][1].bitsize == LONGBITS - 5
    assert sizeof(BStruct) == 2 * sizeof(BLong)
    assert alignof(BStruct) == alignof(BLong)

def test_bitfield_instance():
    BInt = new_primitive_type("int")
    BUnsignedInt = new_primitive_type("unsigned int")
    BStruct = new_struct_type("foo")
    complete_struct_or_union(BStruct, [('a1', BInt, 1),
                                       ('a2', BUnsignedInt, 2),
                                       ('a3', BInt, 3)])
    p = newp(new_pointer_type(BStruct), None)
    p.a1 = -1
    assert p.a1 == -1
    p.a1 = 0
    py.test.raises(OverflowError, "p.a1 = 2")
    assert p.a1 == 0
    #
    p.a1 = -1
    p.a2 = 3
    p.a3 = -4
    py.test.raises(OverflowError, "p.a3 = 4")
    e = py.test.raises(OverflowError, "p.a3 = -5")
    assert str(e.value) == ("value -5 outside the range allowed by the "
                            "bit field width: -4 <= x <= 3")
    assert p.a1 == -1 and p.a2 == 3 and p.a3 == -4
    #
    # special case for convenience: "int x:1", while normally signed,
    # allows also setting the value "1" (it still gets read back as -1)
    p.a1 = 1
    assert p.a1 == -1
    e = py.test.raises(OverflowError, "p.a1 = -2")
    assert str(e.value) == ("value -2 outside the range allowed by the "
                            "bit field width: -1 <= x <= 1")

def test_bitfield_instance_init():
    BInt = new_primitive_type("int")
    BStruct = new_struct_type("foo")
    complete_struct_or_union(BStruct, [('a1', BInt, 1)])
    py.test.raises(NotImplementedError, newp, new_pointer_type(BStruct), [-1])

def test_weakref():
    import weakref
    BInt = new_primitive_type("int")
    BPtr = new_pointer_type(BInt)
    weakref.ref(BInt)
    weakref.ref(newp(BPtr, 42))
    py.test.raises(TypeError, weakref.ref, cast(BPtr, 42))
    py.test.raises(TypeError, weakref.ref, cast(BInt, 42))
