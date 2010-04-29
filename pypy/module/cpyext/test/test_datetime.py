from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest

class TestDatetime(BaseApiTest):
    def test_time(self, space, api):
        w_time = api.PyTime_FromTime(23, 15, 40, 123456)
        assert space.unwrap(space.str(w_time)) == '23:15:40.123456'
