#include "Python.h"

_Py_COMP_DIAG_IGNORE_DEPR_DECLS

#include "unicodetype_db.h"

/* Fast detection of the most frequent whitespace characters */
const unsigned char _Py_ascii_whitespace[] = {
    0, 0, 0, 0, 0, 0, 0, 0,
/*     case 0x0009: * CHARACTER TABULATION */
/*     case 0x000A: * LINE FEED */
/*     case 0x000B: * LINE TABULATION */
/*     case 0x000C: * FORM FEED */
/*     case 0x000D: * CARRIAGE RETURN */
    0, 1, 1, 1, 1, 1, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
/*     case 0x001C: * FILE SEPARATOR */
/*     case 0x001D: * GROUP SEPARATOR */
/*     case 0x001E: * RECORD SEPARATOR */
/*     case 0x001F: * UNIT SEPARATOR */
    0, 0, 0, 0, 1, 1, 1, 1,
/*     case 0x0020: * SPACE */
    1, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,

    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0
};


#define appendstring(string) {for (copy = string;*copy;) *s++ = *copy++;}

/* size of fixed-size buffer for formatting single arguments */
#define ITEM_BUFFER_LEN 21
/* maximum number of characters required for output of %ld.  21 characters
   allows for 64-bit integers (in decimal) and an optional sign. */
#define MAX_LONG_CHARS 21
/* maximum number of characters required for output of %lld.
   We need at most ceil(log10(256)*SIZEOF_LONG_LONG) digits,
   plus 1 for the sign.  53/22 is an upper bound for log10(256). */
#define MAX_LONG_LONG_CHARS (2 + (SIZEOF_LONG_LONG*53-1) / 22)

/* CPython 3.12 removed PyUnicode_AS_UNICODE()/PyUnicode_FromUnicode() (PEP
   623). Copy code points out of an already-canonical (kind/data) unicode
   object one at a time via the still-current PyUnicode_READ_CHAR(), instead
   of the old flat Py_UNICODE_COPY() over a wchar_t buffer. */
wchar_t*
PyUnicode_AsWideCharString(PyObject *unicode,
                           Py_ssize_t *size)
{
    wchar_t* buffer;
    Py_ssize_t buflen;

    if (unicode == NULL) {
        PyErr_BadInternalCall();
        return NULL;
    }

    buflen = PyUnicode_GET_LENGTH(unicode) + 1;
    if (PY_SSIZE_T_MAX / sizeof(wchar_t) < buflen) {
        PyErr_NoMemory();
        return NULL;
    }

    /* PyPy shortcut: Unicode is already an array of wchar_t */
    buffer = PyMem_MALLOC(buflen * sizeof(wchar_t));
    if (buffer == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    if (PyUnicode_AsWideChar(unicode, buffer, buflen) < 0)
	return NULL;
    if (size != NULL)
        *size = buflen - 1;
    return buffer;
}

Py_ssize_t
PyUnicode_GetLength(PyObject *unicode)
{
    if (!PyUnicode_Check(unicode)) {
        PyErr_BadArgument();
        return -1;
    }
    if (PyUnicode_READY(unicode) == -1)
        return -1;
    return PyUnicode_GET_LENGTH(unicode);
}

void
PyUnicode_AppendAndDel(PyObject **pleft, PyObject *right)
{
    PyUnicode_Append(pleft, right);
    Py_XDECREF(right);
}

