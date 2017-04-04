#ifndef Py_COBJECT_H
#define Py_COBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_DATA(PyTypeObject) PyCObject_Type;

#define PyCObject_Check(op) ((op)->ob_type == &PyCObject_Type)

/* Create a PyCObject from a pointer to a C object and an optional
   destructor function.  If the second argument is non-null, then it
   will be called with the first argument if and when the PyCObject is
   destroyed.

*/
PyAPI_FUNC(PyObject *) PyCObject_FromVoidPtr(
	void *cobj, void (*destruct)(void*));


/* Create a PyCObject from a pointer to a C object, a description object,
   and an optional destructor function.  If the third argument is non-null,
   then it will be called with the first and second arguments if and when 
   the PyCObject is destroyed.
*/
PyAPI_FUNC(PyObject *) PyCObject_FromVoidPtrAndDesc(
	void *cobj, void *desc, void (*destruct)(void*,void*));

/* Retrieve a pointer to a C object from a PyCObject. */
PyAPI_FUNC(void *) PyCObject_AsVoidPtr(PyObject *);

/* Retrieve a pointer to a description object from a PyCObject. */
PyAPI_FUNC(void *) PyCObject_GetDesc(PyObject *);

/* Import a pointer to a C object from a module using a PyCObject. */
PyAPI_FUNC(void *) PyCObject_Import(const char *module_name, const char *cobject_name);

/* Modify a C object. Fails (==0) if object has a destructor. */
PyAPI_FUNC(int) PyCObject_SetVoidPtr(PyObject *self, void *cobj);


#if (PY_VERSION_HEX >= 0x02060000 || defined(Py_BUILD_CORE))
typedef struct {
    PyObject_HEAD
    void *cobject;
    void *desc;
    void (*destructor)(void *);
} PyCObject;
#endif

PyAPI_FUNC(PyTypeObject *) _Py_get_cobject_type(void);

#ifdef __cplusplus
}
#endif
#endif /* !Py_COBJECT_H */
