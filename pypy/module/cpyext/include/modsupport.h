
/* Module support interface */

#ifndef Py_MODSUPPORT_H
#define Py_MODSUPPORT_H
#ifdef __cplusplus
extern "C" {
#endif

PyObject *Py_InitModule(const char* name, PyMethodDef* methods);

#ifdef __cplusplus
}
#endif
#endif /* !Py_MODSUPPORT_H */
