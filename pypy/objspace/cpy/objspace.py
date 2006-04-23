from pypy.objspace.cpy.capi import *
from pypy.annotation.pairtype import pair
from pypy.interpreter import baseobjspace


class CPyObjSpace:
    from pypy.objspace.cpy.capi import W_Object

    def __init__(self):
        self.fromcache = baseobjspace.InternalSpaceCache(self).getorbuild
        self.w_int   = W_Object(int)
        self.w_None  = W_Object(None)
        self.w_False = W_Object(False)
        self.w_True  = W_Object(True)
        self.wrap_cache = {}

    def enter_cache_building_mode(self):
        pass

    def leave_cache_building_mode(self, val):
        pass

    def getbuiltinmodule(self, name):
        return PyImport_ImportModule(name)

    def wrap(self, x):
        if isinstance(x, baseobjspace.Wrappable):
            x = x.__spacebind__(self)
            if isinstance(x, baseobjspace.Wrappable):
                try:
                    return self.wrap_cache[x]
                except KeyError:
                    import pypy.objspace.cpy.wrappable
                    result = pair(self, x).wrap()
                    self.wrap_cache[x] = result
                    return result
        if x is None:
            return self.w_None
        if isinstance(x, int):
            return PyInt_FromLong(x)
        if isinstance(x, str):
            return PyString_FromStringAndSize(x, len(x))
        raise TypeError("wrap(%r)" % (x,))
    wrap._annspecialcase_ = "specialize:wrap"

    def unwrap(self, w_obj):
        assert isinstance(w_obj, W_Object)
        return w_obj.value

    getattr = staticmethod(PyObject_GetAttr)
    getitem = staticmethod(PyObject_GetItem)
    setitem = staticmethod(PyObject_SetItem)
    int_w   = staticmethod(PyInt_AsLong)

    def call_function(self, w_callable, *args_w):
        args_w += (None,)
        return PyObject_CallFunctionObjArgs(w_callable, *args_w)

    def _freeze_(self):
        return True

    def new_interned_str(self, s):
        w_s = self.wrap(s)
        PyString_InternInPlace(byref(w_s))
        return w_s

    def newdict(self, items_w):
        w_dict = PyDict_New()
        for w_key, w_value in items_w:
            PyDict_SetItem(w_dict, w_key, w_value)
        return w_dict

    def newlist(self, items_w):
        w_list = PyList_New(0)
        for w_item in items_w:
            # XXX inefficient but:
            #       PyList_SetItem steals a ref so it's harder to use
            #       PySequence_SetItem crashes if it replaces a NULL item
            PyList_Append(w_list, w_item)
        return w_list

    def newtuple(self, items_w):
        # XXX not very efficient, but PyTuple_SetItem steals a ref
        w_list = self.newlist(items_w)
        return PySequence_Tuple(w_list)

    def lt(self, w1, w2): return PyObject_RichCompare(w1, w2, Py_LT)
    def le(self, w1, w2): return PyObject_RichCompare(w1, w2, Py_LE)
    def eq(self, w1, w2): return PyObject_RichCompare(w1, w2, Py_EQ)
    def ne(self, w1, w2): return PyObject_RichCompare(w1, w2, Py_NE)
    def gt(self, w1, w2): return PyObject_RichCompare(w1, w2, Py_GT)
    def ge(self, w1, w2): return PyObject_RichCompare(w1, w2, Py_GE)

    def lt_w(self, w1, w2): return PyObject_RichCompareBool(w1, w2, Py_LT) != 0
    def le_w(self, w1, w2): return PyObject_RichCompareBool(w1, w2, Py_LE) != 0
    def eq_w(self, w1, w2): return PyObject_RichCompareBool(w1, w2, Py_EQ) != 0
    def ne_w(self, w1, w2): return PyObject_RichCompareBool(w1, w2, Py_NE) != 0
    def gt_w(self, w1, w2): return PyObject_RichCompareBool(w1, w2, Py_GT) != 0
    def ge_w(self, w1, w2): return PyObject_RichCompareBool(w1, w2, Py_GE) != 0
