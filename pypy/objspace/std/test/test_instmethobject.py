import autopath

# NB. instmethobject.py has been removed,
# but the following tests still make sense

objspacename = 'std'

class AppTestInstMethObjectApp:
    def test_callBound(self):
        boundMethod = [1,2,3].__len__
        assert boundMethod() == 3
        raises(TypeError, boundMethod, 333)
    def test_callUnbound(self):
        unboundMethod = list.__len__
        assert unboundMethod([1,2,3]) == 3
        raises(TypeError, unboundMethod)
        raises(TypeError, unboundMethod, 333)
        raises(TypeError, unboundMethod, [1,2,3], 333)

    def test_getBound(self):
        def f(l,x): return l[x+1]
        bound = f.__get__('abcdef')
        assert bound(1) == 'c'
        raises(TypeError, bound)
        raises(TypeError, bound, 2, 3)
    def test_getUnbound(self):
        def f(l,x): return l[x+1]
        unbound = f.__get__(None, str)
        assert unbound('abcdef', 2) == 'd'
        raises(TypeError, unbound)
        raises(TypeError, unbound, 4)
        raises(TypeError, unbound, 4, 5)
