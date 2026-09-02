#ifndef Py_PYLIFECYCLE_H
#define Py_PYLIFECYCLE_H
#ifdef __cplusplus
extern "C" {
#endif


PyAPI_FUNC(PyThreadState *) Py_NewInterpreter(void);
PyAPI_FUNC(void) Py_EndInterpreter(PyThreadState *tstate);

/* Restore signals that the interpreter has called SIG_IGN on to SIG_DFL. */
#ifndef Py_LIMITED_API
PyAPI_FUNC(void) _Py_RestoreSignals(void);
#endif

#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 >= 0x030B0000
PyAPI_DATA(const unsigned long) Py_Version;
#endif


/* In Python <= 3.6 there is a variable _Py_Finalizing of type
   'PyThreadState *'.  Emulate it with a macro. */
#define _Py_Finalizing  \
    (_Py_IsFinalizing() ? _PyThreadState_UncheckedGet() : NULL)



/* abi3/limited-API shims */
PyAPI_FUNC(void) Py_Initialize(void);
PyAPI_FUNC(void) Py_InitializeEx(int);
PyAPI_FUNC(void) Py_Finalize(void);
PyAPI_FUNC(int) Py_FinalizeEx(void);
PyAPI_FUNC(void) Py_Exit(int status);
PyAPI_FUNC(int) Py_Main(int argc, wchar_t **argv);
PyAPI_FUNC(int) Py_BytesMain(int argc, char **argv);
PyAPI_FUNC(wchar_t *) Py_GetPath(void);
PyAPI_FUNC(wchar_t *) Py_GetPrefix(void);
PyAPI_FUNC(wchar_t *) Py_GetExecPrefix(void);
PyAPI_FUNC(wchar_t *) Py_GetProgramFullPath(void);
PyAPI_FUNC(wchar_t *) Py_GetPythonHome(void);
PyAPI_FUNC(const char *) Py_GetPlatform(void);
PyAPI_FUNC(const char *) Py_GetCompiler(void);
PyAPI_FUNC(const char *) Py_GetCopyright(void);
PyAPI_FUNC(const char *) Py_GetBuildInfo(void);
PyAPI_FUNC(void) Py_SetPath(const wchar_t *);
PyAPI_FUNC(void) Py_SetProgramName(const wchar_t *);
PyAPI_FUNC(void) Py_SetPythonHome(const wchar_t *);

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYLIFECYCLE_H */
