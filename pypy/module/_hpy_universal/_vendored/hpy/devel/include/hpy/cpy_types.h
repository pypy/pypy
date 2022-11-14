#ifndef HPY_UNIVERSAL_CPY_TYPES_H
#define HPY_UNIVERSAL_CPY_TYPES_H

/* generally speaking, we can't #include Python.h, but there are a bunch of
 * types defined there that we need to use.  Here, we redefine all the types
 * we need, with a cpy_ prefix.
 */

typedef struct _object cpy_PyObject;
typedef cpy_PyObject *(*cpy_PyCFunction)(cpy_PyObject *, cpy_PyObject *);
typedef struct PyMethodDef cpy_PyMethodDef;
typedef struct bufferinfo cpy_Py_buffer;
typedef int (*cpy_visitproc)(cpy_PyObject *, void *);
typedef cpy_PyObject *(*cpy_PyCFunction)(cpy_PyObject *, cpy_PyObject *);
typedef cpy_PyObject *(*cpy_getter)(cpy_PyObject *, void *);
typedef int (*cpy_setter)(cpy_PyObject *, cpy_PyObject *, void *);


#endif /* HPY_UNIVERSAL_CPY_TYPES_H */
