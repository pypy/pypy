/* Boolean object interface */

#ifndef Py_BOOLOBJECT_H
#define Py_BOOLOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyBool_Check(x) (Py_TYPE(x) == &PyBool_Type)

/* Py_False and Py_True are the only two bools in existence.
Don't forget to apply Py_INCREF() when returning either!!! */

/* Use these macros */
#define Py_False ((PyObject *) &_Py_FalseStruct)
#define Py_True ((PyObject *) &_Py_TrueStruct)

/* Macros for returning Py_True or Py_False, respectively */
#define Py_RETURN_TRUE return Py_INCREF(Py_True), Py_True
#define Py_RETURN_FALSE return Py_INCREF(Py_False), Py_False


/* abi3/limited-API shims (CPython defines these as macros over Py_Is, i.e. a
   plain pointer comparison, which is correct on PyPy too) */
#define Py_IsTrue(x) ((x) == Py_True)
#define Py_IsFalse(x) ((x) == Py_False)

#ifdef __cplusplus
}
#endif
#endif /* !Py_BOOLOBJECT_H */
