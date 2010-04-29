from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

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
