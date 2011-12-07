from pypy.objspace.fake.objspace import FakeObjSpace, W_Root
from pypy.rlib.unroll import unrolling_iterable

def test_create():
    FakeObjSpace()


class TestTranslate:
    def setup_method(self, meth):
        self.space = FakeObjSpace()

    def test_simple(self):
        space = self.space
        space.translates(lambda w_x, w_y: space.add(w_x, w_y))

    def test_methodtable(self):
        space = self.space
        for fixed_arity in [1, 2, 3, 4]:
            #
            methodtable = [name for (name, _, arity, _) in space.MethodTable
                                if arity == fixed_arity]
            methodtable = unrolling_iterable(methodtable)
            args_w = (W_Root(),) * fixed_arity
            #
            def f():
                for name in methodtable:
                    getattr(space, name)(*args_w)
            #
            space.translates(f)
