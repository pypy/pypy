class AppTestCrypt: 
    spaceconfig = dict(usemodules=['crypt'])
 
   def test_crypt(self):
        import crypt 
        res = crypt.crypt("pass", "ab")
        assert isinstance(res, str)
        assert res 

