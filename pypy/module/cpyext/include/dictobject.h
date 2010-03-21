
/* dict object interface */

#ifndef Py_DICTOBJECT_H
#define Py_DICTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

PyObject * PyDict_New(void);
int PyDict_SetItemString(PyObject *dp, const char *key, PyObject *item);

#ifdef __cplusplus
}
#endif
#endif /* !Py_DICTOBJECT_H */
