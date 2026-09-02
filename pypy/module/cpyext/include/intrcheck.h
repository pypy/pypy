
/* abi3/limited-API shim declarations: functions and macros that
   CPython exports but PyPy does not implement.  Symbols are provided
   by src/abi3_*.c. */
#ifndef Py_INTRCHECK_H
#define Py_INTRCHECK_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(void) PyOS_BeforeFork(void);
PyAPI_FUNC(void) PyOS_AfterFork_Parent(void);
PyAPI_FUNC(void) PyOS_AfterFork_Child(void);

#ifdef __cplusplus
}
#endif
#endif /* !Py_INTRCHECK_H */
