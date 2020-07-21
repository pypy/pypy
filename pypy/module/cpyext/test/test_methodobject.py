from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.methodobject import PyMethodDef
from pypy.module.cpyext.api import ApiFunction
from pypy.module.cpyext.pyobject import PyObject, make_ref
from pypy.module.cpyext.methodobject import (
    PyDescr_NewMethod, PyCFunction)
from rpython.rtyper.lltypesystem import rffi, lltype

class AppTestMethodObject(AppTestCpythonExtensionBase):

    def test_call_METH_NOARGS(self):
        mod = self.import_extension('MyModule', [
            ('getarg_NO', 'METH_NOARGS',
             '''
             if(args) {
                 Py_INCREF(args);
                 return args;
             }
             else {
                 Py_INCREF(Py_None);
                 return Py_None;
             }
             '''
             ),
            ])
        assert mod.getarg_NO() is None
        raises(TypeError, mod.getarg_NO, 1)
        raises(TypeError, mod.getarg_NO, 1, 1)

    def test_call_METH_O(self):
        mod = self.import_extension('MyModule', [
            ('getarg_O', 'METH_O',
             '''
             Py_INCREF(args);
             return args;
             '''
             ),
            ])
        assert mod.getarg_O(1) == 1
        assert mod.getarg_O.__name__ == "getarg_O"
        raises(TypeError, mod.getarg_O)
        raises(TypeError, mod.getarg_O, 1, 1)

    def test_call_METH_VARARGS(self):
        mod = self.import_extension('MyModule', [
            ('getarg_VARARGS', 'METH_VARARGS',
             '''
             return Py_BuildValue("Ol", args, args->ob_refcnt);
             '''
             ),
            ])
        # check that we pass the expected tuple of arguments AND that the
        # recnt is 1. In particular, on PyPy refcnt==1 means that we created
        # the PyObject tuple directly, without passing from a w_tuple; as
        # such, the tuple will be immediately freed after the call, without
        # having to wait until the GC runs.
        #
        tup, refcnt = mod.getarg_VARARGS()
        assert tup == ()
        # the empty tuple is shared on CPython, so the refcnt will be >1. On
        # PyPy it is not shared, though.
        if not self.runappdirect:
            assert refcnt == 1
        #
        tup, refcnt = mod.getarg_VARARGS(1)
        assert tup == (1,)
        assert refcnt == 1
        #
        tup, refcnt = mod.getarg_VARARGS(1, 2, 3)
        assert tup == (1, 2, 3)
        assert refcnt == 1
        #
        raises(TypeError, mod.getarg_VARARGS, k=1)

    def test_call_METH_OLDARGS(self):
        mod = self.import_extension('MyModule', [
            ('getarg_OLD', 'METH_OLDARGS',
             '''
             if(args) {
                 return Py_BuildValue("Ol", args, args->ob_refcnt);
             }
             else {
                 Py_INCREF(Py_None);
                 return Py_None;
             }
             '''
             ),
            ])
        assert mod.getarg_OLD() is None
        val, refcnt = mod.getarg_OLD(1)
        assert val == 1
        val, refcnt = mod.getarg_OLD(1, 2)
        assert val == (1, 2)
        assert refcnt == 1 # see the comments in the test above

    def test_call_METH_KEYWORDS(self):
        mod = self.import_extension('MyModule', [
            ('getarg_KW', 'METH_VARARGS | METH_KEYWORDS',
             '''
             if (!kwargs) kwargs = Py_None;
             return Py_BuildValue("OO", args, kwargs);
             '''
             ),
            ])
        assert mod.getarg_KW(1) == ((1,), None)
        assert mod.getarg_KW(1, 2) == ((1, 2), None)
        assert mod.getarg_KW(a=3, b=4) == ((), {'a': 3, 'b': 4})
        assert mod.getarg_KW(1, 2, a=3, b=4) == ((1, 2), {'a': 3, 'b': 4})
        assert mod.getarg_KW.__name__ == "getarg_KW"
        assert mod.getarg_KW(*(), **{}) == ((), {})

    def test_func_attributes(self):
        mod = self.import_extension('MyModule', [
            ('isCFunction', 'METH_O',
             '''
             if(PyCFunction_Check(args)) {
                 PyCFunctionObject* func = (PyCFunctionObject*)args;
                 return PyString_FromString(func->m_ml->ml_name);
             }
             else {
                 Py_RETURN_FALSE;
             }
             '''
             ),
            ('getModule', 'METH_O',
             '''
             if(PyCFunction_Check(args)) {
                 PyCFunctionObject* func = (PyCFunctionObject*)args;
                 Py_INCREF(func->m_module);
                 return func->m_module;
             }
             else {
                 Py_RETURN_FALSE;
             }
             '''
             ),
            ('isSameFunction', 'METH_O',
             '''
             PyCFunction ptr = PyCFunction_GetFunction(args);
             if (!ptr) return NULL;
             if (ptr == (PyCFunction)MyModule_getModule)
                 Py_RETURN_TRUE;
             else
                 Py_RETURN_FALSE;
             '''
             ),
            ])
        assert mod.isCFunction(mod.getModule) == "getModule"
        assert mod.getModule(mod.getModule) == 'MyModule'
        if self.runappdirect:  # XXX: fails untranslated
            assert mod.isSameFunction(mod.getModule)
        raises(SystemError, mod.isSameFunction, 1)

    def test_function_as_method(self):
        # Unlike user functions, builtins don't become methods
        mod = self.import_extension('foo', [
            ('f', 'METH_NOARGS',
            '''
                return PyLong_FromLong(42);
            '''),
            ])
        class A(object): pass
        A.f = mod.f
        A.g = lambda: 42
        # Unbound method
        assert A.f() == 42
        raises(TypeError, A.g)
        # Bound method
        assert A().f() == 42
        raises(TypeError, A().g)

    def test_check(self):
        mod = self.import_extension('foo', [
            ('check', 'METH_O',
            '''
                return PyLong_FromLong(PyCFunction_Check(args));
            '''),
            ])
        from math import degrees
        assert mod.check(degrees) == 1
        assert mod.check(list) == 0
        assert mod.check(sorted) == 1
        def func():
            pass
        class A(object):
            def meth(self):
                pass
            @staticmethod
            def stat():
                pass
        assert mod.check(func) == 0
        assert mod.check(A) == 0
        assert mod.check(A.meth) == 0
        assert mod.check(A.stat) == 0

    def test_module_attribute(self):
        mod = self.import_extension('MyModule', [
            ('getarg_NO', 'METH_NOARGS',
             '''
                 Py_INCREF(Py_None);
                 return Py_None;
             '''
             ),
            ])
        assert mod.getarg_NO() is None
        assert mod.getarg_NO.__module__ == 'MyModule'
        mod.getarg_NO.__module__ = 'foobar'
        assert mod.getarg_NO.__module__ == 'foobar'

    def test_callfunc(self):
        mod = self.import_extension('foo', [
            ('callfunc', 'METH_VARARGS',
             '''
                PyObject *func, *argseq=NULL, *kwargs=NULL;
                if (!PyArg_ParseTuple(args, "O|OO", &func, &argseq, &kwargs)) {
                    return NULL;
                }
                if (!PyCFunction_Check(func)) {
                    Py_RETURN_FALSE;
                }
                if (argseq == NULL) {
                    return PyCFunction_Call(func, NULL, NULL);
                }
                if (kwargs == NULL) {
                    return PyCFunction_Call(func, argseq, NULL);
                }
                return PyCFunction_Call(func, argseq, kwargs);
             '''
             ),
             # Define some C functions so we can test this
             ('func_NOARGS', 'METH_NOARGS',
              '''
                    Py_RETURN_TRUE;
              '''),
            ('func_KW', 'METH_VARARGS | METH_KEYWORDS',
             '''
             if (!kwargs) kwargs = Py_None;
             return Py_BuildValue("OO", args, kwargs);
             '''
             ),
            ])
        ret = mod.callfunc(mod.func_NOARGS, ())
        assert ret is True
        ret = mod.callfunc(mod.func_KW, (1, 2, 3), {'a':'a', 'b':'b', 'c':'c'})
        assert ret == ((1, 2, 3), {'a':'a', 'b':'b', 'c':'c'})
        with raises(TypeError):
            mod.callfunc(mod.func_NOARGS, (), {'a': 'a'})
        with raises(TypeError):
            mod.callfunc(mod.func_NOARGS, (1, 2, 3))
