
/* abi3/limited-API shim declarations: functions and macros that
   CPython exports but PyPy does not implement.  Symbols are provided
   by src/abi3_*.c. */
#ifndef Py_PYFRAME_H
#define Py_PYFRAME_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(PyCodeObject *) PyFrame_GetCode(PyFrameObject *frame);

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYFRAME_H */
