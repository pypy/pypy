# -*- coding: iso-8859-1 -*-

class AppTestObject: 
    def test_hash_builtin(self):
        o = object()
        assert hash(o) == id(o) 

    def test_hash_method(self):
        o = object()
        assert hash(o) == o.__hash__() 

    def test_hash_list(self):
        l = range(5)
        raises(TypeError, hash, l)

    def test_no_getnewargs(self):
        o = object()
        assert not hasattr(o, '__getnewargs__')
