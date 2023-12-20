#include <Python.h>
#include "hpy.h"

#ifndef HPY_ABI_CPYTHON
   // for _h2py and _py2h
#  include "handles.h"
#endif

_HPy_HIDDEN int32_t
ctx_ContextVar_Get(HPyContext *ctx, HPy context_var, HPy default_value, HPy *result)
{
    PyObject * py_result;
    int32_t ret = PyContextVar_Get(_h2py(context_var), _h2py(default_value), &py_result);
    *result = _py2h(py_result);
    return ret;
}
