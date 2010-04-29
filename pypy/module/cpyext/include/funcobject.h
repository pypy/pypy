
/* Function object interface */

#ifndef Py_FUNCOBJECT_H
#define Py_FUNCOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    PyObject *func_name;	/* The __name__ attribute, a string object */
} PyFunctionObject;

#define PyMethod_GET_CLASS(obj) PyMethod_Class(obj)
#define PyMethod_GET_FUNCTION(obj) PyMethod_Function(obj)

#ifdef __cplusplus
}
#endif
#endif /* !Py_FUNCOBJECT_H */
