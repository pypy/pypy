from py.test import raises, main

def otherfunc(a,b):
    assert a==b
    
def somefunc(x,y):
    otherfunc(x,y)

class FailingTests(object):
    def test_simple(self):
        def f():
            return 42
        def g():
            return 43

        assert f() == g()

    def test_not(self):
        def f():
            return 42
        assert not f()

    def test_complex_error(self):
        def f():
            return 44
        def g():
            return 43
        somefunc(f(), g())

    def test_z1_unpack_error():
        l = []
        a,b  = l

    def test_z2_type_error():
        l = 3
        a,b  = l

    def test_startswith():
        s = "123"
        g = "456"
        assert s.startswith(g) 

    def test_startswith_nested():
        def f():   
            return "123"
        def g():   
            return "456"
        assert f().startswith(g())

    def test_global_func():
        assert isinstance(globf(42), float)

    def test_instance(self):
        self.x = 6*7
        assert self.x != 42

    def test_compare(self):
        assert globf(10) < 5

    def test_try_finally(self):
        x = 1
        try:
            assert x == 0
        finally:
            x = 0

    def test_raises(self):
        s = 'qwe'
        raises(TypeError, "int(s)")

    def test_raises_doesnt(self):
        raises(IOError, "int('3')")

    def test_raise(self):
        raise ValueError("demo error")
        
    def test_tupleerror(self):
        a,b = [1]

    def test_reinterpret_fails(self):
        l = [1,2,3]
        a,b = l.pop()

    def test_some_error(self):
        if namenotexi:
            pass

def globf(x):
    return x+1

main()
