
/* abi3/limited-API shim declarations: functions and macros that
   CPython exports but PyPy does not implement.  Symbols are provided
   by src/abi3_*.c. */
#ifndef Py_ITEROBJECT_H
#define Py_ITEROBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyCallIter_Check(op) Py_IS_TYPE((op), &PyCallIter_Type)
#define PySeqIter_Check(op) Py_IS_TYPE((op), &PySeqIter_Type)

#ifdef __cplusplus
}
#endif
#endif /* !Py_ITEROBJECT_H */
