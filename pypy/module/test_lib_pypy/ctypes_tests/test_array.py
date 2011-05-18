
import py
from ctypes import *
from support import BaseCTypesTestChecker

formats = "bBhHiIlLqQfd"

formats = c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint, \
          c_long, c_ulonglong, c_float, c_double

class TestArray(BaseCTypesTestChecker):
    def test_simple(self):
        # create classes holding simple numeric types, and check
        # various properties.

        init = range(15, 25)

        for fmt in formats:
            alen = len(init)
            int_array = ARRAY(fmt, alen)

            ia = int_array(*init)
            # length of instance ok?
            assert len(ia) == alen

            # slot values ok?
            values = [ia[i] for i in range(len(init))]
            assert values == init

            # change the items
            from operator import setitem
            new_values = range(42, 42+alen)
            [setitem(ia, n, new_values[n]) for n in range(alen)]
            values = [ia[i] for i in range(len(init))]
            assert values == new_values

            # are the items initialized to 0?
            ia = int_array()
            values = [ia[i] for i in range(len(init))]
            assert values == [0] * len(init)

            # Too many in itializers should be caught
            py.test.raises(IndexError, int_array, *range(alen*2))

        CharArray = ARRAY(c_char, 3)

        ca = CharArray("a", "b", "c")

        # Should this work? It doesn't:
        # CharArray("abc")
        py.test.raises(TypeError, CharArray, "abc")

        assert ca[0] == "a"
        assert ca[1] == "b"
        assert ca[2] == "c"
        assert ca[-3] == "a"
        assert ca[-2] == "b"
        assert ca[-1] == "c"

        assert len(ca) == 3

        # slicing is now supported, but not extended slicing (3-argument)!
        from operator import getslice, delitem
        py.test.raises(TypeError, getslice, ca, 0, 1, -1)

        # cannot delete items
        py.test.raises(TypeError, delitem, ca, 0)

    def test_numeric_arrays(self):

        alen = 5

        numarray = ARRAY(c_int, alen)

        na = numarray()
        values = [na[i] for i in range(alen)]
        assert values == [0] * alen

        na = numarray(*[c_int()] * alen)
        values = [na[i] for i in range(alen)]
        assert values == [0]*alen

        na = numarray(1, 2, 3, 4, 5)
        values = [i for i in na]
        assert values == [1, 2, 3, 4, 5]

        na = numarray(*map(c_int, (1, 2, 3, 4, 5)))
        values = [i for i in na]
        assert values == [1, 2, 3, 4, 5]

    def test_slice(self):
        values = range(5)
        numarray = c_int * 5

        na = numarray(*(c_int(x) for x in values))

        assert list(na[0:0]) == []
        assert list(na[:])   == values
        assert list(na[:10]) == values

    def test_classcache(self):
        assert not ARRAY(c_int, 3) is ARRAY(c_int, 4)
        assert ARRAY(c_int, 3) is ARRAY(c_int, 3)

    def test_from_address(self):
        # Failed with 0.9.8, reported by JUrner
        p = create_string_buffer("foo")
        sz = (c_char * 3).from_address(addressof(p))
        assert sz[:] == "foo"
        assert sz.value == "foo"

    def test_init_again(self):
        sz = (c_char * 3)()
        addr1 = addressof(sz)
        sz.__init__(*"foo")
        addr2 = addressof(sz)
        assert addr1 == addr2

    try:
        create_unicode_buffer
    except NameError:
        pass
    else:
        def test_from_addressW(self):
            p = create_unicode_buffer("foo")
            sz = (c_wchar * 3).from_address(addressof(p))
            assert sz[:] == "foo"
            assert sz.value == "foo"

class TestSophisticatedThings(BaseCTypesTestChecker):
    def test_array_of_structures(self):
        class X(Structure):
            _fields_ = [('x', c_int), ('y', c_int)]

        Y = X * 2
        y = Y()
        x = X()
        x.y = 3
        y[1] = x
        assert y[1].y == 3
        
