from pypy.objspace.fake.objspace import FakeObjSpace

def test_create():
    FakeObjSpace()


class TestTranslate:
    def setup_method(self, meth):
        self.space = FakeObjSpace()

    def test_simple(self):
        space = self.space
        space.translates(lambda w_x, w_y: space.add(w_x, w_y))
