
/* abi3/limited-API shim declarations: functions and macros that
   CPython exports but PyPy does not implement.  Symbols are provided
   by src/abi3_*.c. */
#ifndef Py_CODECS_H
#define Py_CODECS_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(int) PyCodec_Register(PyObject *search_function);
PyAPI_FUNC(int) PyCodec_Unregister(PyObject *search_function);
PyAPI_FUNC(int) PyCodec_RegisterError(const char *name, PyObject *error);
PyAPI_FUNC(PyObject *) PyCodec_LookupError(const char *name);
PyAPI_FUNC(int) PyCodec_KnownEncoding(const char *encoding);
PyAPI_FUNC(PyObject *) PyCodec_StrictErrors(PyObject *exc);
PyAPI_FUNC(PyObject *) PyCodec_IgnoreErrors(PyObject *exc);
PyAPI_FUNC(PyObject *) PyCodec_ReplaceErrors(PyObject *exc);
PyAPI_FUNC(PyObject *) PyCodec_XMLCharRefReplaceErrors(PyObject *exc);
PyAPI_FUNC(PyObject *) PyCodec_BackslashReplaceErrors(PyObject *exc);
PyAPI_FUNC(PyObject *) PyCodec_NameReplaceErrors(PyObject *exc);
PyAPI_FUNC(PyObject *) PyCodec_StreamReader(const char *encoding, PyObject *stream, const char *errors);
PyAPI_FUNC(PyObject *) PyCodec_StreamWriter(const char *encoding, PyObject *stream, const char *errors);

#ifdef __cplusplus
}
#endif
#endif /* !Py_CODECS_H */
