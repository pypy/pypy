
/* abi3/limited-API shim declarations: functions and macros that
   CPython exports but PyPy does not implement.  Symbols are provided
   by src/abi3_*.c. */
#ifndef Py_FILEUTILS_H
#define Py_FILEUTILS_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(wchar_t *) Py_DecodeLocale(const char *arg, size_t *size);
PyAPI_FUNC(char*) Py_EncodeLocale(const wchar_t *text, size_t *error_pos);

#ifdef __cplusplus
}
#endif
#endif /* !Py_FILEUTILS_H */
