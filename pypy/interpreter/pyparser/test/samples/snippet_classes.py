class A:
    def with_white_spaces_before(self):
        pass

    def another_method(self, foo):
        bar = foo


class B(object, A):
    def foo(self, bar):
        a = 2
        return "spam"
