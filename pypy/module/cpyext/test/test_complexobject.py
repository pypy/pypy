from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest

class TestComplexObject(BaseApiTest):
    def test_complexobject(self, space, api):
        w_value = api.PyComplex_FromDoubles(1.2, 3.4)
        assert space.unwrap(w_value) == 1.2+3.4j
        assert api.PyComplex_RealAsDouble(w_value) == 1.2
        assert api.PyComplex_ImagAsDouble(w_value) == 3.4

        assert api.PyComplex_RealAsDouble(space.wrap(42)) == 42
        assert api.PyComplex_RealAsDouble(space.wrap(1.5)) == 1.5
        assert api.PyComplex_ImagAsDouble(space.wrap(1.5)) == 0.0

        # cpython accepts anything for PyComplex_ImagAsDouble
        assert api.PyComplex_ImagAsDouble(space.w_None) == 0.0
        assert not api.PyErr_Occurred()
        assert api.PyComplex_RealAsDouble(space.w_None) == -1.0
        assert api.PyErr_Occurred()
        api.PyErr_Clear()

class AppTestCComplex(AppTestCpythonExtensionBase):
    def test_AsCComplex(self):
        module = self.import_extension('foo', [
            ("as_tuple", "METH_O",
             """
                 Py_complex c = PyComplex_AsCComplex(args);
                 if (PyErr_Occurred()) return NULL;
                 return Py_BuildValue("dd", c.real, c.imag);
             """)])
        assert module.as_tuple(12-34j) == (12, -34)
        assert module.as_tuple(-3.14) == (-3.14, 0.0)
        raises(TypeError, module.as_tuple, "12")

    def test_FromCComplex(self):
        module = self.import_extension('foo', [
            ("test", "METH_NOARGS",
             """
                 Py_complex c = {1.2, 3.4};
                 return PyComplex_FromCComplex(c);
             """)])
        assert module.test() == 1.2 + 3.4j

    def test_PyComplex_to_WComplex(self):
        module = self.import_extension('foo', [
            ("test", "METH_NOARGS",
             """
                 Py_complex c = {1.2, 3.4};
                 PyObject *obj = PyObject_Malloc(sizeof(PyComplexObject));
                 obj = PyObject_Init(obj, &PyComplex_Type);
                 assert(obj != NULL);
                 ((PyComplexObject *)obj)->cval = c;
                 return obj;
             """)])
        assert module.test() == 1.2 + 3.4j

    def test_WComplex_to_PyComplex(self):
        module = self.import_extension('foo', [
            ("test", "METH_O",
             """
                 Py_complex c = ((PyComplexObject *)args)->cval;
                 return Py_BuildValue("dd", c.real, c.imag);
             """)])
        assert module.test(1.2 + 3.4j) == (1.2, 3.4)
