import pytest
from pypy.module.cpyext.test.test_api import BaseApiTest

class TestMemoryViewObject(BaseApiTest):
    def test_fromobject(self, space, api):
        if space.is_true(space.lt(space.sys.get('version_info'),
                                  space.wrap((2, 7)))):
            py.test.skip("unsupported before Python 2.7")

        w_hello = space.newbytes("hello")
        w_view = api.PyMemoryView_FromObject(w_hello)
        w_bytes = space.call_method(w_view, "tobytes")
        assert space.unwrap(w_bytes) == "hello"

    @pytest.mark.skipif(True, reason='write a test for this')
    def test_get_base_and_get_buffer(self, space, api):
        assert False # XXX test PyMemoryView_GET_BASE, PyMemoryView_GET_BUFFER
