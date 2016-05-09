import py
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.api import Py_ssize_tP, PyObjectP
from pypy.module.cpyext.pyobject import make_ref, from_ref
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class TestDictObject(BaseApiTest):
    def test_dict(self, space, api):
        d = api.PyDict_New()
        assert space.eq_w(d, space.newdict())

        assert space.eq_w(api.PyDict_GetItem(space.wrap({"a": 72}),
                                             space.wrap("a")),
                          space.wrap(72))

        assert api.PyDict_SetItem(d, space.wrap("c"), space.wrap(42)) >= 0
        assert space.eq_w(space.getitem(d, space.wrap("c")),
                          space.wrap(42))

        space.setitem(d, space.wrap("name"), space.wrap(3))
        assert space.eq_w(api.PyDict_GetItem(d, space.wrap("name")),
                          space.wrap(3))

        space.delitem(d, space.wrap("name"))
        assert not api.PyDict_GetItem(d, space.wrap("name"))
        assert not api.PyErr_Occurred()

        buf = rffi.str2charp("name")
        assert not api.PyDict_GetItemString(d, buf)
        rffi.free_charp(buf)
        assert not api.PyErr_Occurred()

        assert api.PyDict_Contains(d, space.wrap("c"))
        assert not api.PyDict_Contains(d, space.wrap("z"))

        assert api.PyDict_DelItem(d, space.wrap("c")) == 0
        assert api.PyDict_DelItem(d, space.wrap("name")) < 0
        assert api.PyErr_Occurred() is space.w_KeyError
        api.PyErr_Clear()
        assert api.PyDict_Size(d) == 0

        space.setitem(d, space.wrap("some_key"), space.wrap(3))
        buf = rffi.str2charp("some_key")
        assert api.PyDict_DelItemString(d, buf) == 0
        assert api.PyDict_Size(d) == 0
        assert api.PyDict_DelItemString(d, buf) < 0
        assert api.PyErr_Occurred() is space.w_KeyError
        api.PyErr_Clear()
        rffi.free_charp(buf)

        d = space.wrap({'a': 'b'})
        api.PyDict_Clear(d)
        assert api.PyDict_Size(d) == 0

    def test_check(self, space, api):
        d = api.PyDict_New()
        assert api.PyDict_Check(d)
        assert api.PyDict_CheckExact(d)
        sub = space.appexec([], """():
            class D(dict):
                pass
            return D""")
        d = space.call_function(sub)
        assert api.PyDict_Check(d)
        assert not api.PyDict_CheckExact(d)
        i = space.wrap(2)
        assert not api.PyDict_Check(i)
        assert not api.PyDict_CheckExact(i)

    def test_keys(self, space, api):
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a"), space.wrap("b"))

        assert space.eq_w(api.PyDict_Keys(w_d), space.wrap(["a"]))
        assert space.eq_w(api.PyDict_Values(w_d), space.wrap(["b"]))
        assert space.eq_w(api.PyDict_Items(w_d), space.wrap([("a", "b")]))

    def test_merge(self, space, api):
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a"), space.wrap("b"))

        w_d2 = space.newdict()
        space.setitem(w_d2, space.wrap("a"), space.wrap("c"))
        space.setitem(w_d2, space.wrap("c"), space.wrap("d"))
        space.setitem(w_d2, space.wrap("e"), space.wrap("f"))

        api.PyDict_Merge(w_d, w_d2, 0)
        assert space.unwrap(w_d) == dict(a='b', c='d', e='f')
        api.PyDict_Merge(w_d, w_d2, 1)
        assert space.unwrap(w_d) == dict(a='c', c='d', e='f')

    def test_update(self, space, api):
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a"), space.wrap("b"))

        w_d2 = api.PyDict_Copy(w_d)
        assert not space.is_w(w_d2, w_d)
        space.setitem(w_d, space.wrap("c"), space.wrap("d"))
        space.setitem(w_d2, space.wrap("e"), space.wrap("f"))

        api.PyDict_Update(w_d, w_d2)
        assert space.unwrap(w_d) == dict(a='b', c='d', e='f')

    def test_iter(self, space, api):
        w_dict = space.sys.getdict(space)
        py_dict = make_ref(space, w_dict)

        ppos = lltype.malloc(Py_ssize_tP.TO, 1, flavor='raw')
        ppos[0] = 0
        pkey = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        pvalue = lltype.malloc(PyObjectP.TO, 1, flavor='raw')

        try:
            w_copy = space.newdict()
            while api.PyDict_Next(w_dict, ppos, pkey, pvalue):
                w_key = from_ref(space, pkey[0])
                w_value = from_ref(space, pvalue[0])
                space.setitem(w_copy, w_key, w_value)
        finally:
            lltype.free(ppos, flavor='raw')
            lltype.free(pkey, flavor='raw')
            lltype.free(pvalue, flavor='raw')

        api.Py_DecRef(py_dict) # release borrowed references

        assert space.eq_w(space.len(w_copy), space.len(w_dict))
        assert space.eq_w(w_copy, w_dict)

    def test_iterkeys(self, space, api):
        w_dict = space.sys.getdict(space)
        py_dict = make_ref(space, w_dict)

        ppos = lltype.malloc(Py_ssize_tP.TO, 1, flavor='raw')
        pkey = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        pvalue = lltype.malloc(PyObjectP.TO, 1, flavor='raw')

        keys_w = []
        values_w = []
        try:
            ppos[0] = 0
            while api.PyDict_Next(w_dict, ppos, pkey, None):
                w_key = from_ref(space, pkey[0])
                keys_w.append(w_key)
            ppos[0] = 0
            while api.PyDict_Next(w_dict, ppos, None, pvalue):
                w_value = from_ref(space, pvalue[0])
                values_w.append(w_value)
        finally:
            lltype.free(ppos, flavor='raw')
            lltype.free(pkey, flavor='raw')
            lltype.free(pvalue, flavor='raw')

        api.Py_DecRef(py_dict) # release borrowed references

        assert space.eq_w(space.newlist(keys_w),
                          space.call_method(w_dict, "keys"))
        assert space.eq_w(space.newlist(values_w),
                          space.call_method(w_dict, "values"))

    def test_dictproxy(self, space, api):
        w_dict = space.sys.get('modules')
        w_proxy = api.PyDictProxy_New(w_dict)
        assert space.contains_w(w_proxy, space.wrap('sys'))
        raises(OperationError, space.setitem,
               w_proxy, space.wrap('sys'), space.w_None)
        raises(OperationError, space.delitem,
               w_proxy, space.wrap('sys'))
        raises(OperationError, space.call_method, w_proxy, 'clear')
        assert api.PyDictProxy_Check(w_proxy)

class AppTestDictObject(AppTestCpythonExtensionBase):
    def test_dictproxytype(self):
        module = self.import_extension('foo', [
            ("dict_proxy", "METH_VARARGS",
             """
                 PyObject * dict;
                 PyObject * proxydict;
                 int i;
                 if (!PyArg_ParseTuple(args, "O", &dict))
                     return NULL;
                 proxydict = PyDictProxy_New(dict);
#ifdef PYPY_VERSION  // PyDictProxy_Check[Exact] are PyPy-specific.
                 if (!PyDictProxy_Check(proxydict)) {
                    Py_DECREF(proxydict);
                    PyErr_SetNone(PyExc_ValueError);
                    return NULL;
                 }
                 if (!PyDictProxy_CheckExact(proxydict)) {
                    Py_DECREF(proxydict);
                    PyErr_SetNone(PyExc_ValueError);
                    return NULL;
                 }
#endif  // PYPY_VERSION
                 i = PyObject_Size(proxydict);
                 Py_DECREF(proxydict);
                 return PyLong_FromLong(i);
             """),
            ])
        assert module.dict_proxy({'a': 1, 'b': 2}) == 2
