
/* abi3/limited-API shim declarations: functions and macros that
   CPython exports but PyPy does not implement.  Symbols are provided
   by src/abi3_*.c. */
#ifndef Py_PYBUFFER_H
#define Py_PYBUFFER_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(int) PyObject_CopyData(PyObject *dest, PyObject *src);
PyAPI_FUNC(Py_ssize_t) PyBuffer_SizeFromFormat(const char *format);
PyAPI_FUNC(void) PyBuffer_FillContiguousStrides(int ndims, Py_ssize_t *shape, Py_ssize_t *strides, int itemsize, char fort);

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYBUFFER_H */
