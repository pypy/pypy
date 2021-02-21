
/* set object interface */

#ifndef Py_SETOBJECT_H
#define Py_SETOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    PyObject *_tmplist; /* a private place to put values during _PySet_Next */
} PySetObject;

#define PyFrozenSet_CheckExact(ob) (Py_TYPE(ob) == &PyFrozenSet_Type)
#define PyAnySet_CheckExact(ob) \
    (Py_TYPE(ob) == &PySet_Type || Py_TYPE(ob) == &PyFrozenSet_Type)
#define PyAnySet_Check(ob) \
    (Py_TYPE(ob) == &PySet_Type || Py_TYPE(ob) == &PyFrozenSet_Type || \
      PyType_IsSubtype(Py_TYPE(ob), &PySet_Type) || \
      PyType_IsSubtype(Py_TYPE(ob), &PyFrozenSet_Type))
#define PySet_Check(ob) \
    (Py_TYPE(ob) == &PySet_Type || \
    PyType_IsSubtype(Py_TYPE(ob), &PySet_Type))
#define   PyFrozenSet_Check(ob) \
    (Py_TYPE(ob) == &PyFrozenSet_Type || \
      PyType_IsSubtype(Py_TYPE(ob), &PyFrozenSet_Type))


#ifdef __cplusplus
}
#endif
#endif /* !Py_SETOBJECT_H */

