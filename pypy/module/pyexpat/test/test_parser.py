from pypy.conftest import gettestobjspace
from pypy.module.pyexpat.interp_pyexpat import global_storage

class AppTestPyexpat:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['pyexpat'])

    def teardown_class(cls):
        global_storage.clear()

    def test_simple(self):
        import pyexpat
        p = pyexpat.ParserCreate()
        res = p.Parse("<xml></xml>")
        assert res == 1

        raises(pyexpat.ExpatError, p.Parse, "3")
