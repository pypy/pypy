
from pypy.interpreter.module import Module

class TestModule: 
    def test_name(self, space):
        w = space.wrap
        m = Module(space, space.wrap('m'))
        w_m = w(m)
        assert space.eq_w(space.getattr(w_m, w('__name__')), w('m'))

    def test_attr(self, space):
        w = space.wrap
        w_m = w(Module(space, space.wrap('m')))
        self.space.setattr(w_m, w('x'), w(15))
        assert space.eq_w(space.getattr(w_m, w('x')), w(15))
        space.delattr(w_m, w('x'))
        space.raises_w(space.w_AttributeError,
                       space.delattr, w_m, w('x'))

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
        
        import _pypy_interact # known to be in pypy/lib
        r = repr(_pypy_interact)
        assert (r.startswith("<module '_pypy_interact' from ") and
                ('pypy/lib/_pypy_interact.py' in r or
                 r'pypy\\lib\\_pypy_interact.py' in r.lower()) and
                r.endswith('>'))
        nofile = type(_pypy_interact)('nofile', 'foo')
        assert repr(nofile) == "<module 'nofile' from ?>"

        m = type(_pypy_interact).__new__(type(_pypy_interact))
        assert repr(m).startswith("<module '?'")
