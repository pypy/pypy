import pytest
from ctypes import *

def test_slice():
    values = range(5)
    numarray = c_int * 5

    na = numarray(*(c_int(x) for x in values))

    assert list(na[0:0]) == []
    assert list(na[:])   == values
    assert list(na[:10]) == values

def test_init_again():
    sz = (c_char * 3)()
    addr1 = addressof(sz)
    sz.__init__(*"foo")
    addr2 = addressof(sz)
    assert addr1 == addr2

def test_array_of_structures():
    class X(Structure):
        _fields_ = [('x', c_int), ('y', c_int)]

    Y = X * 2
    y = Y()
    x = X()
    x.y = 3
    y[1] = x
    assert y[1].y == 3

def test_output_simple():
    A = c_char * 10
    TP = POINTER(A)
    x = TP(A())
    assert x[0] != ''

    A = c_wchar * 10
    TP = POINTER(A)
    x = TP(A())
    assert x[0] != ''

def test_output_simple_array():
    A = c_char * 10
    AA = A * 10
    aa = AA()
    assert aa[0] != ''

def test_output_complex_test():
    class Car(Structure):
        _fields_ = [("brand", c_char * 10),
                    ("speed", c_float),
                    ("owner", c_char * 10)]

    assert isinstance(Car("abcdefghi", 42.0, "12345").brand, bytes)
    assert Car("abcdefghi", 42.0, "12345").brand == "abcdefghi"
    assert Car("abcdefghio", 42.0, "12345").brand == "abcdefghio"
    with pytest.raises(ValueError):
        Car("abcdefghiop", 42.0, "12345")

    A = Car._fields_[2][1]
    TP = POINTER(A)
    x = TP(A())
    assert x[0] != ''
