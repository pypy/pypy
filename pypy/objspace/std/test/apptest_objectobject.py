from abc import ABCMeta, abstractmethod


def test_abstract_method_error_message_singular():
    class C(metaclass=ABCMeta):
        @abstractmethod
        def method_one(self):
            pass
    try:
        C()
    except TypeError as e:
        msg = str(e)
    else:
        raise AssertionError("expected TypeError")
    assert msg == ("Can't instantiate abstract class C without an "
                   "implementation for abstract method 'method_one'")


def test_abstract_method_error_message_plural():
    class D(metaclass=ABCMeta):
        @abstractmethod
        def method_one(self):
            pass
        @abstractmethod
        def method_two(self):
            pass
    try:
        D()
    except TypeError as e:
        msg = str(e)
    else:
        raise AssertionError("expected TypeError")
    assert msg == ("Can't instantiate abstract class D without an "
                   "implementation for abstract methods "
                   "'method_one', 'method_two'")
