
def test_something(space):
    assert space.w_None is space.w_None

class AppTestSomething:
    def test_method_app(self):
        assert 23 == 23

class TestSomething:
    def test_method(self):
        assert self.space

