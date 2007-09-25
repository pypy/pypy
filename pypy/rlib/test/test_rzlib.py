
"""
Tests for the rzlib module.
"""

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


def test_init_end():
    """
    deflateInit() followed by deflateEnd() should work and do nothing.
    """
    stream = rzlib.deflateInit()
    rzlib.deflateEnd(stream)


def test_compression():
    """
    Once we have got a deflate stream, rzlib.compress() and rzlib.flush()
    should allow us to compress bytes.
    """
    stream = rzlib.deflateInit()
    bytes = rzlib.compress(stream, expanded)
    bytes += rzlib.compress(stream, "", rzlib.Z_FINISH)
    rzlib.deflateEnd(stream)
    assert bytes == compressed


##def test_decompression(self):
##    """
##    zlib.decompressobj should return an object which can be used to
##    decompress bytes.
##    """
##    decompressor = self.zlib.decompressobj()
##    bytes = decompressor.decompress(self.compressed)
##    bytes += decompressor.flush()
##    assert bytes == self.expanded
