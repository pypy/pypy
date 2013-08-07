/* Interfaces to parse and execute pieces of python code */

#ifndef Py_PYTHONRUN_H
#define Py_PYTHONRUN_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(void) Py_FatalError(const char *message);

/* the -3 option will probably not be implemented */
#define Py_Py3kWarningFlag 0

#define Py_FrozenFlag 0
#define Py_VerboseFlag 0
#define Py_DebugFlag 1

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

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYTHONRUN_H */
