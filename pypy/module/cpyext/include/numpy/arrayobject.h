
/* NDArray object interface - S. H. Muller, 2013/07/26 */

#ifndef Py_NDARRAYOBJECT_H
#define Py_NDARRAYOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#include "old_defines.h"

#define NPY_INLINE

/* fake PyArrayObject so that code that doesn't do direct field access works */
#define PyArrayObject PyObject
#define PyArray_Descr PyObject

PyTypeObject PyArray_Type;

typedef unsigned char npy_bool;
typedef unsigned char npy_uint8;
typedef int npy_int;

#ifndef npy_intp
#define npy_intp long
#endif
#ifndef NPY_INTP_FMT
#define NPY_INTP_FMT "ld"
#endif
#ifndef import_array
#define import_array()
#endif

#define NPY_MAXDIMS 32

typedef struct {
    npy_intp *ptr;
    int len;
} PyArray_Dims;

/* data types copied from numpy/ndarraytypes.h 
 * keep numbers in sync with micronumpy.interp_dtype.DTypeCache
 */
enum NPY_TYPES {    NPY_BOOL=0,
                    NPY_BYTE, NPY_UBYTE,
                    NPY_SHORT, NPY_USHORT,
                    NPY_INT, NPY_UINT,
                    NPY_LONG, NPY_ULONG,
                    NPY_LONGLONG, NPY_ULONGLONG,
                    NPY_FLOAT, NPY_DOUBLE, NPY_LONGDOUBLE,
                    NPY_CFLOAT, NPY_CDOUBLE, NPY_CLONGDOUBLE,
                    NPY_OBJECT=17,
                    NPY_STRING, NPY_UNICODE,
                    NPY_VOID,
                    /*
                     * New 1.6 types appended, may be integrated
                     * into the above in 2.0.
                     */
                    NPY_DATETIME, NPY_TIMEDELTA, NPY_HALF,

                    NPY_NTYPES,
                    NPY_NOTYPE,
                    NPY_CHAR,      /* special flag */
                    NPY_USERDEF=256,  /* leave room for characters */

                    /* The number of types not including the new 1.6 types */
                    NPY_NTYPES_ABI_COMPATIBLE=21
};

#define NPY_INT8      NPY_BYTE
#define NPY_UINT8     NPY_UBYTE
#define NPY_INT16     NPY_SHORT
#define NPY_UINT16    NPY_USHORT
#define NPY_INT32     NPY_INT
#define NPY_UINT32    NPY_UINT
#define NPY_INT64     NPY_LONG
#define NPY_UINT64    NPY_ULONG
#define NPY_FLOAT32   NPY_FLOAT
#define NPY_FLOAT64   NPY_DOUBLE
#define NPY_COMPLEX32 NPY_CFLOAT
#define NPY_COMPLEX64 NPY_CDOUBLE

#define PyTypeNum_ISBOOL(type)      ((type) == NPY_BOOL)
#define PyTypeNum_ISINTEGER(type)  (((type) >= NPY_BYTE) && \
                                    ((type) <= NPY_ULONGLONG))
#define PyTypeNum_ISFLOAT(type)   ((((type) >= NPY_FLOAT) && \
                                    ((type) <= NPY_LONGDOUBLE)) || \
                                    ((type) == NPY_HALF))
#define PyTypeNum_ISCOMPLEX(type)  (((type) >= NPY_CFLOAT) && \
                                    ((type) <= NPY_CLONGDOUBLE))

#define PyArray_ISBOOL(arr)    (PyTypeNum_ISBOOL(PyArray_TYPE(arr)))
#define PyArray_ISINTEGER(arr) (PyTypeNum_ISINTEGER(PyArray_TYPE(arr)))
#define PyArray_ISFLOAT(arr)   (PyTypeNum_ISFLOAT(PyArray_TYPE(arr)))
#define PyArray_ISCOMPLEX(arr) (PyTypeNum_ISCOMPLEX(PyArray_TYPE(arr)))


/* selection of flags */
#define NPY_CONTIGUOUS      0x0001
#define NPY_FORTRAN         0x0002
#define NPY_OWNDATA         0x0004
#define NPY_FORCECAST       0x0010
#define NPY_ALIGNED         0x0100
#define NPY_NOTSWAPPED      0x0200
#define NPY_WRITEABLE       0x0400
#define NPY_C_CONTIGUOUS    NPY_CONTIGUOUS
#define NPY_F_CONTIGUOUS    NPY_FORTRAN
#define NPY_IN_ARRAY       (NPY_C_CONTIGUOUS | NPY_ALIGNED)
#define NPY_BEHAVED        (NPY_ALIGNED | NPY_WRITEABLE)
#define NPY_CARRAY         (NPY_CONTIGUOUS | NPY_BEHAVED)
#define NPY_FARRAY         (NPY_FORTRAN | NPY_BEHAVED)
#define NPY_DEFAULT         NPY_CARRAY

/* functions */
#ifndef PyArray_NDIM

#define PyArray_Check      _PyArray_Check
#define PyArray_CheckExact _PyArray_CheckExact

#define PyArray_ISONESEGMENT(arr) (1)
#define PyArray_FLAGS(arr)        (0)

#define PyArray_ISCONTIGUOUS _PyArray_ISCONTIGUOUS

#define PyArray_ISCARRAY(arr)   PyArray_ISCONTIGUOUS(arr)
#define PyArray_ISFARRAY(arr) (!PyArray_ISCONTIGUOUS(arr))

#define PyArray_NDIM       _PyArray_NDIM
#define PyArray_DIM        _PyArray_DIM
#define PyArray_STRIDE     _PyArray_STRIDE
#define PyArray_SIZE       _PyArray_SIZE
#define PyArray_ITEMSIZE   _PyArray_ITEMSIZE
#define PyArray_NBYTES     _PyArray_NBYTES
#define PyArray_TYPE       _PyArray_TYPE
#define PyArray_DATA       _PyArray_DATA

#define PyArray_Size PyArray_SIZE
#define PyArray_BYTES(arr) ((char *)PyArray_DATA(arr))

#define PyArray_FromAny _PyArray_FromAny
#define PyArray_FromObject _PyArray_FromObject
#define PyArray_ContiguousFromObject PyArray_FromObject
#define PyArray_ContiguousFromAny PyArray_FromObject

#define PyArray_FROMANY(obj, typenum, min, max, requirements) (obj)
#define PyArray_FROM_OTF(obj, typenum, requirements) \
        PyArray_FromObject(obj, typenum, 0, 0)

#define PyArray_New _PyArray_New
#define PyArray_SimpleNew _PyArray_SimpleNew
#define PyArray_SimpleNewFromData _PyArray_SimpleNewFromData
#define PyArray_SimpleNewFromDataOwning _PyArray_SimpleNewFromDataOwning

#define PyArray_EMPTY(nd, dims, type_num, fortran) \
        PyArray_SimpleNew(nd, dims, type_num)

void _PyArray_FILLWBYTE(PyObject* obj, int val);
PyObject* _PyArray_ZEROS(int nd, npy_intp* dims, int type_num, int fortran);
int _PyArray_CopyInto(PyArrayObject* dest, PyArrayObject* src);

#define PyArray_FILLWBYTE _PyArray_FILLWBYTE
#define PyArray_ZEROS _PyArray_ZEROS
#define PyArray_CopyInto _PyArray_CopyInto

#define PyArray_Resize(self, newshape, refcheck, fortran) (NULL)

/* Don't use these in loops! */

#define PyArray_GETPTR1(obj, i) ((void *)(PyArray_BYTES(obj) + \
                                         (i)*PyArray_STRIDE(obj,0)))

#define PyArray_GETPTR2(obj, i, j) ((void *)(PyArray_BYTES(obj) + \
                                            (i)*PyArray_STRIDE(obj,0) + \
                                            (j)*PyArray_STRIDE(obj,1)))

#define PyArray_GETPTR3(obj, i, j, k) ((void *)(PyArray_BYTES(obj) + \
                                            (i)*PyArray_STRIDE(obj,0) + \
                                            (j)*PyArray_STRIDE(obj,1) + \
                                            (k)*PyArray_STRIDE(obj,2)))

#define PyArray_GETPTR4(obj, i, j, k, l) ((void *)(PyArray_BYTES(obj) + \
                                            (i)*PyArray_STRIDE(obj,0) + \
                                            (j)*PyArray_STRIDE(obj,1) + \
                                            (k)*PyArray_STRIDE(obj,2) + \
                                            (l)*PyArray_STRIDE(obj,3)))

#endif

#ifdef __cplusplus
}
#endif
#endif /* !Py_NDARRAYOBJECT_H */
