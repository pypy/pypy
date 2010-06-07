from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest

class TestDatetime(BaseApiTest):
    def test_time(self, space, api):
        w_time = api.PyTime_FromTime(23, 15, 40, 123456)
        assert space.unwrap(space.str(w_time)) == '23:15:40.123456'
    def test_deltacheck(self, space, api):
        w_delta = space.appexec([space.wrap(3), space.wrap(15)], """(days, seconds):
            from datetime import timedelta
            return timedelta(days, seconds)
        """)
        assert api.PyDelta_Check(w_delta)

        w_delta = space.appexec([space.wrap(1), space.wrap(1), space.wrap(1999)], """(day, month, year):
            from datetime import datetime
            return datetime.now() - datetime(year, month, day)
        """)
        assert api.PyDelta_Check(w_delta)
