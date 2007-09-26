"""
Tests for the struct module implemented at interp-level in pypy/module/struct.
"""

import py
from pypy.conftest import gettestobjspace


class AppTestStruct(object):

    def setup_class(cls):
        """
        Create a space with the struct module and import it for use by the
        tests.
        """
        cls.space = gettestobjspace(usemodules=['struct'])
        cls.w_struct = cls.space.call_function(
            cls.space.builtin.get('__import__'),
            cls.space.wrap('struct'))


    def test_error(self):
        """
        struct.error should be an exception class.
        """
        assert issubclass(self.struct.error, Exception)


    def test_calcsize_standard(self):
        """
        Check the standard size of the various format characters.
        """
        calcsize = self.struct.calcsize
        assert calcsize('=') == 0
        assert calcsize('<x') == 1
        assert calcsize('>c') == 1
        assert calcsize('!b') == 1
        assert calcsize('=B') == 1
        assert calcsize('<h') == 2
        assert calcsize('>H') == 2
        assert calcsize('!i') == 4
        assert calcsize('=I') == 4
        assert calcsize('<l') == 4
        assert calcsize('>L') == 4
        assert calcsize('!q') == 8
        assert calcsize('=Q') == 8
        assert calcsize('<f') == 4
        assert calcsize('>d') == 8
        assert calcsize('!13s') == 13
        assert calcsize('=500p') == 500
        # test with some repetitions and multiple format characters
        assert calcsize('=bQ3i') == 1 + 8 + 3*4


    def test_pack_standard_little(self):
        """
        Check packing with the '<' format specifier.
        """
        pack = self.struct.pack
        assert pack("<i", 0x41424344) == 'DCBA'


    def test_calcsize_native(self):
        """
        Check that the size of the various format characters is reasonable.
        """
        skip("in-progress")
        calcsize = self.struct.calcsize
        assert calcsize('') == 0
        assert calcsize('x') == 1
        assert calcsize('c') == 1
        assert calcsize('b') == 1
        assert calcsize('B') == 1
        assert (2 <= calcsize('h') == calcsize('H')
                  <  calcsize('i') == calcsize('I')
                  <= calcsize('l') == calcsize('L')
                  <= calcsize('q') == calcsize('Q'))
        assert 4 <= calcsize('f') <= 8 <= calcsize('d')
        assert calcsize('13s') == 13
        assert calcsize('500p') == 500
        assert 4 <= calcsize('P') <= 8
