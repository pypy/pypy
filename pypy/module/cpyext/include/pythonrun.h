/* Interfaces to parse and execute pieces of python code */

#ifndef Py_PYTHONRUN_H
#define Py_PYTHONRUN_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(void) Py_FatalError(const char *msg);

/* taken from Python-2.7.3/Include/pydebug.h */
PyAPI_DATA(int) Py_DebugFlag;
PyAPI_DATA(int) Py_VerboseFlag;
PyAPI_DATA(int) Py_InteractiveFlag;
PyAPI_DATA(int) Py_InspectFlag;
PyAPI_DATA(int) Py_OptimizeFlag;
PyAPI_DATA(int) Py_NoSiteFlag;
PyAPI_DATA(int) Py_BytesWarningFlag;
PyAPI_DATA(int) Py_UseClassExceptionsFlag; /* Unused, removed in 3.7 */
PyAPI_DATA(int) Py_FrozenFlag; /* set when the python is "frozen" */
PyAPI_DATA(int) Py_TabcheckFlag;
PyAPI_DATA(int) Py_UnicodeFlag;
PyAPI_DATA(int) Py_IgnoreEnvironmentFlag;
PyAPI_DATA(int) Py_DivisionWarningFlag;
PyAPI_DATA(int) Py_DontWriteBytecodeFlag;
PyAPI_DATA(int) Py_NoUserSiteDirectory;
/* _XXX Py_QnewFlag should go away in 3.0.  It's true iff -Qnew is passed,
 *   on the command line, and is used in 2.2 by ceval.c to make all "/" divisions
 *     true divisions (which they will be in 3.0). */
PyAPI_DATA(int) _Py_QnewFlag;
/* Warn about 3.x issues */
PyAPI_DATA(int) Py_Py3kWarningFlag;
PyAPI_DATA(int) Py_HashRandomizationFlag;


typedef struct {
    int cf_flags;  /* bitmask of CO_xxx flags relevant to future */
} PyCompilerFlags;

#define PyCF_MASK (CO_FUTURE_DIVISION | CO_FUTURE_ABSOLUTE_IMPORT | \
                   CO_FUTURE_WITH_STATEMENT | CO_FUTURE_PRINT_FUNCTION | \
                   CO_FUTURE_UNICODE_LITERALS)
#define PyCF_MASK_OBSOLETE (CO_NESTED)
#define PyCF_SOURCE_IS_UTF8  0x0100
#define PyCF_DONT_IMPLY_DEDENT 0x0200
#define PyCF_ONLY_AST 0x0400

#define Py_CompileString(str, filename, start) Py_CompileStringFlags(str, filename, start, NULL)

/* Stuff with no proper home (yet) */
PyAPI_DATA(int) (*PyOS_InputHook)(void);
typedef int (*_pypy_pyos_inputhook)(void);
PyAPI_FUNC(_pypy_pyos_inputhook) _PyPy_get_PyOS_InputHook(void);

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYTHONRUN_H */
