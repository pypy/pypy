from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.pyobject import PyObject, make_ref, from_ref
from pypy.module.cpyext.funcobject import PyFunctionObject
from pypy.interpreter.function import Function, Method

class TestFunctionObject(BaseApiTest):
    def test_function(self, space, api):
        w_function = space.appexec([], """():
            def f(): pass
            return f
        """)
        ref = make_ref(space, w_function)
        assert (from_ref(space, rffi.cast(PyObject, ref.c_ob_type)) is
                space.gettypeobject(Function.typedef))
        assert "f" == space.unwrap(
           from_ref(space, rffi.cast(PyFunctionObject, ref).c_func_name))
        api.Py_DecRef(ref)

    def test_method(self, space, api):
        w_method = space.appexec([], """():
            class C(list):
                def method(self): pass
            return C().method
        """)

        w_function = space.getattr(w_method, space.wrap("im_func"))
        w_self = space.getattr(w_method, space.wrap("im_self"))
        w_class = space.getattr(w_method, space.wrap("im_class"))

        assert space.is_w(api.PyMethod_Function(w_method), w_function)
        assert space.is_w(api.PyMethod_Self(w_method), w_self)
        assert space.is_w(api.PyMethod_Class(w_method), w_class)

        w_method2 = api.PyMethod_New(w_function, w_self, w_class)
        assert space.eq_w(w_method, w_method2)
