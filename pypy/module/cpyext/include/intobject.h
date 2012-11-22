
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

#ifdef __cplusplus
}
#endif
#endif /* !Py_INTOBJECT_H */
