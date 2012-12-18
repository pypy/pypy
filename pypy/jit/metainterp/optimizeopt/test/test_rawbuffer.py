import py
from pypy.jit.metainterp.optimizeopt.rawbuffer import (InvalidRawWrite,
                                                       InvalidRawRead, RawBuffer)

def test_write_value():
    buf = RawBuffer()
    buf.write_value(8, 4, 'three')
    buf.write_value(0, 4, 'one')
    buf.write_value(4, 2, 'two')
    buf.write_value(12, 2, 'four')
    assert buf._get_memory() == [
        ( 0, 4, 'one'),
        ( 4, 2, 'two'),
        ( 8, 4, 'three'),
        (12, 2, 'four'),
        ]
    #

def test_write_value_update():
    buf = RawBuffer()
    buf.write_value(0, 4, 'one')
    buf.write_value(4, 2, 'two')
    buf.write_value(0, 4, 'ONE')
    assert buf._get_memory() == [
        ( 0, 4, 'ONE'),
        ( 4, 2, 'two'),
        ]

def test_write_value_invalid_length():
    buf = RawBuffer()
    buf.write_value(0, 4, 'one')
    with py.test.raises(InvalidRawWrite):
        buf.write_value(0, 5, 'two')
    
def test_write_value_overlapping():
    buf = RawBuffer()
    buf.write_value(0, 4, 'one')
    buf.write_value(6, 4, 'two')
    with py.test.raises(InvalidRawWrite):
        buf.write_value(4, 4, 'three')

def test_read_value():
    buf = RawBuffer()
    buf.write_value(0, 4, 'one')
    buf.write_value(4, 4, 'two')
    assert buf.read_value(0, 4) == 'one'
    assert buf.read_value(4, 4) == 'two'
    with py.test.raises(InvalidRawRead):
        buf.read_value(0, 2)
    with py.test.raises(InvalidRawRead):
        buf.read_value(8, 2)
