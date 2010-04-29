from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.interpreter.function import Function, Method

class TestClassObject(BaseApiTest):
    def test_newinstance(self, space, api):
        w_class = space.appexec([], """():
            class C:
                x = None
                def __init__(self):
                    self.x = 1
            return C
        """)

        assert api.PyClass_Check(w_class)

        w_instance = api.PyInstance_NewRaw(w_class, None)
        assert api.PyInstance_Check(w_instance)
        assert space.getattr(w_instance, space.wrap('x')) is space.w_None

        w_instance = api.PyInstance_NewRaw(w_class, space.wrap(dict(a=3)))
        assert space.getattr(w_instance, space.wrap('x')) is space.w_None
        assert space.unwrap(space.getattr(w_instance, space.wrap('a'))) == 3

    def test_lookup(self, space, api):
        w_instance = space.appexec([], """():
            class C:
                def __init__(self):
                    self.x = None
                def f(self): pass
            return C()
        """)

        assert api.PyInstance_Check(w_instance)
        assert api.PyObject_GetAttr(w_instance, space.wrap('x')) is space.w_None
        assert api._PyInstance_Lookup(w_instance, space.wrap('x')) is space.w_None
        assert api._PyInstance_Lookup(w_instance, space.wrap('y')) is None
        assert not api.PyErr_Occurred()

        # getattr returns a bound method
        assert not isinstance(api.PyObject_GetAttr(w_instance, space.wrap('f')), Function)
        # _PyInstance_Lookup returns the raw descriptor
        assert isinstance(api._PyInstance_Lookup(w_instance, space.wrap('f')), Function)
