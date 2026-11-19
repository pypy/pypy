#ifndef Py_LIMITED_API
PyAPI_DATA(const char *) _PyPy_FileSystemDefaultEncoding;
#define Py_FileSystemDefaultEncoding _PyPy_FileSystemDefaultEncoding
#endif /* !Py_LIMITED_API */
PyAPI_FUNC(void) _Py_setfilesystemdefaultencoding(const char *);
