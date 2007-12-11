
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable
from pypy.objspace.std.test.test_proxy_internals import AppProxy
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

class W_Wrapped(Wrappable):
    def new(space, w_type):
        return space.wrap(W_Wrapped())

W_Wrapped.typedef = TypeDef(
    'Wrapped',
    __new__ = interp2app(W_Wrapped.new.im_func)
)

class AppTestProxyNewtype(AppProxy):
    def setup_class(cls):
        AppProxy.setup_class.im_func(cls)
        cls.w_wrapped = cls.space.wrap(W_Wrapped())
        
    def test_one(self):
        x = type(self.wrapped)()
        print x
