
/* Int object interface */

#ifndef Py_INTOBJECT_H
#define Py_INTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    long ob_ival;
} PyIntObject;

#define PyInt_Check(op) \
		 PyType_FastSubclass((op)->ob_type, Py_TPFLAGS_INT_SUBCLASS)
#define PyInt_CheckExact(op) ((op)->ob_type == &PyInt_Type)

PyAPI_FUNC(PyObject *) PyInt_FromLong(long);
PyAPI_FUNC(void) _PyPy_int_dealloc(PyObject *);

#ifdef __cplusplus
}
#endif
#endif /* !Py_BOOLOBJECT_H */
