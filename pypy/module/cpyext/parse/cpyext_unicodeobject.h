typedef unsigned int Py_UCS4;
/* On PyPy, Py_UNICODE is always wchar_t */
#define PY_UNICODE_TYPE wchar_t
typedef PY_UNICODE_TYPE Py_UNICODE;

#define Py_UNICODE_REPLACEMENT_CHARACTER ((Py_UNICODE) 0xFFFD)

typedef struct {
    PyObject_HEAD
    Py_UNICODE *buffer;
    Py_ssize_t length;
    char *utf8buffer;
} PyUnicodeObject;
