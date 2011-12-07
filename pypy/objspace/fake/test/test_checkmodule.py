import py
from pypy.objspace.fake.checkmodule import checkmodule
from pypy.objspace.fake.objspace import FakeObjSpace, is_root
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, W_Root, ObjSpace


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
    space.translates()
    assert len(check) == 1

def test_wrap_interp2app_int():
    see, check = make_checker()
    def foobar(space, x, w_y, z):
        is_root(w_y)
        see()
        return space.wrap(x - z)
    space = FakeObjSpace()
    space.wrap(interp2app(foobar, unwrap_spec=[ObjSpace, int, W_Root, int]))
    space.translates()
    assert check


def test_gettypefor_untranslated():
    py.test.skip("in-progress")
    class W_Foo(Wrappable):
        pass
    W_Foo.typedef = TypeDef('foo',
                            __module__ = 'barmod',
                            do_it = interp2app(W_Foo.do_it))
    see, check = make_checker()
    space = FakeObjSpace()
    space.gettypefor(W_Foo)

def test_itertools_module():
    checkmodule('itertools')
