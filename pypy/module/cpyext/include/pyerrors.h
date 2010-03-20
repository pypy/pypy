
/* Exception interface */

#ifndef Py_PYERRORS_H
#define Py_PYERRORS_H
#ifdef __cplusplus
extern "C" {
#endif

extern PyObject *PyPyExc_Exception;
#define PyExc_Exception PyPyExc_Exception

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYERRORS_H */
