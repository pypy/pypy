
import autopath
from pypy.interpreter.module import Module

class TestModule: 
    def setup_class(cls):
        cls.m = Module(cls.space, cls.space.wrap('m'))
    def teardown_class(cls):
        del cls.m 

    def test_name(self):
        w = self.space.wrap
        w_m = w(self.m)
        assert self.space.eq_w(self.space.getattr(w_m, w('__name__')), w('m'))

    def test_attr(self):
        w = self.space.wrap
        w_m = w(self.m)
        self.space.setattr(w_m, w('x'), w(15))
        assert self.space.eq_w(self.space.getattr(w_m, w('x')), w(15))
        self.space.delattr(w_m, w('x'))
        self.space.raises_w(self.space.w_AttributeError,
                            self.space.delattr, w_m, w('x'))

class AppTest_ModuleObject: 
    def test_attr(self):
        m = __import__('__builtin__')
        m.x = 15
        assert m.x == 15
        assert getattr(m, 'x') == 15
        setattr(m, 'x', 23)
        assert m.x == 23
        assert getattr(m, 'x') == 23
        del m.x
        raises(AttributeError, getattr, m, 'x')
        m.x = 15
        delattr(m, 'x')
        raises(AttributeError, getattr, m, 'x')
        raises(AttributeError, delattr, m, 'x')
