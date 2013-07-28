"""
Numpy C-API for PyPy - S. H. Muller, 2013/07/26
"""

from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, Py_ssize_t, CANNOT_FAIL
from pypy.module.cpyext.pyobject import PyObject
from pypy.module.micronumpy.interp_numarray import W_NDimArray, convert_to_array
from pypy.module.micronumpy.interp_dtype import get_dtype_cache
from pypy.module.micronumpy.arrayimpl.scalar import Scalar
from rpython.rlib.rawstorage import RAW_STORAGE_PTR

# the asserts are needed, otherwise the translation fails

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def _PyArray_NDIM(space, w_array):
    assert isinstance(w_array, W_NDimArray)
    return len(w_array.get_shape())

@cpython_api([PyObject, Py_ssize_t], Py_ssize_t, error=CANNOT_FAIL)
def _PyArray_DIM(space, w_array, n):
    assert isinstance(w_array, W_NDimArray)
    return w_array.get_shape()[n]

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def _PyArray_SIZE(space, w_array):
    assert isinstance(w_array, W_NDimArray)
    return w_array.get_size()

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def _PyArray_ITEMSIZE(space, w_array):
    assert isinstance(w_array, W_NDimArray)
    return w_array.get_dtype().get_size()

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def _PyArray_NBYTES(space, w_array):
    assert isinstance(w_array, W_NDimArray)
    return w_array.get_size() * w_array.get_dtype().get_size()

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def _PyArray_TYPE(space, w_array):
    assert isinstance(w_array, W_NDimArray)
    return w_array.get_dtype().num


@cpython_api([PyObject], rffi.VOIDP, error=CANNOT_FAIL)
def _PyArray_DATA(space, w_array):
    # fails on scalars - see PyArray_FromAny()
    assert isinstance(w_array, W_NDimArray)
    return rffi.cast(rffi.VOIDP, w_array.implementation.storage)


@cpython_api([PyObject, rffi.VOIDP, Py_ssize_t, Py_ssize_t, Py_ssize_t, rffi.VOIDP], 
             PyObject)
def _PyArray_FromAny(space, w_obj, dtype, min_depth, max_depth, requirements, context):
    # ignore all additional arguments for now
    w_array = convert_to_array(space, w_obj)
    if w_array.is_scalar():
        # since PyArray_DATA() fails on scalars, create a 1D array and set empty 
        # shape. So the following combination works for *reading* scalars:
        #     PyObject *arr = PyArray_FromAny(obj);
        #     int nd = PyArray_NDIM(arr);
        #     void *data = PyArray_DATA(arr);
        impl = w_array.implementation
        w_array = W_NDimArray.from_shape(space, [1], impl.dtype)
        w_array.implementation.setitem(0, impl.value)
        w_array.implementation.shape = []
    return w_array


@cpython_api([Py_ssize_t, rffi.LONGP, Py_ssize_t], PyObject)
def _PyArray_SimpleNew(space, nd, dims, typenum):
    dtype = get_dtype_cache(space).dtypes_by_num[typenum]
    shape = []
    for i in range(nd):
        # back-and-forth wrapping needed to translate
        shape.append(space.int_w(space.wrap(dims[i])))

    return W_NDimArray.from_shape(space, shape, dtype)


def simple_new_from_data(space, nd, dims, typenum, data, owning):
    dtype = get_dtype_cache(space).dtypes_by_num[typenum]
    storage = rffi.cast(RAW_STORAGE_PTR, data)
    if nd == 0:
        w_val = dtype.itemtype.box_raw_data(storage)
        return W_NDimArray(Scalar(dtype, w_val))
    else:
        shape = []
        for i in range(nd):
            # back-and-forth wrapping needed to translate
            shape.append(space.int_w(space.wrap(dims[i])))
        
        return W_NDimArray.from_shape_and_storage(space, shape, storage, dtype, owning=owning)

@cpython_api([Py_ssize_t, rffi.LONGP, Py_ssize_t, rffi.VOIDP], PyObject)
def _PyArray_SimpleNewFromData(space, nd, dims, typenum, data):
    return simple_new_from_data(space, nd, dims, typenum, data, owning=False)

@cpython_api([Py_ssize_t, rffi.LONGP, Py_ssize_t, rffi.VOIDP], PyObject)
def _PyArray_SimpleNewFromDataOwning(space, nd, dims, typenum, data):
    # Variant to take over ownership of the memory, equivalent to:
    #     PyObject *arr = PyArray_SimpleNewFromData(nd, dims, typenum, data);
    #     ((PyArrayObject*)arr)->flags |= NPY_OWNDATA;
    return simple_new_from_data(space, nd, dims, typenum, data, owning=True)

