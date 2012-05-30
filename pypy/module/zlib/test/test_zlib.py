
"""
Tests for the zlib module.
"""

try:
    import zlib
except ImportError:
    import py; py.test.skip("no zlib module on this host Python")

try:
    from pypy.module.zlib import interp_zlib
except ImportError:
    import py; py.test.skip("no zlib C library on this machine")
 
from pypy.conftest import gettestobjspace

def test_unsigned_to_signed_32bit():
    assert interp_zlib.unsigned_to_signed_32bit(123) == 123
    assert interp_zlib.unsigned_to_signed_32bit(2**31) == -2**31
    assert interp_zlib.unsigned_to_signed_32bit(2**32-1) == -1


class AppTestZlib(object):
    def setup_class(cls):
        """
        Create a space with the zlib module and import it for use by the tests.
        Also create some compressed data with the bootstrap zlib module so that
        compression and decompression tests have a little real data to assert
        against.
        """
        cls.space = gettestobjspace(usemodules=['zlib'])
        cls.w_zlib = cls.space.appexec([], """():
            import zlib
            return zlib
        """)
        expanded = b'some bytes which will be compressed'
        cls.w_expanded = cls.space.wrapbytes(expanded)
        cls.w_compressed = cls.space.wrapbytes(zlib.compress(expanded))


    def test_error(self):
        """
        zlib.error should be an exception class.
        """
        assert issubclass(self.zlib.error, Exception)


    def test_crc32(self):
        """
        When called with a string, zlib.crc32 should compute its CRC32 and
        return it as a signed 32 bit integer.  On 64-bit machines too
        (it is a bug in CPython < 2.6 to return unsigned values in this case).
        """
        assert self.zlib.crc32(b'') == 0
        assert self.zlib.crc32(b'\0') == -771559539
        assert self.zlib.crc32(b'hello, world.') == -936931198


    def test_crc32_start_value(self):
        """
        When called with a string and an integer, zlib.crc32 should compute the
        CRC32 of the string using the integer as the starting value.
        """
        assert self.zlib.crc32(b'', 42) == 42
        assert self.zlib.crc32(b'\0', 42) == 163128923
        assert self.zlib.crc32(b'hello, world.', 42) == 1090960721
        hello = b'hello, '
        hellocrc = self.zlib.crc32(hello)
        world = b'world.'
        helloworldcrc = self.zlib.crc32(world, hellocrc)
        assert helloworldcrc == self.zlib.crc32(hello + world)

    def test_crc32_negative_start(self):
        v = self.zlib.crc32(b'', -1)
        assert v == -1

    def test_crc32_negative_long_start(self):
        v = self.zlib.crc32(b'', -1)
        assert v == -1
        assert self.zlib.crc32(b'foo', -99999999999999999999999) == 1611238463

    def test_crc32_long_start(self):
        import sys
        v = self.zlib.crc32(b'', sys.maxint*2)
        assert v == -2
        assert self.zlib.crc32(b'foo', 99999999999999999999999) == 1635107045

    def test_adler32(self):
        """
        When called with a string, zlib.adler32() should compute its adler 32
        checksum and return it as a signed 32 bit integer.
        On 64-bit machines too
        (it is a bug in CPython < 2.6 to return unsigned values in this case).
        """
        assert self.zlib.adler32(b'') == 1
        assert self.zlib.adler32(b'\0') == 65537
        assert self.zlib.adler32(b'hello, world.') == 571147447
        assert self.zlib.adler32(b'x' * 23) == -2122904887


    def test_adler32_start_value(self):
        """
        When called with a string and an integer, zlib.adler32 should compute
        the adler 32 checksum of the string using the integer as the starting
        value.
        """
        assert self.zlib.adler32(b'', 42) == 42
        assert self.zlib.adler32(b'\0', 42) == 2752554
        assert self.zlib.adler32(b'hello, world.', 42) == 606078176
        assert self.zlib.adler32(b'x' * 23, 42) == -2061104398
        hello = b'hello, '
        hellosum = self.zlib.adler32(hello)
        world = b'world.'
        helloworldsum = self.zlib.adler32(world, hellosum)
        assert helloworldsum == self.zlib.adler32(hello + world)

        assert self.zlib.adler32(b'foo', -1) == 45547858
        assert self.zlib.adler32(b'foo', 99999999999999999999999) == -114818734


    def test_invalidLevel(self):
        """
        zlib.compressobj should raise ValueError when an out of bounds level is
        passed to it.
        """
        raises(ValueError, self.zlib.compressobj, -2)
        raises(ValueError, self.zlib.compressobj, 10)


    def test_compression(self):
        """
        zlib.compressobj should return an object which can be used to compress
        bytes.
        """
        compressor = self.zlib.compressobj()
        bytes = compressor.compress(self.expanded)
        bytes += compressor.flush()
        assert bytes == self.compressed


    def test_decompression(self):
        """
        zlib.decompressobj should return an object which can be used to
        decompress bytes.
        """
        decompressor = self.zlib.decompressobj()
        bytes = decompressor.decompress(self.compressed)
        bytes += decompressor.flush()
        assert bytes == self.expanded


    def test_compress(self):
        """
        Test the zlib.compress() function.
        """
        bytes = self.zlib.compress(self.expanded)
        assert bytes == self.compressed


    def test_decompress(self):
        """
        Test the zlib.decompress() function.
        """
        bytes = self.zlib.decompress(self.compressed)
        assert bytes == self.expanded


    def test_decompress_invalid_input(self):
        """
        Try to feed garbage to zlib.decompress().
        """
        raises(self.zlib.error, self.zlib.decompress, self.compressed[:-2])
        raises(self.zlib.error, self.zlib.decompress, b'foobar')


    def test_unused_data(self):
        """
        Try to feed too much data to zlib.decompress().
        It should show up in the unused_data attribute.
        """
        d = self.zlib.decompressobj()
        s = d.decompress(self.compressed + b'extrastuff')
        assert s == self.expanded
        assert d.unused_data == b'extrastuff'
        # try again with several decompression steps
        d = self.zlib.decompressobj()
        s1 = d.decompress(self.compressed[:10])
        assert d.unused_data == b''
        s2 = d.decompress(self.compressed[10:-3])
        assert d.unused_data == b''
        s3 = d.decompress(self.compressed[-3:] + b'spam' * 100)
        assert d.unused_data == b'spam' * 100
        assert s1 + s2 + s3 == self.expanded
        s4 = d.decompress(b'egg' * 50)
        assert d.unused_data == b'egg' * 50
        assert s4 == b''


    def test_max_length(self):
        """
        Test the max_length argument of the decompress() method
        and the corresponding unconsumed_tail attribute.
        """
        d = self.zlib.decompressobj()
        data = self.compressed
        for i in range(0, 100, 10):
            s1 = d.decompress(data, 10)
            assert s1 == self.expanded[i:i+10]
            data = d.unconsumed_tail
        assert not data


    def test_buffer(self):
        """
        We should be able to pass buffer objects instead of strings.
        """
        assert self.zlib.crc32(memoryview(b'hello, world.')) == -936931198
        assert self.zlib.adler32(memoryview(b'hello, world.')) == 571147447

        compressor = self.zlib.compressobj()
        bytes = compressor.compress(memoryview(self.expanded))
        bytes += compressor.flush()
        assert bytes == self.compressed

        decompressor = self.zlib.decompressobj()
        bytes = decompressor.decompress(memoryview(self.compressed))
        bytes += decompressor.flush()
        assert bytes == self.expanded

        bytes = self.zlib.compress(memoryview(self.expanded))
        assert bytes == self.compressed

        bytes = self.zlib.decompress(memoryview(self.compressed))
        assert bytes == self.expanded
