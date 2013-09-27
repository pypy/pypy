import py

from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi, lltype

from pypy.module.micronumpy.interp_numarray import W_NDimArray
from pypy.module.micronumpy.interp_dtype import get_dtype_cache

def scalar(space):
    dtype = get_dtype_cache(space).w_float64dtype
    return W_NDimArray.new_scalar(space, dtype, space.wrap(10.))

def array(space, shape, order='C'):
    dtype = get_dtype_cache(space).w_float64dtype
    return W_NDimArray.from_shape(space, shape, dtype, order=order)

def iarray(space, shape, order='C'):
    dtype = get_dtype_cache(space).w_int64dtype
    return W_NDimArray.from_shape(space, shape, dtype, order=order)


NULL = lltype.nullptr(rffi.VOIDP.TO)

class TestNDArrayObject(BaseApiTest):

    def test_Check(self, space, api):
        a = array(space, [10, 5, 3])
        x = space.wrap(10.)
        assert api._PyArray_Check(a)
        assert api._PyArray_CheckExact(a)
        assert not api._PyArray_Check(x)
        assert not api._PyArray_CheckExact(x)

    def test_FLAGS(self, space, api):
        s = array(space, [10])
        c = array(space, [10, 5, 3], order='C')
        f = array(space, [10, 5, 3], order='F')
        assert api._PyArray_FLAGS(s) & 0x0001
        assert api._PyArray_FLAGS(s) & 0x0002
        assert api._PyArray_FLAGS(c) & 0x0001
        assert api._PyArray_FLAGS(f) & 0x0002
        assert not api._PyArray_FLAGS(c) & 0x0002
        assert not api._PyArray_FLAGS(f) & 0x0001

    def test_NDIM(self, space, api):
        a = array(space, [10, 5, 3])
        assert api._PyArray_NDIM(a) == 3

    def test_DIM(self, space, api):
        a = array(space, [10, 5, 3])
        assert api._PyArray_DIM(a, 1) == 5

    def test_STRIDE(self, space, api):
        a = array(space, [10, 5, 3], )
        assert api._PyArray_STRIDE(a, 1) == a.implementation.get_strides()[1]

    def test_SIZE(self, space, api):
        a = array(space, [10, 5, 3])
        assert api._PyArray_SIZE(a) == 150

    def test_ITEMSIZE(self, space, api):
        a = array(space, [10, 5, 3])
        assert api._PyArray_ITEMSIZE(a) == 8

    def test_NBYTES(self, space, api):
        a = array(space, [10, 5, 3])
        assert api._PyArray_NBYTES(a) == 1200

    def test_TYPE(self, space, api):
        a = array(space, [10, 5, 3])
        assert api._PyArray_TYPE(a) == 12

    def test_DATA(self, space, api):
        a = array(space, [10, 5, 3])
        addr = api._PyArray_DATA(a)
        addr2 = rffi.cast(rffi.VOIDP, a.implementation.storage)
        assert addr == addr2

    def test_FromAny_scalar(self, space, api):
        a0 = scalar(space)
        assert a0.implementation.get_scalar_value().value == 10.

        a = api._PyArray_FromAny(a0, NULL, 0, 0, 0, NULL)
        assert api._PyArray_NDIM(a) == 0

        ptr = rffi.cast(rffi.DOUBLEP, api._PyArray_DATA(a))
        assert ptr[0] == 10.

    def test_FromAny(self, space, api):
        a = array(space, [10, 5, 3])
        assert api._PyArray_FromAny(a, NULL, 0, 0, 0, NULL) is a
        self.raises(space, api, NotImplementedError, api._PyArray_FromAny,
                    a, NULL, 0, 3, 0, NULL)

    def test_FromObject(self, space, api):
        a = array(space, [10, 5, 3])
        assert api._PyArray_FromObject(a, a.get_dtype().num, 0, 0) is a
        exc = self.raises(space, api, NotImplementedError, api._PyArray_FromObject,
                    a, 11, 0, 3)
        assert exc.errorstr(space).find('FromObject') >= 0

    def test_list_from_fixedptr(self, space, api):
        A = lltype.GcArray(lltype.Float)
        ptr = lltype.malloc(A, 3)
        assert isinstance(ptr, lltype._ptr)
        ptr[0] = 10.
        ptr[1] = 5.
        ptr[2] = 3.
        l = list(ptr)
        assert l == [10., 5., 3.]

    def test_list_from_openptr(self, space, api):
        nd = 3
        a = array(space, [nd])
        ptr = rffi.cast(rffi.DOUBLEP, api._PyArray_DATA(a))
        ptr[0] = 10.
        ptr[1] = 5.
        ptr[2] = 3.
        l = []
        for i in range(nd):
            l.append(ptr[i])
        assert l == [10., 5., 3.]

    def test_SimpleNew_scalar(self, space, api):
        ptr_s = lltype.nullptr(rffi.LONGP.TO)
        a = api._PyArray_SimpleNew(0, ptr_s, 12)

        dtype = get_dtype_cache(space).w_float64dtype

        a.set_scalar_value(dtype.itemtype.box(10.))
        assert a.get_scalar_value().value == 10.

    def test_SimpleNewFromData_scalar(self, space, api):
        a = array(space, [1])
        num = api._PyArray_TYPE(a)
        ptr_a = api._PyArray_DATA(a)

        x = rffi.cast(rffi.DOUBLEP, ptr_a)
        x[0] = float(10.)

        ptr_s = lltype.nullptr(rffi.LONGP.TO)

        res = api._PyArray_SimpleNewFromData(0, ptr_s, num, ptr_a)
        assert res.is_scalar()
        assert res.get_scalar_value().value == 10.

    def test_SimpleNew(self, space, api):
        shape = [10, 5, 3]
        nd = len(shape)

        s = iarray(space, [nd])
        ptr_s = rffi.cast(rffi.LONGP, api._PyArray_DATA(s))
        ptr_s[0] = 10
        ptr_s[1] = 5
        ptr_s[2] = 3

        a = api._PyArray_SimpleNew(nd, ptr_s, 12)

        #assert list(api._PyArray_DIMS(a))[:3] == shape

        ptr_a = api._PyArray_DATA(a)

        x = rffi.cast(rffi.DOUBLEP, ptr_a)
        for i in range(150):
            x[i] = float(i)

        for i in range(150):
            assert x[i] == float(i)

    def test_SimpleNewFromData(self, space, api):
        shape = [10, 5, 3]
        nd = len(shape)

        s = iarray(space, [nd])
        ptr_s = rffi.cast(rffi.LONGP, api._PyArray_DATA(s))
        ptr_s[0] = 10
        ptr_s[1] = 5
        ptr_s[2] = 3

        a = array(space, shape)
        num = api._PyArray_TYPE(a)
        ptr_a = api._PyArray_DATA(a)

        x = rffi.cast(rffi.DOUBLEP, ptr_a)
        for i in range(150):
            x[i] = float(i)

        res = api._PyArray_SimpleNewFromData(nd, ptr_s, num, ptr_a)
        assert api._PyArray_TYPE(res) == num
        assert api._PyArray_DATA(res) == ptr_a
        for i in range(nd):
            assert api._PyArray_DIM(res, i) == shape[i]
        ptr_r = rffi.cast(rffi.DOUBLEP, api._PyArray_DATA(res))
        for i in range(150):
            assert ptr_r[i] == float(i)
        res = api._PyArray_SimpleNewFromDataOwning(nd, ptr_s, num, ptr_a)
        x = rffi.cast(rffi.DOUBLEP, ptr_a)
        ptr_r = rffi.cast(rffi.DOUBLEP, api._PyArray_DATA(res))
        x[20] = -100.
        assert ptr_r[20] == -100.

    def test_SimpleNewFromData_complex(self, space, api):
        a = array(space, [2])
        ptr_a = api._PyArray_DATA(a)

        x = rffi.cast(rffi.DOUBLEP, ptr_a)
        x[0] = 3.
        x[1] = 4.

        ptr_s = lltype.nullptr(rffi.LONGP.TO)

        res = api._PyArray_SimpleNewFromData(0, ptr_s, 15, ptr_a)
        assert res.get_scalar_value().real == 3.
        assert res.get_scalar_value().imag == 4.

class AppTestCNumber(AppTestCpythonExtensionBase):
    def test_ndarray_object_c(self):
        mod = self.import_extension('foo', [
                ("test_simplenew", "METH_NOARGS",
                '''
                npy_intp dims[2] ={2, 3};
                PyObject * obj = PyArray_SimpleNew(2, dims, 11);
                return obj;
                '''
                ),
                ("test_fill", "METH_NOARGS",
                '''
                npy_intp dims[2] ={2, 3};
                PyObject * obj = PyArray_SimpleNew(2, dims, 1);
                PyArray_FILLWBYTE(obj, 42);
                return obj;
                '''
                ),
                ("test_copy", "METH_NOARGS",
                '''
                npy_intp dims1[2] ={2, 3};
                npy_intp dims2[2] ={3, 2};
                PyObject * obj1 = PyArray_ZEROS(2, dims1, 11, 0);
                PyObject * obj2 = PyArray_ZEROS(2, dims2, 11, 0);
                PyArray_FILLWBYTE(obj2, 42);
                PyArray_CopyInto(obj2, obj1);
                Py_DECREF(obj1);
                return obj2;
                '''
                ),
                ("test_FromAny", "METH_NOARGS",
                '''
                npy_intp dims[2] ={2, 3};
                PyObject * obj1 = PyArray_SimpleNew(2, dims, 1);
                PyArray_FILLWBYTE(obj1, 42);
                PyObject * obj2 = _PyArray_FromAny(obj1, NULL, 0, 0, 0, NULL);
                Py_DECREF(obj1);
                return obj2;
                '''
                ),
                 ("test_FromObject", "METH_NOARGS",
                '''
                npy_intp dims[2] ={2, 3};
                PyObject * obj1 = PyArray_SimpleNew(2, dims, 1);
                PyArray_FILLWBYTE(obj1, 42);
                PyObject * obj2 = _PyArray_FromObject(obj1, 12, 0, 0);
                Py_DECREF(obj1);
                return obj2;
                '''
                ),
                ], prologue='#include <numpy/arrayobject.h>')
        arr = mod.test_simplenew()
        assert arr.shape == (2, 3)
        assert arr.dtype.num == 11 #float32 dtype
        arr = mod.test_fill()
        assert arr.shape == (2, 3)
        assert arr.dtype.num == 1 #int8 dtype
        assert (arr == 42).all()
        arr = mod.test_copy()
        assert (arr == 0).all()
        #Make sure these work without errors
        arr = mod.test_FromAny()
        arr = mod.test_FromObject()
