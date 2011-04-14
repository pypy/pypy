import py

from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    Py_LT, Py_LE, Py_NE, Py_EQ, Py_GE, Py_GT)

class TestObject(BaseApiTest):
    def test_IsTrue(self, space, api):
        assert api.PyObject_IsTrue(space.wrap(1.0)) == 1
        assert api.PyObject_IsTrue(space.wrap(False)) == 0
        assert api.PyObject_IsTrue(space.wrap(0)) == 0

    def test_Not(self, space, api):
        assert api.PyObject_Not(space.wrap(False)) == 1
        assert api.PyObject_Not(space.wrap(0)) == 1
        assert api.PyObject_Not(space.wrap(True)) == 0
        assert api.PyObject_Not(space.wrap(3.14)) == 0

    def test_exception(self, space, api):
        class C:
            def __nonzero__(self):
                raise ValueError

        assert api.PyObject_IsTrue(space.wrap(C())) == -1
        assert api.PyObject_Not(space.wrap(C())) == -1
        api.PyErr_Clear()

    def test_HasAttr(self, space, api):
        hasattr_ = lambda w_obj, name: api.PyObject_HasAttr(w_obj,
                                                            space.wrap(name))
        assert hasattr_(space.wrap(''), '__len__')
        assert hasattr_(space.w_int, '__eq__')
        assert not hasattr_(space.w_int, 'nonexistingattr')

        buf = rffi.str2charp('__len__')
        assert api.PyObject_HasAttrString(space.w_str, buf)
        assert not api.PyObject_HasAttrString(space.w_int, buf)
        rffi.free_charp(buf)

    def test_SetAttr(self, space, api):
        class X:
            pass
        x = X()
        api.PyObject_SetAttr(space.wrap(x), space.wrap('test'), space.wrap(5))
        assert not api.PyErr_Occurred()
        assert x.test == 5
        assert api.PyObject_HasAttr(space.wrap(x), space.wrap('test'))
        api.PyObject_SetAttr(space.wrap(x), space.wrap('test'), space.wrap(10))
        assert x.test == 10

        buf = rffi.str2charp('test')
        api.PyObject_SetAttrString(space.wrap(x), buf, space.wrap(20))
        rffi.free_charp(buf)
        assert x.test == 20

    def test_getattr(self, space, api):
        charp1 = rffi.str2charp("__len__")
        charp2 = rffi.str2charp("not_real")
        assert api.PyObject_GetAttrString(space.wrap(""), charp1)
        assert not api.PyObject_GetAttrString(space.wrap(""), charp2)
        assert api.PyErr_Occurred() is space.w_AttributeError
        api.PyErr_Clear()
        assert api.PyObject_DelAttrString(space.wrap(""), charp1) == -1
        assert api.PyErr_Occurred() is space.w_AttributeError
        api.PyErr_Clear()
        rffi.free_charp(charp1)
        rffi.free_charp(charp2)

        assert api.PyObject_GetAttr(space.wrap(""), space.wrap("__len__"))
        assert api.PyObject_DelAttr(space.wrap(""), space.wrap("__len__")) == -1
        api.PyErr_Clear()

    def test_getitem(self, space, api):
        w_t = space.wrap((1, 2, 3, 4, 5))
        assert space.unwrap(api.PyObject_GetItem(w_t, space.wrap(3))) == 4

        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a key!"), space.wrap(72))
        assert space.unwrap(api.PyObject_GetItem(w_d, space.wrap("a key!"))) == 72

        assert api.PyObject_SetItem(w_d, space.wrap("key"), space.w_None) == 0
        assert space.getitem(w_d, space.wrap("key")) is space.w_None

        assert api.PyObject_DelItem(w_d, space.wrap("key")) == 0
        assert api.PyObject_GetItem(w_d, space.wrap("key")) is None
        assert api.PyErr_Occurred() is space.w_KeyError
        api.PyErr_Clear()

    def test_size(self, space, api):
        assert api.PyObject_Size(space.newlist([space.w_None])) == 1
        
    def test_repr(self, space, api):
        w_list = space.newlist([space.w_None, space.wrap(42)])
        assert space.str_w(api.PyObject_Repr(w_list)) == "[None, 42]"
        assert space.str_w(api.PyObject_Repr(space.wrap("a"))) == "'a'"
        
        w_list = space.newlist([space.w_None, space.wrap(42)])
        assert space.str_w(api.PyObject_Str(w_list)) == "[None, 42]"
        assert space.str_w(api.PyObject_Str(space.wrap("a"))) == "a"
        
    def test_RichCompare(self, space, api):
        def compare(w_o1, w_o2, opid):
            res = api.PyObject_RichCompareBool(w_o1, w_o2, opid)
            w_res = api.PyObject_RichCompare(w_o1, w_o2, opid)
            assert space.is_true(w_res) == res
            return res
        
        def test_compare(o1, o2):
            w_o1 = space.wrap(o1)
            w_o2 = space.wrap(o2)
            
            for opid, expected in [
                    (Py_LT, o1 <  o2), (Py_LE, o1 <= o2),
                    (Py_NE, o1 != o2), (Py_EQ, o1 == o2),
                    (Py_GT, o1 >  o2), (Py_GE, o1 >= o2)]:
                assert compare(w_o1, w_o2, opid) == expected

        test_compare(1, 2)
        test_compare(2, 2)
        test_compare('2', '1')
        
        w_i = space.wrap(1)
        assert api.PyObject_RichCompareBool(w_i, w_i, 123456) == -1
        assert api.PyErr_Occurred() is space.w_SystemError
        api.PyErr_Clear()
        
    def test_IsInstance(self, space, api):
        assert api.PyObject_IsInstance(space.wrap(1), space.w_int) == 1
        assert api.PyObject_IsInstance(space.wrap(1), space.w_float) == 0
        assert api.PyObject_IsInstance(space.w_True, space.w_int) == 1
        assert api.PyObject_IsInstance(
            space.wrap(1), space.newtuple([space.w_int, space.w_float])) == 1
        assert api.PyObject_IsInstance(space.w_type, space.w_type) == 1
        assert api.PyObject_IsInstance(space.wrap(1), space.w_None) == -1
        api.PyErr_Clear()

    def test_IsSubclass(self, space, api):
        assert api.PyObject_IsSubclass(space.w_type, space.w_type) == 1
        assert api.PyObject_IsSubclass(space.w_type, space.w_object) == 1
        assert api.PyObject_IsSubclass(space.w_object, space.w_type) == 0
        assert api.PyObject_IsSubclass(
            space.w_type, space.newtuple([space.w_int, space.w_type])) == 1
        assert api.PyObject_IsSubclass(space.wrap(1), space.w_type) == -1
        api.PyErr_Clear()

    def test_fileno(self, space, api):
        assert api.PyObject_AsFileDescriptor(space.wrap(1)) == 1
        assert api.PyObject_AsFileDescriptor(space.wrap(-20)) == -1
        assert api.PyErr_Occurred() is space.w_ValueError
        api.PyErr_Clear()

        w_File = space.appexec([], """():
            class File:
                def fileno(self):
                    return 42
            return File""")
        w_f = space.call_function(w_File)
        assert api.PyObject_AsFileDescriptor(w_f) == 42
    
    def test_hash(self, space, api):
        assert api.PyObject_Hash(space.wrap(72)) == 72
        assert api.PyObject_Hash(space.wrap(-1)) == -1
        assert (api.PyObject_Hash(space.wrap([])) == -1 and
            api.PyErr_Occurred() is space.w_TypeError)
        api.PyErr_Clear()

    def test_type(self, space, api):
        assert api.PyObject_Type(space.wrap(72)) is space.w_int

    def test_compare(self, space, api):
        assert api.PyObject_Compare(space.wrap(42), space.wrap(72)) == -1
        assert api.PyObject_Compare(space.wrap(72), space.wrap(42)) == 1
        assert api.PyObject_Compare(space.wrap("a"), space.wrap("a")) == 0

    def test_cmp(self, space, api):
        w = space.wrap
        with lltype.scoped_alloc(rffi.INTP.TO, 1) as ptr:
            assert api.PyObject_Cmp(w(42), w(72), ptr) == 0
            assert ptr[0] == -1
            assert api.PyObject_Cmp(w("a"), w("a"), ptr) == 0
            assert ptr[0] == 0
            assert api.PyObject_Cmp(w(u"\xe9"), w("\xe9"), ptr) < 0
            assert api.PyErr_Occurred()
            api.PyErr_Clear()

    def test_unicode(self, space, api):
        assert space.unwrap(api.PyObject_Unicode(space.wrap([]))) == u"[]"
        assert space.unwrap(api.PyObject_Unicode(space.wrap("e"))) == u"e"
        assert api.PyObject_Unicode(space.wrap("\xe9")) is None
        api.PyErr_Clear()

class AppTestObject(AppTestCpythonExtensionBase):
    def setup_class(cls):
        AppTestCpythonExtensionBase.setup_class.im_func(cls)
        cls.w_tmpname = cls.space.wrap(str(py.test.ensuretemp("out", dir=0)))

    def test_TypeCheck(self):
        module = self.import_extension('foo', [
            ("typecheck", "METH_VARARGS",
             """
                 PyObject *obj = PyTuple_GET_ITEM(args, 0);
                 PyTypeObject *type = (PyTypeObject *)PyTuple_GET_ITEM(args, 1);
                 return PyBool_FromLong(PyObject_TypeCheck(obj, type));
             """)])
        assert module.typecheck(1, int)
        assert module.typecheck('foo', str)
        assert module.typecheck('foo', object)
        assert module.typecheck(1L, long)
        assert module.typecheck(True, bool)
        assert module.typecheck(1.2, float)
        assert module.typecheck(int, type)

    def test_print(self):
        module = self.import_extension('foo', [
            ("dump", "METH_VARARGS",
             """
                 PyObject *fname = PyTuple_GetItem(args, 0);
                 PyObject *obj = PyTuple_GetItem(args, 1);

                 FILE *fp = fopen(PyString_AsString(fname), "wb");
                 int ret;
                 if (fp == NULL)
                     Py_RETURN_NONE;
                 ret = PyObject_Print(obj, fp, Py_PRINT_RAW);
                 fclose(fp);
                 if (ret < 0)
                     return NULL;
                 Py_RETURN_TRUE;
             """)])
        assert module.dump(self.tmpname, None)
        assert open(self.tmpname).read() == 'None'
