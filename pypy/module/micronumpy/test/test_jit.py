
from pypy.module.micronumpy.numarray import SingleDimArray, Add
from pypy.conftest import gettestobjspace
from pypy.jit.metainterp.test.test_basic import LLJitMixin

class FakeSpace(object):
    pass

class TestNumpyJIt(LLJitMixin):
    def setup_class(cls):
        cls.space = FakeSpace()
    
    def test_add(self):
        space = self.space
        
        def f(i):
            ar = SingleDimArray(i)
            if i:
                v = Add(ar, ar)
            else:
                v = ar
            return v.force().storage[3]

        self.meta_interp(f, [5])
