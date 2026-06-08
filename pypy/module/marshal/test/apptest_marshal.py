import marshal
import sys


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def marshal_check(case):
    from io import BytesIO
    s = marshal.dumps(case)
    x = marshal.loads(s)
    assert x == case and type(x) is type(case)

    y = marshal.loads(memoryview(s))
    assert y == case and type(y) is type(case)

    if '__pypy__' in sys.builtin_module_names:
        f = BytesIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case and type(x) is type(case)
    return x


# ---------------------------------------------------------------------------
# Basic scalars
# ---------------------------------------------------------------------------

def test_None():
    marshal_check(None)

def test_False():
    marshal_check(False)

def test_True():
    marshal_check(True)

def test_StopIteration():
    marshal_check(StopIteration)

def test_Ellipsis():
    marshal_check(Ellipsis)

def test_42():
    marshal_check(42)

def test_minus_17():
    marshal_check(-17)

def test_sys_maxsize():
    marshal_check(sys.maxsize)

def test_minus_1_dot_25():
    marshal_check(-1.25)

def test_2_plus_5j():
    marshal_check(2+5j)

def test_long():
    marshal_check(-1234567890123456789012345678901234567890)


# ---------------------------------------------------------------------------
# Strings
# ---------------------------------------------------------------------------

def test_hello_not_interned():
    hello = "he"
    hello += "llo"
    marshal_check(hello)

def test_hello_interned():
    marshal_check("hello")

def test_bytes():
    marshal_check(b'hello')

def test_unicode():
    marshal_check('\uFFFF')
    marshal_check('\ud800')
    c = u"\ud800"
    marshal_check(c + u'\udc00')
    marshal_check(chr(sys.maxunicode))

def test_unmarshal_ascii():
    s = marshal.loads(b"a\x04\x00\x00\x00abcd")
    assert s == u"abcd"

def test_marshal_ascii():
    s = marshal.dumps("a")
    assert s.endswith(b"\x01a")
    s = marshal.dumps("a" * 1000)
    assert s == b"\xe1\xe8\x03\x00\x00" + b"a" * 1000
    for x in ("?" * 255, "a" * 1000, "xyza"):
        s = marshal.dumps(x)
        s1 = marshal.dumps((x, x))  # check that sharing works
        # The outer tuple is at ref index 0, the string at index 1.
        assert s1 == b"\xa9\x02" + s + b"r\x01\x00\x00\x00"

def test_shared_string():
    x = "hello, "
    x += "world"
    xl = 256
    xl **= 100
    for version in [2, 3]:
        s = marshal.dumps((x, x), version)
        assert s.count(b'hello, world') == 2 if version < 3 else 1
        y = marshal.loads(s)
        assert y == (x, x)
        #
        s = marshal.dumps((xl, xl), version)
        if version < 3:
            assert 200 < len(s) < 250
        else:
            assert 100 < len(s) < 125
        yl = marshal.loads(s)
        assert yl == (xl, xl)

def test_ascii_bug():
    with raises(ValueError):
        # TYPE_ASCII but not actually ascii
        marshal.loads(b'a\x01\0\0\0\xff')


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

def test_empty_tuple():
    marshal_check(())

def test_tuple_1_2():
    marshal_check((1, 2))

def test_empty_list():
    marshal_check([])

def test_list_3_4():
    marshal_check([3, 4])

def test_empty_dict():
    marshal_check({})

def test_dict_5_6_7_8():
    marshal_check({5: 6, 7: 8})

def test_empty_set():
    marshal_check(set())

def test_set_1_2():
    marshal_check(set([1, 2]))

def test_empty_frozenset():
    marshal_check(frozenset())

def test_frozenset_3_4():
    marshal_check(frozenset([3, 4]))

def test_list_recursive():
    l = []
    l.append(l)
    b = marshal.dumps(l)
    l2 = marshal.loads(b)
    assert len(l2) == 1
    assert l2[0] is l2


# ---------------------------------------------------------------------------
# Sharing / instancing (v3+)
# ---------------------------------------------------------------------------

def test_shared_tuple():
    t = (1, "hello")
    for version in [2, 3]:
        s = marshal.dumps((t, t), version)
        y = marshal.loads(s)
        assert y == (t, t)

def test_tuple_sharing_identity():
    # v3+: the same tuple object should be reused (not serialized twice)
    t = (1, "hello")
    for version in [3, 4]:
        s = marshal.dumps((t, t), version)
        y = marshal.loads(s)
        assert y == (t, t)
        assert y[0] is y[1]

def test_tuple_sharing_nested_in_list():
    # A tuple appearing twice inside a list should share identity on load
    inner = (42, "abc")
    lst = [inner, inner]
    for version in [3, 4]:
        data = marshal.dumps(lst, version)
        loaded = marshal.loads(data)
        assert loaded[0] is loaded[1]

def test_tuple_sharing_nested_in_dict():
    # A tuple appearing as two values in a dict should share identity on load
    val = (42, "abc")
    d = {"x": val, "y": val}
    for version in [3, 4]:
        data = marshal.dumps(d, version)
        loaded = marshal.loads(data)
        assert loaded["x"] is loaded["y"]


# ---------------------------------------------------------------------------
# Code objects
# ---------------------------------------------------------------------------

def test_code_object():
    def foo(a, b):
        pass
    s = marshal.dumps(foo.__code__)
    code2 = marshal.loads(s)
    for attr_name in dir(code2):
        if attr_name.startswith("co_"):
            if callable(getattr(code2, attr_name)):  # co_lines, co_positions
                assert list(getattr(code2, attr_name)()) == list(getattr(foo.__code__, attr_name)())
            else:
                assert getattr(code2, attr_name) == getattr(foo.__code__, attr_name)

def test_code_positions():
    def foo(a, b):
        return (
            a.x +
                b.y
        )
    s = marshal.dumps(foo.__code__)
    code2 = marshal.loads(s)
    assert list(code2.co_positions()) == list(foo.__code__.co_positions())

def test_func_code():
    def func(x):
        return lambda y: x+y
    marshal_check(func.__code__)

def test_scopefunc_code():
    def func(x):
        return lambda y: x+y
    scopefunc = func(42)
    marshal_check(scopefunc.__code__)

def test_co_filename_bug():
    code = compile('pass', 'tmp-\udcff.py', "exec")
    res = marshal.dumps(code)  # must not crash
    code2 = marshal.loads(res)
    assert code.co_filename == code2.co_filename


# ---------------------------------------------------------------------------
# Buffer-like objects
# ---------------------------------------------------------------------------

def test_marshal_bufferlike_object():
    s = marshal.dumps(memoryview(b'asd'))
    t = marshal.loads(s)
    assert type(t) is bytes and t == b'asd'

    s = marshal.dumps(memoryview(bytearray(b'asd')))
    t = marshal.loads(s)
    assert type(t) is bytes and t == b'asd'


# ---------------------------------------------------------------------------
# Stream I/O
# ---------------------------------------------------------------------------

def test_stream_reader_writer():
    import tempfile, os
    obj1 = [4, ("hello", 7.5)]
    obj2 = "foobar"
    fd, tmpfile = tempfile.mkstemp()
    os.close(fd)
    try:
        f = open(tmpfile, 'wb')
        marshal.dump(obj1, f)
        marshal.dump(obj2, f)
        f.write(b'END')
        f.close()
        f = open(tmpfile, 'rb')
        obj1b = marshal.load(f)
        obj2b = marshal.load(f)
        tail = f.read()
        f.close()
        assert obj1b == obj1
        assert obj2b == obj2
        assert tail == b'END'
    finally:
        os.unlink(tmpfile)


# ---------------------------------------------------------------------------
# Error / edge cases
# ---------------------------------------------------------------------------

def test_unmarshal_evil_long():
    raises(ValueError, marshal.loads, b'l\x02\x00\x00\x00\x00\x00\x00\x00')

def test_int64():
    assert marshal.loads(b'I\xff\xff\xff\xff\xff\xff\xff\x7f') == 0x7fffffffffffffff
    assert marshal.loads(b'I\xfe\xdc\xba\x98\x76\x54\x32\x10') == 0x1032547698badcfe
    assert marshal.loads(b'I\x01\x23\x45\x67\x89\xab\xcd\xef') == -0x1032547698badcff
    assert marshal.loads(b'I\x08\x19\x2a\x3b\x4c\x5d\x6e\x7f') == 0x7f6e5d4c3b2a1908
    assert marshal.loads(b'I\xf7\xe6\xd5\xc4\xb3\xa2\x91\x80') == -0x7f6e5d4c3b2a1909

def test_bad_typecode():
    exc = raises(ValueError, marshal.loads, bytes([1]))
    assert str(exc.value).startswith("bad marshal data (unknown type code")

def test_bad_reader():
    import io
    class BadReader(io.BytesIO):
        def read(self, n=-1):
            b = super().read(n)
            if n is not None and n > 4:
                b += b' ' * 10**6
            return b
    for value in (1.0, 1j, b'0123456789', '0123456789'):
        raises(ValueError, marshal.load, BadReader(marshal.dumps(value)))

def test_reject_subtypes():
    types = (float, complex, int, tuple, list, dict, set, frozenset)
    for cls in types:
        class subtype(cls):
            pass
        exc = raises(ValueError, marshal.dumps, subtype)
        assert str(exc.value) == 'unmarshallable object'
        exc = raises(ValueError, marshal.dumps, subtype())
        assert str(exc.value) == 'unmarshallable object'
        exc = raises(ValueError, marshal.dumps, (subtype(),))
        assert str(exc.value) == 'unmarshallable object'

def test_valid_subtypes():
    class subtype(bytearray):
        pass
    assert marshal.dumps(subtype(b'test')) == marshal.dumps(bytearray(b'test'))
