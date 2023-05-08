#ifndef HPY_UNIVERSAL_CPY_TYPES_H
#define HPY_UNIVERSAL_CPY_TYPES_H

/* ~~~~~~~~~~~~~~~~ CPython legacy types ~~~~~~~~~~~~~~~~ */

/* These are the types which are needed to implement legacy features such as
   .legacy_slots, .legacy_methods, HPy_FromPyObject, HPy_AsPyObject, etc.

   In cpython and hybrid ABI mode we can #include Python.h and use the "real"
   types.

   In universal ABI mode, legacy features cannot be used, but we still need
   the corresponding C types to use in the HPy declarations. Note that we use
   only forward declarations, meaning that it will actually be impossible to
   instantiate any of these struct.
*/

#ifdef HPY_ABI_UNIVERSAL

typedef struct FORBIDDEN_cpy_PyObject cpy_PyObject;
typedef struct FORBIDDEN_PyMethodDef cpy_PyMethodDef;
typedef struct FORBIDDEN_PyModuleDef cpy_PyModuleDef;
typedef struct FORBIDDEN_bufferinfo cpy_Py_buffer;

// declare the following API functions as _HPY_LEGACY, which triggers an
// #error if they are used
HPyAPI_FUNC _HPY_LEGACY cpy_PyObject *HPy_AsPyObject(HPyContext *ctx, HPy h);
HPyAPI_FUNC _HPY_LEGACY HPy HPy_FromPyObject(HPyContext *ctx, cpy_PyObject *obj);

#else

// Python.h has already been included by the main hpy.h
typedef PyObject cpy_PyObject;
typedef PyMethodDef cpy_PyMethodDef;
typedef PyModuleDef cpy_PyModuleDef;
typedef Py_buffer cpy_Py_buffer;

#endif /* HPY_ABI_UNIVERSAL */


typedef cpy_PyObject *(*cpy_PyCFunction)(cpy_PyObject *, cpy_PyObject *const *, HPy_ssize_t);
typedef int (*cpy_visitproc)(cpy_PyObject *, void *);
typedef cpy_PyObject *(*cpy_getter)(cpy_PyObject *, void *);
typedef int (*cpy_setter)(cpy_PyObject *, cpy_PyObject *, void *);
typedef void (*cpy_PyCapsule_Destructor)(cpy_PyObject *);
typedef cpy_PyObject *(*cpy_vectorcallfunc)(cpy_PyObject *callable, cpy_PyObject *const *args,
                                    size_t nargsf, cpy_PyObject *kwnames);

#endif /* HPY_UNIVERSAL_CPY_TYPES_H */
