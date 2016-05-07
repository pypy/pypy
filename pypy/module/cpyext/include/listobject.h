#define PyList_GET_ITEM(o, i)     PyList_GetItem((PyObject*)(o), (i))
#define PyList_SET_ITEM(o, i, v)  _PyList_SET_ITEM((PyObject*)(o), (i), (v))
#define PyList_GET_SIZE(o)        _PyList_GET_SIZE((PyObject*)(o))
