import py
from pypy.conftest import gettestobjspace, option


class AppTestBZ2File:
    def setup_class(cls):
        if not option.runappdirect:
            py.test.skip("skipping this very slow test; try 'pypy-c -A'")
        cls.space = gettestobjspace(usemodules=('bz2',))
        largetest_bz2 = py.path.local(__file__).dirpath().join("largetest.bz2")
        cls.w_compressed_data = cls.space.wrap(largetest_bz2.read('rb'))

    def test_decompress(self):
        from bz2 import decompress
        result = decompress(self.compressed_data)
        assert len(result) == 901179
