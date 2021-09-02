#include <Python.h>
#include "hpy.h"

#ifdef HPY_UNIVERSAL_ABI
   // for _h2py and _py2h
#  include "handles.h"
#endif


_HPy_HIDDEN void
ctx_Dump(HPyContext ctx, HPy h)
{
    // just use _PyObject_Dump for now, but we might want to add more info
    // about the handle itself in the future.
    _PyObject_Dump(_h2py(h));
}

/* NOTE: contrarily to CPython, the HPy have to check that h_type is a
   type. On CPython it's not necessarily because it passes a PyTypeObject*,
   but here we can only receive an HPy.

   However, we can't/don't want to raise an exception if you pass a non-type,
   because the CPython version (PyObject_TypeCheck) always succeed and it
   would be too easy to forget to check the return value. We just raise a
   fatal error instead.

   Hopefully the slowdown is not too much. If it proves to be too much, we
   could say that the function is allowed to crash if you pass a non-type, and
   do the check only in debug mode.
*/
_HPy_HIDDEN int
ctx_TypeCheck(HPyContext ctx, HPy h_obj, HPy h_type)
{
    PyObject *type= _h2py(h_type);
    assert(type != NULL);
    if (!PyType_Check(type)) {
        Py_FatalError("HPy_TypeCheck arg 2 must be a type");
    }
    return PyObject_TypeCheck(_h2py(h_obj), (PyTypeObject*)type);
}
