
/* abi3/limited-API shim declarations: functions and macros that
   CPython exports but PyPy does not implement.  Symbols are provided
   by src/abi3_*.c. */
#ifndef Py_PYSTRCMP_H
#define Py_PYSTRCMP_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyOS_stricmp PyOS_mystricmp
#define PyOS_strnicmp PyOS_mystrnicmp
PyAPI_FUNC(int) PyOS_mystricmp(const char *, const char *);
PyAPI_FUNC(int) PyOS_mystrnicmp(const char *, const char *, Py_ssize_t);

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYSTRCMP_H */
