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
