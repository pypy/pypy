"""Module docstring."""

import autopath
from pypy.tool import newtest


def test_function1():
    raise newtest.service.fail("failed test")

def test_function2():
    newtest.service.skip()


class TestDummy1(newtest.TestCase):
    """
    Example of a docstring for a class.
    """
    def test_success1(self):
        self.assertEquals(1+1, 2)

    def test_error1(self):
        raise TypeError("intentional TypeError")

    def test_failure1(self):
        raise self.fail("fail deliberately in test_failure1")


class TestDummy2(newtest.TestCase):
    def test_success2(self):
        self.assertEquals(1+1, 2)

    def test_error2(self):
        """Docstring of a method."""
        raise ValueError("intentional ValueError")

    def test_failure2(self):
        raise self.fail("fail deliberately in test_failure2")


class TestSkip1(newtest.TestCase):
    def setUp(self):
        self.skip()

    def test_skip1(self):
        pass


class TestSkip2(newtest.TestCase):
    def test_skip2(self):
        self.skip()


# these items shouldn't be identified as testable objects
def f():
    raise TypeError


class X:
    def test_skip(self):
        newtest.service.skip()
