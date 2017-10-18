/* Definitions of missing symbols go here */

#include "Python.h"

PyTypeObject PyFunction_Type;

PyTypeObject PyMethod_Type;
PyTypeObject PyRange_Type;
PyTypeObject PyTraceBack_Type;

int Py_DebugFlag = 1;
int Py_VerboseFlag = 0;
int Py_InteractiveFlag = 0;
int Py_InspectFlag = 0;
int Py_OptimizeFlag = 0;
int Py_NoSiteFlag = 0;
int Py_BytesWarningFlag = 0;
int Py_UseClassExceptionsFlag = 0;
int Py_FrozenFlag = 0;
int Py_TabcheckFlag = 0;
int Py_UnicodeFlag = 0;
int Py_IgnoreEnvironmentFlag = 0;
int Py_DivisionWarningFlag = 0;
int Py_DontWriteBytecodeFlag = 0;
int Py_NoUserSiteDirectory = 0;
int _Py_QnewFlag = 0;
int Py_Py3kWarningFlag = 0;
int Py_HashRandomizationFlag = 0;

const char *Py_FileSystemDefaultEncoding;  /* filled when cpyext is imported */
void _Py_setfilesystemdefaultencoding(const char *enc) {
    Py_FileSystemDefaultEncoding = enc;
}
