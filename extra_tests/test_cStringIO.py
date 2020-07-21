"""
Tests for the PyPy cStringIO implementation.
"""
from cStringIO import StringIO

data = b"some bytes"

def test_reset():
    """
    Test that the reset method of cStringIO objects sets the position
    marker to the beginning of the stream.
    """
    stream = StringIO()
    stream.write(data)
    assert stream.read() == ''
    stream.reset()
    assert stream.read() == data

    stream = StringIO(data)
    assert stream.read() == data
    assert stream.read() == ''
    stream.reset()
    assert stream.read() == data
