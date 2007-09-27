
"""
Tests for the zlib module.
"""

import zlib

from pypy.conftest import gettestobjspace

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
        expanded = 'some bytes which will be compressed'
        cls.w_expanded = cls.space.wrap(expanded)
        cls.w_compressed = cls.space.wrap(zlib.compress(expanded))


    def test_error(self):
        """
        zlib.error should be an exception class.
        """
        assert issubclass(self.zlib.error, Exception)


    def test_crc32(self):
        """
        When called with a string, zlib.crc32 should compute its CRC32 and
        return it as a signed 32 bit integer.
        """
        assert self.zlib.crc32('') == 0
        assert self.zlib.crc32('\0') == -771559539
        assert self.zlib.crc32('hello, world.') == -936931198


    def test_crc32_start_value(self):
        """
        When called with a string and an integer, zlib.crc32 should compute the
        CRC32 of the string using the integer as the starting value.
        """
        assert self.zlib.crc32('', 42) == 42
        assert self.zlib.crc32('\0', 42) == 163128923
        assert self.zlib.crc32('hello, world.', 42) == 1090960721
        hello = 'hello, '
        hellocrc = self.zlib.crc32(hello)
        world = 'world.'
        helloworldcrc = self.zlib.crc32(world, hellocrc)
        assert helloworldcrc == self.zlib.crc32(hello + world)


    def test_adler32(self):
        """
        When called with a string, zlib.crc32 should compute its adler 32
        checksum and return it as a signed 32 bit integer.
        """
        assert self.zlib.adler32('') == 1
        assert self.zlib.adler32('\0') == 65537
        assert self.zlib.adler32('hello, world.') == 571147447
        assert self.zlib.adler32('x' * 23) == -2122904887


    def test_adler32_start_value(self):
        """
        When called with a string and an integer, zlib.adler32 should compute
        the adler 32 checksum of the string using the integer as the starting
        value.
        """
        assert self.zlib.adler32('', 42) == 42
        assert self.zlib.adler32('\0', 42) == 2752554
        assert self.zlib.adler32('hello, world.', 42) == 606078176
        assert self.zlib.adler32('x' * 23, 42) == -2061104398
        hello = 'hello, '
        hellosum = self.zlib.adler32(hello)
        world = 'world.'
        helloworldsum = self.zlib.adler32(world, hellosum)
        assert helloworldsum == self.zlib.adler32(hello + world)


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
        raises(self.zlib.error, self.zlib.decompress, self.compressed[:-2])
        raises(self.zlib.error, self.zlib.decompress, 'foobar')
