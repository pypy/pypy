from rpython.jit.metainterp.valueapi import *

def test_const_none():
    c = valueapi.create_const(None)
    assert valueapi.get_value(c) is None
    assert valueapi.is_constant(c)

def test_const_int():
    c = valueapi.create_const(123)
    assert valueapi.get_value(c) == 123
    assert valueapi.is_constant(c)
    assert valueapi.get_type(c) == TYPE_INT

def test_const_float():
    c = valueapi.create_const(5.4)
    assert valueapi.get_value(c) == 5.4
    assert valueapi.is_constant(c)
    assert valueapi.get_type(c) == TYPE_FLOAT

def test_box_none():
    b = valueapi.create_box(5, None)
    assert valueapi.get_value(b) is None
    assert not valueapi.is_constant(b)
    assert valueapi.get_position(b) == 5

def test_box_int():
    b = valueapi.create_box(5, 123)
    assert valueapi.get_value(b) == 123
    assert not valueapi.is_constant(b)
    assert valueapi.get_position(b) == 5
    assert valueapi.get_type(b) == TYPE_INT

def test_box_float():
    b = valueapi.create_box(5, 5.4)
    assert valueapi.get_value(b) == 5.4
    assert not valueapi.is_constant(b)
    assert valueapi.get_position(b) == 5
    assert valueapi.get_type(b) == TYPE_FLOAT
