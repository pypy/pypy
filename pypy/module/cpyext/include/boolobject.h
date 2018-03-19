
/* Bool object interface */

#ifndef Py_BOOLOBJECT_H
#define Py_BOOLOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyBoolObject PyIntObject

#define Py_False ((PyObject *) &_Py_ZeroStruct)
#define Py_True ((PyObject *) &_Py_TrueStruct)

/* Macros for returning Py_True or Py_False, respectively */
#define Py_RETURN_TRUE do { Py_INCREF(Py_True); return Py_True; } while(0)
#define Py_RETURN_FALSE do { Py_INCREF(Py_False); return Py_False; } while(0)

#ifdef __cplusplus
}
#endif
#endif /* !Py_BOOLOBJECT_H */
