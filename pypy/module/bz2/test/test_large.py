import py
from pypy.conftest import gettestobjspace


class AppTestBZ2File:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('bz2',))
        largetest_bz2 = py.path.local(__file__).dirpath().join("largetest.bz2")
        cls.w_compressed_data = cls.space.wrap(largetest_bz2.read())

    def test_decompress(self):
        from bz2 import decompress
        result = decompress(self.compressed_data)
        assert len(result) == 901179
