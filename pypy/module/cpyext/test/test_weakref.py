from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest

class TestWeakReference(BaseApiTest):
    def test_weakref(self, space, api):
        w_obj = space.w_Exception
        w_ref = api.PyWeakref_NewRef(w_obj, space.w_None)
        assert w_ref is not None
        assert space.is_w(api.PyWeakref_GetObject(w_ref), w_obj)
        assert space.is_w(api.PyWeakref_LockObject(w_ref), w_obj)

        w_obj = space.newtuple([])
        assert api.PyWeakref_NewRef(w_obj, space.w_None) is None
        assert api.PyErr_Occurred() is space.w_TypeError
        api.PyErr_Clear()
