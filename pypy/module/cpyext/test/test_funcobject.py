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

    def test_getcode(self, space, api):
        w_function = space.appexec([], """():
            def func(x): return x
            return func
        """)
        w_code = api.PyFunction_GetCode(w_function)
        assert w_code.co_name == "func"

    def test_newcode(self, space, api):
        filename = rffi.str2charp('filename')
        funcname = rffi.str2charp('funcname')
        w_code = api.PyCode_NewEmpty(filename, funcname, 3)
        assert w_code.co_filename == 'filename'
        assert w_code.co_firstlineno == 3
        rffi.free_charp(filename)
        rffi.free_charp(funcname)

    def test_classmethod(self, space, api):
        w_function = space.appexec([], """():
            def method(x): return x
            return method
        """)
        w_class = space.call_function(space.w_type, space.wrap("C"),
                                      space.newtuple([]), space.newdict())
        w_instance = space.call_function(w_class)
        # regular instance method
        space.setattr(w_class, space.wrap("method"), w_function)
        assert space.is_w(space.call_method(w_instance, "method"), w_instance)
        # now a classmethod
        w_classmethod = api.PyClassMethod_New(w_function)
        space.setattr(w_class, space.wrap("classmethod"), w_classmethod)
        assert space.is_w(space.call_method(w_instance, "classmethod"), w_class)
