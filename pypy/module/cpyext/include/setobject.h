/* Int object interface */

#ifndef Py_SETOBJECT_H
#define Py_SETOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PySet_GET_SIZE(obj) _PySet_GET_SIZE((PyObject*)obj);

#ifdef __cplusplus
}
#endif
#endif /* !Py_SETOBJECT_H */
