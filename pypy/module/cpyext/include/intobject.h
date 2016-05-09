
/* Int object interface */

#ifndef Py_INTOBJECT_H
#define Py_INTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyInt_AS_LONG(obj) _PyInt_AS_LONG((PyObject*)obj)

typedef struct {
    PyObject_HEAD
    long ob_ival;
} PyIntObject;

#ifdef __cplusplus
}
#endif
#endif /* !Py_BOOLOBJECT_H */
