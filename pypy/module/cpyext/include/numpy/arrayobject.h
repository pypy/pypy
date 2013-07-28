
/* NDArray object interface - S. H. Muller, 2013/07/26 */

#ifndef Py_NDARRAYOBJECT_H
#define Py_NDARRAYOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

/* fake PyArrayObject so that code that doesn't do direct field access works */
#define PyArrayObject PyObject

#ifndef npy_intp
#define npy_intp long
#endif
#ifndef import_array
#define import_array()
#endif

#ifndef PyArray_NDIM

#define PyArray_NDIM     _PyArray_NDIM
#define PyArray_DIM      _PyArray_DIM
#define PyArray_SIZE     _PyArray_SIZE
#define PyArray_ITEMSIZE _PyArray_ITEMSIZE
#define PyArray_NBYTES   _PyArray_NBYTES
#define PyArray_TYPE     _PyArray_TYPE
#define PyArray_DATA     _PyArray_DATA
#define PyArray_FromAny  _PyArray_FromAny

#define PyArray_SimpleNew _PyArray_SimpleNew
#define PyArray_SimpleNewFromData _PyArray_SimpleNewFromData
#define PyArray_SimpleNewFromDataOwning _PyArray_SimpleNewFromDataOwning

#endif

/* copied from numpy/ndarraytypes.h 
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

#ifdef __cplusplus
}
#endif
#endif /* !Py_NDARRAYOBJECT_H */
