#include <Python.h>
#include "hpy.h"

#ifndef HPY_ABI_CPYTHON
   // for _h2py and _py2h
#  include "handles.h"
#endif

_HPy_HIDDEN HPy
ctx_Capsule_New(HPyContext *ctx, void *pointer, const char *name,
        HPyCapsule_Destructor *destructor)
{
    PyObject *res;
    if (destructor) {
        // If a destructor is given, it is not allowed to omit the functions
        if ((destructor->cpy_trampoline == NULL || destructor->impl == NULL)) {
            PyErr_SetString(PyExc_ValueError, "Invalid HPyCapsule destructor");
            return HPy_NULL;
        }
        res = PyCapsule_New(pointer, name, destructor->cpy_trampoline);
    } else {
        res = PyCapsule_New(pointer, name, NULL);
    }
    return _py2h(res);
}

_HPy_HIDDEN int
ctx_Capsule_SetDestructor(HPyContext *ctx, HPy h_capsule,
        HPyCapsule_Destructor *destructor)
{
    if (destructor) {
        // If a destructor is given, it is not allowed to omit the functions
        if ((destructor->cpy_trampoline == NULL || destructor->impl == NULL)) {
            PyErr_SetString(PyExc_ValueError, "Invalid HPyCapsule destructor");
            return -1;
        }
        return PyCapsule_SetDestructor(_h2py(h_capsule), destructor->cpy_trampoline);
    }
    return PyCapsule_SetDestructor(_h2py(h_capsule), NULL);
}

#ifndef HPY_ABI_CPYTHON
_HPy_HIDDEN void *
ctx_Capsule_Get(HPyContext *ctx, HPy capsule, _HPyCapsule_key key, const char *name)
{
    switch (key)
    {
    case HPyCapsule_key_Pointer:
        return PyCapsule_GetPointer(_h2py(capsule), name);
    case HPyCapsule_key_Name:
        return (void *) PyCapsule_GetName(_h2py(capsule));
    case HPyCapsule_key_Context:
        return PyCapsule_GetContext(_h2py(capsule));
    case HPyCapsule_key_Destructor:
        PyErr_SetString(PyExc_ValueError, "Invalid operation: get HPyCapsule_key_Destructor");
        return NULL;
    }
    /* unreachable */
    assert(0);
    return NULL;
}

_HPy_HIDDEN int
ctx_Capsule_Set(HPyContext *ctx, HPy capsule, _HPyCapsule_key key, void *value)
{
    switch (key)
    {
    case HPyCapsule_key_Pointer:
        return PyCapsule_SetPointer(_h2py(capsule), value);
    case HPyCapsule_key_Name:
        return PyCapsule_SetName(_h2py(capsule), (const char *) value);
    case HPyCapsule_key_Context:
        return PyCapsule_SetContext(_h2py(capsule), value);
    case HPyCapsule_key_Destructor:
        return ctx_Capsule_SetDestructor(ctx, capsule, (HPyCapsule_Destructor *) value);
    }
    /* unreachable */
    assert(0);
    return -1;
}
#endif
