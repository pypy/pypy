import autopath
from pypy.tool import newtest

class TestDummy1(newtest.TestCase):
    def test_success1(self):
        self.assertEquals(1+1, 2)

    def test_error1(self):
        raise ValueError

    def test_failure1(self):
        raise newtest.Failure


class TestDummy2(newtest.TestCase):
    def test_success2(self):
        self.assertEquals(1+1, 2)

    def test_error2(self):
        raise ValueError

    def test_failure2(self):
        raise newtest.Failure


class TestSkip1(newtest.TestCase):
    def setUp(self):
        raise newtest.Skipped

    def test_skip1(self):
        pass


class TestSkip2(newtest.TestCase):
    def test_skip2(self):
        raise newtest.Skipped
