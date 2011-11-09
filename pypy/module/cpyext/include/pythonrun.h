/* Interfaces to parse and execute pieces of python code */

#ifndef Py_PYTHONRUN_H
#define Py_PYTHONRUN_H
#ifdef __cplusplus
extern "C" {
#endif

  void Py_FatalError(const char *msg);

/* the -3 option will probably not be implemented */
#define Py_Py3kWarningFlag 0

#define Py_FrozenFlag 0
#define Py_VerboseFlag 0

typedef struct {
    int cf_flags;  /* bitmask of CO_xxx flags relevant to future */
} PyCompilerFlags;

#define Py_CompileString(str, filename, start) Py_CompileStringFlags(str, filename, start, NULL)

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYTHONRUN_H */
