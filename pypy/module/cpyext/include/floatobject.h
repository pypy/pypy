
/* Float object interface */

#ifndef Py_FLOATOBJECT_H
#define Py_FLOATOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

PyObject* PyFloat_FromDouble(double);
double PyFloat_AsDouble(PyObject*);

#ifdef __cplusplus
}
#endif
#endif /* !Py_FLOATOBJECT_H */
