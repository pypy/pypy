
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
        raises(TypeError, setattr, m, '__dict__', {})

    def test_docstring(self):
        import sys
        foo = type(sys)('foo')
        assert foo.__name__ == 'foo'
        assert foo.__doc__ is None
        bar = type(sys)('bar','docstring')
        assert bar.__doc__ == 'docstring'

    def test___file__(self): 
        import sys, os
        if not hasattr(sys, "pypy_objspaceclass"):
            skip("need PyPy for sys.__file__ checking")
        assert sys.__file__ 
        assert os.path.basename(sys.__file__) == 'sys'

    def test_repr(self):
        import sys
        r = repr(sys)
        assert r == "<module 'sys' (built-in)>"
        
        import _exceptions # known to be in pypy/lib
        r = repr(_exceptions)
        assert r.startswith("<module '_exceptions' from ") and \
               'pypy/lib/_exceptions.py' in r and \
               r.endswith('>')
        nofile = type(_exceptions)('nofile', 'foo')
        assert repr(nofile) == "<module 'nofile' from ?>"

        m = type(_exceptions).__new__(type(_exceptions))
        assert repr(m).startswith("<module '?'")
