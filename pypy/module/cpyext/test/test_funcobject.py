from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.pyobject import PyObject, make_ref, from_ref, decref
from pypy.module.cpyext.methodobject import PyClassMethod_New
from pypy.module.cpyext.funcobject import (
    PyFunctionObject, PyCodeObject, CODE_FLAGS, PyMethod_Function,
    PyMethod_Self, PyMethod_New, PyFunction_GetCode, PyFunction_GetModule,
    PyCode_NewEmpty, PyCode_Addr2Line)
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.interpreter.function import Function
from pypy.interpreter.pycode import PyCode

globals().update(CODE_FLAGS)

class TestFunctionObject(BaseApiTest):
    def test_function(self, space):
        w_function = space.appexec([], """():
            def f(): pass
            return f
        """)
        ref = make_ref(space, w_function)
        assert (from_ref(space, rffi.cast(PyObject, ref.c_ob_type)) is
                space.gettypeobject(Function.typedef))
        assert "f" == space.unwrap(
            from_ref(space, rffi.cast(PyFunctionObject, ref).c_func_name))
        decref(space, ref)

    def test_method(self, space):
        w_method = space.appexec([], """():
            class C(list):
                def method(self): pass
            return C().method
        """)

        w_function = space.getattr(w_method, space.wrap("__func__"))
        w_self = space.getattr(w_method, space.wrap("__self__"))

        assert space.is_w(PyMethod_Function(space, w_method), w_function)
        assert space.is_w(PyMethod_Self(space, w_method), w_self)

        w_method2 = PyMethod_New(space, w_function, w_self)
        assert space.eq_w(w_method, w_method2)

    def test_getxxx(self, space):
        w_function = space.appexec([], """():
            def func(x, y, z): return x
            func.__module__ = "abc"
            return func
        """, cache=False)
        w_code = PyFunction_GetCode(space, w_function)
        assert w_code.co_name == "func"

        ref = make_ref(space, w_code)
        assert (from_ref(space, rffi.cast(PyObject, ref.c_ob_type)) is
                space.gettypeobject(PyCode.typedef))
        assert "func" == space.unwrap(
            from_ref(space, rffi.cast(PyCodeObject, ref).c_co_name))
        assert 3 == rffi.cast(PyCodeObject, ref).c_co_argcount
        decref(space, ref)

        w_module = PyFunction_GetModule(space,w_function)
        assert space.utf8_w(w_module) == "abc"

    def test_co_flags(self, space):
        def get_flags(signature, body="pass"):
            w_code = space.appexec([], """():
                def func(%s): %s
                return func.__code__
            """ % (signature, body), cache=False)
            ref = make_ref(space, w_code)
            co_flags = rffi.cast(PyCodeObject, ref).c_co_flags
            decref(space, ref)
            return co_flags
        assert get_flags("x") == CO_NESTED | CO_OPTIMIZED | CO_NEWLOCALS
        assert get_flags("x, *args") & CO_VARARGS
        assert get_flags("x, **kw") & CO_VARKEYWORDS
        assert get_flags("x", "yield x") & CO_GENERATOR

    def test_newcode(self, space):
        filename = rffi.str2charp('filename')
        funcname = rffi.str2charp('funcname')
        w_code = PyCode_NewEmpty(space, filename, funcname, 3)
        assert w_code.co_filename == 'filename'
        assert w_code.co_firstlineno == 3

        ref = make_ref(space, w_code)
        assert "filename" == space.unwrap(
            from_ref(space, rffi.cast(PyCodeObject, ref).c_co_filename))
        decref(space, ref)
        rffi.free_charp(filename)
        rffi.free_charp(funcname)

    def test_classmethod(self, space):
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
        w_classmethod = PyClassMethod_New(space, w_function)
        space.setattr(w_class, space.wrap("classmethod"), w_classmethod)
        assert space.is_w(
            space.call_method(w_instance, "classmethod"), w_class)

    def test_addr2line(self, space):
        w_function = space.appexec([], """():
            def func():
                x = a + b
                return x
            return func
        """, cache=False)
        w_code = PyFunction_GetCode(space, w_function)
        assert PyCode_Addr2Line(space, w_code, 0) == 3
        assert PyCode_Addr2Line(space, w_code, 8) == 4
        assert PyCode_Addr2Line(space, w_code, -1) == -1
        assert PyCode_Addr2Line(space, w_code, 100) == -1

class AppTestCall(AppTestCpythonExtensionBase):
    def test_code_new_empty(self):
        module = self.import_extension('foo', [
            ("code_newempty", "METH_VARARGS",
             """
                const char *filename;
                const char *funcname;
                int firstlineno;

                if (!PyArg_ParseTuple(args, "ssi:code_newempty",
                                      &filename, &funcname, &firstlineno))
                    return NULL;

                return (PyObject *)PyCode_NewEmpty(filename, funcname, firstlineno);
             """),
            ])

        def f():
            return args
        # check that calling a code object constructed by PyCode_NewEmpty
        # doesn't crash, and produce the right file, lineno, etc
        if not self.runappdirect:
            # The exception mocking for appdirect doesn't work well enough
            f.__code__ = module.code_newempty("abc", "def", 23)
            with raises(AssertionError) as info:
                f()

            lines = list(f.__code__.co_lines())
            assert lines == [(0, 4, 23)]
            assert info.tb.tb_next.tb_lineno == 23


    def test_get_xxx(self):
        module = self.import_extension('foo', [
            ("code_numfree", "METH_O",
             """
                PyCodeObject *code = (PyCodeObject*)PyFunction_GetCode(args);
                if (code == NULL) {
                    return NULL;
                }
                size_t n = PyCode_GetNumFree(code);
                return PyLong_FromSize_t(n);
             """),
            ("code_cellvars", "METH_O",
             """
                PyCodeObject *code = (PyCodeObject*)PyFunction_GetCode(args);
                if (code == NULL) {
                    return NULL;
                }
                return PyCode_GetCellvars(code);
             """),
            ("code_code", "METH_O",
             """
                PyCodeObject *code = (PyCodeObject*)PyFunction_GetCode(args);
                if (code == NULL) {
                    return NULL;
                }
                return PyCode_GetCode(code);
             """),
            ("code_freevars", "METH_O",
             """
                PyCodeObject *code = (PyCodeObject*)PyFunction_GetCode(args);
                if (code == NULL) {
                    return NULL;
                }
                return PyCode_GetFreevars(code);
             """),
            ("code_varnames", "METH_O",
             """
                PyCodeObject *code = (PyCodeObject*)PyFunction_GetCode(args);
                if (code == NULL) {
                    return NULL;
                }
                return PyCode_GetVarnames(code);
             """),
            ("func_globals", "METH_O",
             """
                return PyFunction_GetGlobals(args);
             """),
        ])

        g = 42
        def wrapper(x):
            a = 5
            global g
            g = 12
            def func(x):
                return a, x
        code = wrapper.__code__
        assert module.code_cellvars(wrapper) == ('a', )
        assert module.code_numfree(wrapper) == 0
        assert module.code_code(wrapper) == code.co_code
        assert module.code_freevars(wrapper) == code.co_freevars
        assert module.code_varnames(wrapper) == code.co_varnames
        assert module.func_globals(wrapper) == wrapper.__globals__
