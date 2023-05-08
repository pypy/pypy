#include <Python.h>
#include "hpy.h"

#ifndef HPY_ABI_CPYTHON
   // for _h2py and _py2h
#  include "handles.h"
#endif

_HPy_HIDDEN HPy
ctx_Compile_s(HPyContext *ctx, const char *utf8_source, const char *utf8_filename, HPy_SourceKind kind)
{
    int start;
    switch (kind)
    {
    case HPy_SourceKind_Expr: start = Py_eval_input; break;
    case HPy_SourceKind_File: start = Py_file_input; break;
    case HPy_SourceKind_Single: start = Py_single_input; break;
    default:
        PyErr_SetString(PyExc_SystemError, "invalid source kind");
        return HPy_NULL;
    }
    return _py2h(Py_CompileString(utf8_source, utf8_filename, start));
}
