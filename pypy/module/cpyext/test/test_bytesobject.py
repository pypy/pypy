from pypy.module.cpyext.test.test_api import BaseApiTest

class TestBytes(BaseApiTest):
    def test_FromObject(self, space, api):
        w_obj = space.wrapbytes("test")
        assert space.eq_w(w_obj, api.PyBytes_FromObject(w_obj))
        w_obj = space.call_function(space.w_bytearray, w_obj)
        assert space.eq_w(w_obj, api.PyBytes_FromObject(w_obj))
        w_obj = space.wrap(u"test")
        assert api.PyBytes_FromObject(w_obj) is None
        api.PyErr_Clear()
