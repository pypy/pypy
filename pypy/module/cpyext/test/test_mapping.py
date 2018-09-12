from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.module.cpyext.pyobject import get_w_obj_and_decref


class TestMapping(BaseApiTest):
    def test_check(self, space, api):
        assert api.PyMapping_Check(space.newdict())
        assert not api.PyMapping_Check(space.newlist([]))
        assert not api.PyMapping_Check(space.newtuple([]))

    def test_size(self, space, api):
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a"), space.wrap("b"))

        assert api.PyMapping_Size(w_d) == 1
        assert api.PyMapping_Length(w_d) == 1

    def test_keys(self, space, api):
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a"), space.wrap("b"))

        assert space.eq_w(api.PyMapping_Keys(w_d), space.wrap(["a"]))
        assert space.eq_w(api.PyMapping_Values(w_d), space.wrap(["b"]))
        assert space.eq_w(api.PyMapping_Items(w_d), space.wrap([("a", "b")]))

    def test_setitemstring(self, space, api):
        w_d = space.newdict()
        key = rffi.str2charp("key")
        api.PyMapping_SetItemString(w_d, key, space.wrap(42))
        assert 42 == space.unwrap(get_w_obj_and_decref(space,
            api.PyMapping_GetItemString(w_d, key)))
        rffi.free_charp(key)

    def test_haskey(self, space, api):
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a"), space.wrap("b"))

        assert api.PyMapping_HasKey(w_d, space.wrap("a"))
        assert not api.PyMapping_HasKey(w_d, space.wrap("b"))

        assert api.PyMapping_HasKey(w_d, w_d) == 0
        # and no error is set


class AppTestMapping(AppTestCpythonExtensionBase):

    def test_getitemstring_returns_new_but_borrowed_ref(self):
        module = self.import_extension('foo', [
           ("test_mapping", "METH_O",
            '''
                PyObject *value = PyMapping_GetItemString(args, "a");
                /* officially, "value" can have a refcount equal to one,
                   but some code out there assumes that it has a refcnt
                   of at least two --- which is bogus --- because it
                   is generally kept alive by the container. */
                PyObject *refcnt = PyLong_FromLong(value->ob_refcnt);
                Py_DECREF(value);
                return refcnt;
            '''),])
        d = {"a": 42}
        res = module.test_mapping(d)
        assert res > 1
