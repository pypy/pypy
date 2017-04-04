typedef unsigned int Py_UCS4;
/* On PyPy, Py_UNICODE is always wchar_t */
#define PY_UNICODE_TYPE wchar_t
typedef PY_UNICODE_TYPE Py_UNICODE;

#define Py_UNICODE_REPLACEMENT_CHARACTER ((Py_UNICODE) 0xFFFD)

typedef struct {
    PyObject_HEAD
    Py_UNICODE *str;
    Py_ssize_t length;
    long hash;                  /* Hash value; -1 if not set */
    PyObject *defenc;           /* (Default) Encoded version as Python
                                   string, or NULL; this is used for
                                   implementing the buffer protocol */
} PyUnicodeObject;
