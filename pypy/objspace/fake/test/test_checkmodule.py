from pypy.objspace.fake.checkmodule import checkmodule, FakeObjSpace
from pypy.interpreter.gateway import interp2app


def make_checker():
    check = []
    def see():
        check.append(True)
    see._annspecialcase_ = 'specialize:memo'
    return see, check


def test_wrap_interp2app():
    see, check = make_checker()
    space = FakeObjSpace()
    assert len(space._seen_extras) == 0
    assert len(check) == 0
    space.wrap(interp2app(lambda space: see()))
    assert len(space._seen_extras) == 1
    assert len(check) == 0
    space.translates(lambda: None)
    assert len(check) == 1

def test_itertools_module():
    checkmodule('itertools')
