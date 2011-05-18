
"""
Tests for the rzlib module.
"""

import py
from pypy.rlib import rzlib
from pypy.rlib.rarithmetic import r_uint
import zlib

expanded = 'some bytes which will be compressed'
compressed = zlib.compress(expanded)


def test_crc32():
    """
    When called with a string, rzlib.crc32 should compute its CRC32 and
    return it as a unsigned 32 bit integer.
    """
    assert rzlib.crc32('') == r_uint(0)
    assert rzlib.crc32('\0') == r_uint(3523407757)
    assert rzlib.crc32('hello, world.') == r_uint(3358036098)


def test_crc32_start_value():
    """
    When called with a string and an integer, zlib.crc32 should compute the
    CRC32 of the string using the integer as the starting value.
    """
    assert rzlib.crc32('', 42) == r_uint(42)
    assert rzlib.crc32('\0', 42) == r_uint(163128923)
    assert rzlib.crc32('hello, world.', 42) == r_uint(1090960721)
    hello = 'hello, '
    hellocrc = rzlib.crc32(hello)
    world = 'world.'
    helloworldcrc = rzlib.crc32(world, hellocrc)
    assert helloworldcrc == rzlib.crc32(hello + world)


def test_adler32():
    """
    When called with a string, zlib.crc32 should compute its adler 32
    checksum and return it as an unsigned 32 bit integer.
    """
    assert rzlib.adler32('') == r_uint(1)
    assert rzlib.adler32('\0') == r_uint(65537)
    assert rzlib.adler32('hello, world.') == r_uint(571147447)
    assert rzlib.adler32('x' * 23) == r_uint(2172062409)


def test_adler32_start_value():
    """
    When called with a string and an integer, zlib.adler32 should compute
    the adler 32 checksum of the string using the integer as the starting
    value.
    """
    assert rzlib.adler32('', 42) == r_uint(42)
    assert rzlib.adler32('\0', 42) == r_uint(2752554)
    assert rzlib.adler32('hello, world.', 42) == r_uint(606078176)
    assert rzlib.adler32('x' * 23, 42) == r_uint(2233862898)
    hello = 'hello, '
    hellosum = rzlib.adler32(hello)
    world = 'world.'
    helloworldsum = rzlib.adler32(world, hellosum)
    assert helloworldsum == rzlib.adler32(hello + world)


def test_invalidLevel():
    """
    deflateInit() should raise ValueError when an out of bounds level is
    passed to it.
    """
    raises(ValueError, rzlib.deflateInit, -2)
    raises(ValueError, rzlib.deflateInit, 10)


def test_deflate_init_end():
    """
    deflateInit() followed by deflateEnd() should work and do nothing.
    """
    stream = rzlib.deflateInit()
    rzlib.deflateEnd(stream)


def test_compression():
    """
    Once we have got a deflate stream, rzlib.compress() 
    should allow us to compress bytes.
    """
    stream = rzlib.deflateInit()
    bytes = rzlib.compress(stream, expanded)
    bytes += rzlib.compress(stream, "", rzlib.Z_FINISH)
    rzlib.deflateEnd(stream)
    assert bytes == compressed


def test_compression_lots_of_data():
    """
    Test compression of more data that fits in a single internal output buffer.
    """
    expanded = repr(range(20000))
    compressed = zlib.compress(expanded)
    print len(expanded), '=>', len(compressed)
    stream = rzlib.deflateInit()
    bytes = rzlib.compress(stream, expanded, rzlib.Z_FINISH)
    rzlib.deflateEnd(stream)
    assert bytes == compressed


def test_inflate_init_end():
    """
    inflateInit() followed by inflateEnd() should work and do nothing.
    """
    stream = rzlib.inflateInit()
    rzlib.inflateEnd(stream)


def test_decompression():
    """
    Once we have got a inflate stream, rzlib.decompress()
    should allow us to decompress bytes.
    """
    stream = rzlib.inflateInit()
    bytes1, finished1, unused1 = rzlib.decompress(stream, compressed)
    bytes2, finished2, unused2 = rzlib.decompress(stream, "", rzlib.Z_FINISH)
    rzlib.inflateEnd(stream)
    assert bytes1 + bytes2 == expanded
    assert finished1 is True
    assert finished2 is True
    assert unused1 == 0
    assert unused2 == 0


def test_decompression_lots_of_data():
    """
    Test compression of more data that fits in a single internal output buffer.
    """
    expanded = repr(range(20000))
    compressed = zlib.compress(expanded)
    print len(compressed), '=>', len(expanded)
    stream = rzlib.inflateInit()
    bytes, finished, unused = rzlib.decompress(stream, compressed,
                                               rzlib.Z_FINISH)
    rzlib.inflateEnd(stream)
    assert bytes == expanded
    assert finished is True
    assert unused == 0


def test_decompression_truncated_input():
    """
    Test that we can accept incomplete input when inflating, but also
    detect this situation when using Z_FINISH.
    """
    expanded = repr(range(20000))
    compressed = zlib.compress(expanded)
    print len(compressed), '=>', len(expanded)
    stream = rzlib.inflateInit()
    data, finished1, unused1 = rzlib.decompress(stream, compressed[:1000])
    assert expanded.startswith(data)
    assert finished1 is False
    assert unused1 == 0
    data2, finished2, unused2 = rzlib.decompress(stream, compressed[1000:2000])
    data += data2
    assert finished2 is False
    assert unused2 == 0
    assert expanded.startswith(data)
    exc = py.test.raises(
        rzlib.RZlibError,
        rzlib.decompress, stream, compressed[2000:-500], rzlib.Z_FINISH)
    msg = "Error -5 while decompressing data: incomplete or truncated stream"
    assert str(exc.value) == msg
    rzlib.inflateEnd(stream)


def test_decompression_too_much_input():
    """
    Check the case where we feed extra data to decompress().
    """
    stream = rzlib.inflateInit()
    data1, finished1, unused1 = rzlib.decompress(stream, compressed[:-5])
    assert finished1 is False
    assert unused1 == 0
    data2, finished2, unused2 = rzlib.decompress(stream,
                                                 compressed[-5:] + 'garbage')
    assert finished2 is True
    assert unused2 == len('garbage')
    assert data1 + data2 == expanded
    data3, finished3, unused3 = rzlib.decompress(stream, 'more_garbage')
    assert finished3 is True
    assert unused3 == len('more_garbage')
    assert data3 == ''

    rzlib.deflateEnd(stream)


def test_decompress_max_length():
    """
    Test the max_length argument of decompress().
    """
    stream = rzlib.inflateInit()
    data1, finished1, unused1 = rzlib.decompress(stream, compressed,
                                                 max_length = 17)
    assert data1 == expanded[:17]
    assert finished1 is False
    assert unused1 > 0
    data2, finished2, unused2 = rzlib.decompress(stream, compressed[-unused1:])
    assert data2 == expanded[17:]
    assert finished2 is True
    assert unused2 == 0

    rzlib.deflateEnd(stream)


def test_cornercases():
    """
    Test degenerate arguments.
    """
    stream = rzlib.deflateInit()
    bytes = rzlib.compress(stream, "")
    bytes += rzlib.compress(stream, "")
    bytes += rzlib.compress(stream, "", rzlib.Z_FINISH)
    assert zlib.decompress(bytes) == ""
    rzlib.deflateEnd(stream)

    stream = rzlib.inflateInit()
    data, finished, unused = rzlib.decompress(stream, "")
    assert data == ""
    assert finished is False
    assert unused == 0
    buf = compressed
    for i in range(10):
        data, finished, unused = rzlib.decompress(stream, buf, max_length=0)
        assert data == ""
        assert finished is False
        assert unused > 0
        buf = buf[-unused:]
    rzlib.deflateEnd(stream)
