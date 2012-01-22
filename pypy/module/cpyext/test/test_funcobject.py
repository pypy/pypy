from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.pyobject import PyObject, make_ref, from_ref
from pypy.module.cpyext.funcobject import (
    PyFunctionObject, PyCodeObject, CODE_FLAGS)
from pypy.interpreter.function import Function, Method
from pypy.interpreter.pycode import PyCode

globals().update(CODE_FLAGS)

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
            def func(x, y, z): return x
            return func
        """)
        w_code = api.PyFunction_GetCode(w_function)
        assert w_code.co_name == "func"

        ref = make_ref(space, w_code)
        assert (from_ref(space, rffi.cast(PyObject, ref.c_ob_type)) is
                space.gettypeobject(PyCode.typedef))
        assert "func" == space.unwrap(
           from_ref(space, rffi.cast(PyCodeObject, ref).c_co_name))
        assert 3 == rffi.cast(PyCodeObject, ref).c_co_argcount
        api.Py_DecRef(ref)

    def test_co_flags(self, space, api):
        def get_flags(signature, body="pass"):
            w_code = space.appexec([], """():
                def func(%s): %s
                return func.__code__
            """ % (signature, body))
            ref = make_ref(space, w_code)
            co_flags = rffi.cast(PyCodeObject, ref).c_co_flags
            api.Py_DecRef(ref)
            return co_flags
        assert get_flags("x") == CO_NESTED | CO_OPTIMIZED | CO_NEWLOCALS
        assert get_flags("x", "exec x") == CO_NESTED | CO_NEWLOCALS
        assert get_flags("x, *args") & CO_VARARGS
        assert get_flags("x, **kw") & CO_VARKEYWORDS
        assert get_flags("x", "yield x") & CO_GENERATOR

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
