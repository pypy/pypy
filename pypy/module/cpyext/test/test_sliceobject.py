from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.api import Py_ssize_t, Py_ssize_tP

class TestSliceObject(BaseApiTest):

    def test_GetIndicesEx(self, space, api):
        w = space.wrap
        def get_indices(w_start, w_stop, w_step, length):
            w_slice = space.newslice(w_start, w_stop, w_step)
            values = lltype.malloc(Py_ssize_tP.TO, 4, flavor='raw')

            res = api.PySlice_GetIndicesEx(w_slice, 100, values,
                rffi.ptradd(values, 1),
                rffi.ptradd(values, 2),
                rffi.ptradd(values, 3))
            assert res == 0
            rv = values[0], values[1], values[2], values[3]
            lltype.free(values, flavor='raw')
            return rv
        assert get_indices(w(10), w(20), w(1), 200) == (10, 20, 1, 10)

    def test_GetIndices(self, space, api):
        w = space.wrap
        def get_indices(w_start, w_stop, w_step, length):
            w_slice = space.newslice(w_start, w_stop, w_step)
            values = lltype.malloc(Py_ssize_tP.TO, 3, flavor='raw')

            res = api.PySlice_GetIndices(w_slice, 100, values,
                rffi.ptradd(values, 1),
                rffi.ptradd(values, 2))
            if res != 0:
                return None
            rv = values[0], values[1], values[2]
            lltype.free(values, flavor='raw')
            return rv
        assert get_indices(w(10), w(20), w(1), 200) == (10, 20, 1)
        assert get_indices(w(10.1), w(20), w(1), 200) is None

class AppTestSliceMembers(AppTestCpythonExtensionBase):
    def test_members(self):
        module = self.import_extension('foo', [
            ("clone", "METH_O",
             """
                 PySliceObject *slice = (PySliceObject *)args;
                 if (Py_TYPE(slice) != &PySlice_Type) {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 return PySlice_New(slice->start,
                                    slice->stop,
                                    slice->step);
             """),
            ])
        s = slice(10, 20, 30)
        assert module.clone(s) == s

    def test_nulls(self):
        module = self.import_extension('foo', [
            ("nullslice", "METH_NOARGS",
             """
                 return PySlice_New(NULL, NULL, NULL);
             """),
            ])
        assert module.nullslice() == slice(None, None, None)

    def test_ellipsis(self):
        module = self.import_extension('foo', [
            ("get_ellipsis", "METH_NOARGS",
             """
                 PyObject *ret = Py_Ellipsis;
                 Py_INCREF(ret);
                 return ret;
             """),
            ])
        assert module.get_ellipsis() is Ellipsis

    def test_typecheck(self):
        module = self.import_extension('foo', [
            ("check", "METH_O",
             """
                 PySliceObject *slice = (PySliceObject *)args;
                 return PyLong_FromLong(PySlice_Check(slice));
             """),
            ])
        s = slice(10, 20, 30)
        assert module.check(s)
