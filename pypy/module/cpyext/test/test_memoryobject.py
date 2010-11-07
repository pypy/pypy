from pypy.module.cpyext.test.test_api import BaseApiTest

class TestMemoryViewObject(BaseApiTest):
    def test_fromobject(self, space, api):
        w_hello = space.wrap("hello")
        w_view = api.PyMemoryView_FromObject(w_hello)
        w_bytes = space.call_method(w_view, "tobytes")
        assert space.unwrap(w_bytes) == "hello"
