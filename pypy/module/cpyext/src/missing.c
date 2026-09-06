/* Definitions of missing symbols go here */

#include "Python.h"

int Py_DebugFlag = 1;
int Py_VerboseFlag = 0;
int Py_QuietFlag = 0;
int Py_InteractiveFlag = 0;
int Py_InspectFlag = 0;
/* intentionally set to -1 for test, should be reset at startup */
int Py_OptimizeFlag = -1;
int Py_NoSiteFlag = 0;
int Py_BytesWarningFlag = 0;
int Py_FrozenFlag = 0;
int Py_IgnoreEnvironmentFlag = 0;
int Py_DontWriteBytecodeFlag = 0;
int Py_NoUserSiteDirectory = 0;
int Py_UnbufferedStdioFlag = 0;
int Py_HashRandomizationFlag = 0;
int Py_IsolatedFlag = 0;

#ifdef MS_WINDOWS
int Py_LegacyWindowsStdioFlag = 0;
#endif

const unsigned long Py_Version = PY_VERSION_HEX;

const char *_PyPy_FileSystemDefaultEncoding;  /* filled when cpyext is imported */
void _Py_setfilesystemdefaultencoding(const char *enc) {
    _PyPy_FileSystemDefaultEncoding = enc;
}

int (*PyOS_InputHook)(void) = 0;  /* only ever filled in by C extensions */
#ifdef CPYEXT_TESTS
#ifdef __GNUC__
__attribute__((visibility("default")))
#else
__declspec(dllexport)
#endif
#endif  /* CPYEXT_TESTS */
PyAPI_FUNC(_pypy_pyos_inputhook) _Py_get_PyOS_InputHook(void) {
    return PyOS_InputHook;
}

/* PEP 697, as in CPython's Objects/typeobject.c. PyType_FromMetaclass lays
   the type data out at _align_up(base->tp_basicsize), see
   _PyType_FromMetaclass_impl in typeobject.py */
static Py_ssize_t
_align_up(Py_ssize_t size)
{
    return (size + ALIGNOF_MAX_ALIGN_T - 1) & ~(ALIGNOF_MAX_ALIGN_T - 1);
}

void *
PyObject_GetTypeData(PyObject *obj, PyTypeObject *cls)
{
    assert(PyObject_TypeCheck(obj, cls));
    return (char *)obj + _align_up(cls->tp_base->tp_basicsize);
}

Py_ssize_t
PyType_GetTypeDataSize(PyTypeObject *cls)
{
    ptrdiff_t result = cls->tp_basicsize - _align_up(cls->tp_base->tp_basicsize);
    if (result < 0) {
        return 0;
    }
    return result;
}
