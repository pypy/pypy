from rpython.jit.metainterp.valueapi import *
from hypothesis import given, strategies as st
import sys

def test_const_none():
    c = valueapi.create_const(None)
    assert valueapi.is_constant(c)

def test_const_int():
    c = valueapi.create_const(123)
    assert valueapi.get_value_int(c) == 123
    assert valueapi.is_constant(c)
    assert valueapi.get_type(c) == TYPE_INT

def test_const_float():
    c = valueapi.create_const(5.4)
    assert valueapi.get_value_float(c) == 5.4
    assert valueapi.is_constant(c)
    assert valueapi.get_type(c) == TYPE_FLOAT

def test_box_none():
    b = valueapi.create_box(5, None)
    assert not valueapi.is_constant(b)
    assert valueapi.get_position(b) == 5

def test_box_int():
    b = valueapi.create_box(5, 123)
    assert valueapi.get_value_int(b) == 123
    assert not valueapi.is_constant(b)
    assert valueapi.get_position(b) == 5
    assert valueapi.get_type(b) == TYPE_INT

def test_box_float():
    b = valueapi.create_box(5, 5.4)
    assert valueapi.get_value_float(b) == 5.4
    assert not valueapi.is_constant(b)
    assert valueapi.get_position(b) == 5
    assert valueapi.get_type(b) == TYPE_FLOAT

@given(st.integers(-MAX_INT - 1, MAX_INT))
def test_gen_const_int(i):
    assert decode_const_int(encode_const_int(i)) == i

@given(st.integers(0, MAX_POS), st.integers(-MAX_INT - 1, MAX_INT))
def test_gen_box_int(pos, i):
    assert decode_int(encode_int(pos, i)) == (pos, i)

@given(st.integers(-MAX_INT - 1, MAX_INT))
def test_gen_const_int_erased(i):
    c = valueapi.create_const(i)
    assert valueapi.get_value_int(c) == i
    assert valueapi.is_constant(c)
    assert valueapi.get_type(c) == TYPE_INT

@given(st.integers(0, MAX_POS), st.integers(-MAX_INT - 1, MAX_INT))
def test_gen_box_int_erased(pos, i):
    b = valueapi.create_box(pos, i)
    assert valueapi.get_value_int(b) == i
    assert not valueapi.is_constant(b)
    assert valueapi.get_position(b) == pos
    assert valueapi.get_type(b) == TYPE_INT
