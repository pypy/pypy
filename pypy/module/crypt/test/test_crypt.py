from pypy.conftest import gettestobjspace

class AppTestCrypt: 
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['crypt'])
    def test_crypt(self):
        import crypt 
        res = crypt.crypt("pass", "ab")
        assert isinstance(res, str)
        assert res 

