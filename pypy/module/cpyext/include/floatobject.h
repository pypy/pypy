
/* Float object interface */

#ifndef Py_FLOATOBJECT_H
#define Py_FLOATOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    double ob_fval;
} PyFloatObject;

#ifdef __cplusplus
}
#endif
#endif /* !Py_FLOATOBJECT_H */
