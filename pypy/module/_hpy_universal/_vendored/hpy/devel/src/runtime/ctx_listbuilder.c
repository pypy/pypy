#include <stddef.h>
#include <Python.h>
#include "hpy.h"

#ifdef HPY_UNIVERSAL_ABI
   // for _h2py and _py2h
#  include "handles.h"
#endif


_HPy_HIDDEN HPyListBuilder
ctx_ListBuilder_New(HPyContext ctx, HPy_ssize_t initial_size)
{
    PyObject *lst = PyList_New(initial_size);
    if (lst == NULL)
        PyErr_Clear();   /* delay the MemoryError */
    return (HPyListBuilder){_py2h(lst)};
}

_HPy_HIDDEN void
ctx_ListBuilder_Set(HPyContext ctx, HPyListBuilder builder,
                    HPy_ssize_t index, HPy h_item)
{
    PyObject *lst = _h2py(builder._lst);
    if (lst != NULL) {
        PyObject *item = _h2py(h_item);
        assert(index >= 0 && index < PyList_GET_SIZE(lst));
        Py_INCREF(item);
        PyList_SET_ITEM(lst, index, item);
    }
}

_HPy_HIDDEN HPy
ctx_ListBuilder_Build(HPyContext ctx, HPyListBuilder builder)
{
    HPy h_lst = builder._lst;
    builder._lst = HPy_NULL;
    if (HPy_IsNull(h_lst))
        PyErr_NoMemory();
    return h_lst;
}

_HPy_HIDDEN void
ctx_ListBuilder_Cancel(HPyContext ctx, HPyListBuilder builder)
{
    HPy h_lst = builder._lst;
    builder._lst = HPy_NULL;
    HPy_Close(ctx, h_lst);
}
