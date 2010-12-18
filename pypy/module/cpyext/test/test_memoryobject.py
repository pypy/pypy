import py
from pypy.module.cpyext.test.test_api import BaseApiTest

class TestMemoryViewObject(BaseApiTest):
    def test_fromobject(self, space, api):
        if space.is_true(space.lt(space.sys.get('version_info'),
                                  space.wrap((2, 7)))):
            py.test.skip("unsupported before Python 2.7")

        w_hello = space.wrap("hello")
        w_view = api.PyMemoryView_FromObject(w_hello)
        w_bytes = space.call_method(w_view, "tobytes")
        assert space.unwrap(w_bytes) == "hello"
