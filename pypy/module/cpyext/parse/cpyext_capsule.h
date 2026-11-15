typedef void (*PyCapsule_Destructor)(PyObject *);

/* Internal structure of PyCapsule; CPython does not declare it at all */
#ifndef Py_LIMITED_API
typedef struct {
    PyObject_HEAD
    void *pointer;
    const char *name;
    void *context;
    PyCapsule_Destructor destructor;
} PyCapsule;
#endif /* !Py_LIMITED_API */



