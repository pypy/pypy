import autopath
    
class AppTest_Descriptor:

    def test_non_data_descr(self):
        class X(object):
            def f(self):
                return 42
        x = X()
        assert x.f() == 42
        x.f = 43
        assert x.f == 43
        del x.f
        assert x.f() == 42

    def test_member(self):
        import sys
        assert sys.stdin.softspace == 0
        assert file.softspace.__get__(sys.stdin) == 0
        sys.stdin.softspace = 1
        assert sys.stdin.softspace == 1
        file.softspace.__set__(sys.stdin, 0)
        assert sys.stdin.softspace == 0
        raises(TypeError, delattr, sys.stdin, 'softspace')
        raises(TypeError, file.softspace.__delete__, sys.stdin)

    def test_special_methods_returning_strings(self): 
        class A: 
            seen = []
            def __str__(self): 
                self.seen.append(1) 
            def __repr__(self): 
                self.seen.append(2) 
            def __oct__(self): 
                self.seen.append(3) 
            def __hex__(self): 
                self.seen.append(4) 

        inst = A()
        raises(TypeError, str, inst) 
        raises(TypeError, repr, inst) 
        raises(TypeError, oct, inst) 
        raises(TypeError, hex, inst) 
        assert A.seen == [1,2,3,4]
