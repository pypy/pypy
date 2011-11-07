from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.methodobject import PyMethodDef
from pypy.module.cpyext.api import ApiFunction
from pypy.module.cpyext.pyobject import PyObject, make_ref, Py_DecRef
from pypy.module.cpyext.methodobject import (
    PyDescr_NewMethod, PyCFunction_typedef)
from pypy.rpython.lltypesystem import rffi, lltype

class AppTestMethodObject(AppTestCpythonExtensionBase):
    def test_call_METH(self):
        mod = self.import_extension('foo', [
            ('getarg_O', 'METH_O',
             '''
             Py_INCREF(args);
             return args;
             '''
             ),
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
            ('getarg_OLD', 'METH_OLDARGS',
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
            ('isSameFunction', 'METH_O',
             '''
             PyCFunction ptr = PyCFunction_GetFunction(args);
             if (!ptr) return NULL;
             if (ptr == foo_getarg_O)
                 Py_RETURN_TRUE;
             else
                 Py_RETURN_FALSE;
             '''
             ),
            ])
        assert mod.getarg_O(1) == 1
        raises(TypeError, mod.getarg_O)
        raises(TypeError, mod.getarg_O, 1, 1)

        assert mod.getarg_NO() is None
        raises(TypeError, mod.getarg_NO, 1)
        raises(TypeError, mod.getarg_NO, 1, 1)

        assert mod.getarg_OLD(1) == 1
        assert mod.getarg_OLD() is None
        assert mod.getarg_OLD(1, 2) == (1, 2)

        assert mod.isCFunction(mod.getarg_O) == "getarg_O"
        assert mod.isSameFunction(mod.getarg_O)
        raises(TypeError, mod.isSameFunction, 1)

class TestPyCMethodObject(BaseApiTest):
    def test_repr(self, space, api):
        """
        W_PyCMethodObject has a repr string which describes it as a method
        and gives its name and the name of its class.
        """
        def func(space, w_self, w_args):
            return space.w_None
        c_func = ApiFunction([PyObject, PyObject], PyObject, func)
        func.api_func = c_func
        ml = lltype.malloc(PyMethodDef, flavor='raw', zero=True)
        namebuf = rffi.str2charp('func')
        ml.c_ml_name = namebuf
        ml.c_ml_meth = rffi.cast(PyCFunction_typedef,
                                 c_func.get_llhelper(space))

        method = api.PyDescr_NewMethod(space.w_str, ml)
        assert repr(method).startswith(
            "<built-in method 'func' of 'str' object ")

        rffi.free_charp(namebuf)
        lltype.free(ml, flavor='raw')
