from pypy.objspace.std import StdObjSpace 

class AppTestCrypt: 
    def setup_class(cls):
        cls.space = StdObjSpace(usemodules=['crypt'])
    def test_crypt(self):
        import crypt 
        res = crypt.crypt("pass", "ab")
        assert isinstance(res, str)
        assert res 

