import py
import py.test
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.typedef import interp_attrproperty, GetSetProperty
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.function import BuiltinFunction
from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
from pypy.objspace.cpy.objspace import CPyObjSpace, W_Object
from pypy.translator.c.test.test_genc import compile


class W_MyType(Wrappable):
    def __init__(self, space, x=1):
        self.space = space
        self.x = x

    def multiply(self, w_y):
        space = self.space
        y = space.int_w(w_y)
        return space.wrap(self.x * y)

    def fget_x(space, self):
        return space.wrap(self.x)

    def fset_x(space, self, w_value):
        self.x = space.int_w(w_value)

def test_direct():
    W_MyType.typedef = TypeDef("MyType")
    space = CPyObjSpace()
    x = W_MyType(space)
    y = W_MyType(space)
    w_x = space.wrap(x)
    w_y = space.wrap(y)
    assert space.interp_w(W_MyType, w_x) is x
    assert space.interp_w(W_MyType, w_y) is y
    py.test.raises(OperationError, "space.interp_w(W_MyType, space.wrap(42))")


def test_get_blackbox():
    W_MyType.typedef = TypeDef("MyType")
    space = CPyObjSpace()

    def make_mytype():
        return space.wrap(W_MyType(space))
    fn = compile(make_mytype, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res = fn()
    assert type(res).__name__ == 'MyType'


def test_get_blackboxes():
    W_MyType.typedef = TypeDef("MyType")

    class W_MyType2(Wrappable):
        def __init__(self, space, x=1):
            self.space = space
            self.x = x
    W_MyType2.typedef = TypeDef("MyType2")
    space = CPyObjSpace()

    def make_mytype(n):
        if n:
            return space.wrap(W_MyType2(space))
        else:
            return space.wrap(W_MyType(space))
    fn = compile(make_mytype, [int],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res2 = fn(1)
    assert type(res2).__name__ == 'MyType2'
    res = fn(0)
    assert type(res).__name__ == 'MyType'


def test_blackbox():
    W_MyType.typedef = TypeDef("MyType")
    space = CPyObjSpace()

    def mytest(w_myobj):
        myobj = space.interp_w(W_MyType, w_myobj, can_be_None=True)
        if myobj is None:
            myobj = W_MyType(space)
            myobj.abc = 1
        myobj.abc *= 2
        w_myobj = space.wrap(myobj)
        w_abc = space.wrap(myobj.abc)
        return space.newtuple([w_myobj, w_abc])

    def fn(obj):
        w_obj = W_Object(obj)
        w_res = mytest(w_obj)
        return w_res.value
    fn.allow_someobjects = True

    fn = compile(fn, [object],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res, abc = fn(None)
    assert abc == 2
    assert type(res).__name__ == 'MyType'

    res2, abc = fn(res)
    assert abc == 4
    assert res2 is res

    res2, abc = fn(res)
    assert abc == 8
    assert res2 is res

    res2, abc = fn(res)
    assert abc == 16
    assert res2 is res


def test_class_attr():
    W_MyType.typedef = TypeDef("MyType",
                               hello = 7)
    space = CPyObjSpace()

    def make_mytype():
        return space.wrap(W_MyType(space))
    fn = compile(make_mytype, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res = fn()
    assert type(res).__name__ == 'MyType'
    assert res.hello == 7
    assert type(res).hello == 7


def test_method():
    W_MyType.typedef = TypeDef("MyType",
                               multiply = interp2app(W_MyType.multiply))
    space = CPyObjSpace()
    assert space.int_w(W_MyType(space, 6).multiply(space.wrap(7))) == 42

    def make_mytype():
        return space.wrap(W_MyType(space, 123))
    fn = compile(make_mytype, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res = fn()
    assert type(res).__name__ == 'MyType'
    assert res.multiply(3) == 369

def test_special_method():
    W_MyType.typedef = TypeDef("MyType",
                               __mul__ = interp2app(W_MyType.multiply))
    space = CPyObjSpace()
    assert space.int_w(W_MyType(space, 6).multiply(space.wrap(7))) == 42

    def make_mytype():
        return space.wrap(W_MyType(space, 123))
    fn = compile(make_mytype, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res = fn()
    assert type(res).__name__ == 'MyType'
    assert res * 3 == 369


def test_interp_attrproperty():
    W_MyType.typedef = TypeDef("MyType",
                               x = interp_attrproperty("x", W_MyType))
    space = CPyObjSpace()

    def mytest(w_myobj):
        myobj = space.interp_w(W_MyType, w_myobj, can_be_None=True)
        if myobj is None:
            myobj = W_MyType(space)
            myobj.x = 1
        myobj.x *= 2
        w_myobj = space.wrap(myobj)
        w_x = space.wrap(myobj.x)
        return space.newtuple([w_myobj, w_x])

    def fn(obj):
        w_obj = W_Object(obj)
        w_res = mytest(w_obj)
        return w_res.value
    fn.allow_someobjects = True

    fn = compile(fn, [object],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res, x = fn(None)
    assert type(res).__name__ == 'MyType'
    assert x == 2
    assert res.x == 2

    res2, x = fn(res)
    assert res2 is res
    assert x == 4
    assert res.x == 4


def test_getset():
    getset_x = GetSetProperty(W_MyType.fget_x, W_MyType.fset_x, cls=W_MyType)
    W_MyType.typedef = TypeDef("MyType",
                               x = getset_x)
    space = CPyObjSpace()

    def mytest(w_myobj):
        myobj = space.interp_w(W_MyType, w_myobj, can_be_None=True)
        if myobj is None:
            myobj = W_MyType(space)
            myobj.x = 1
        myobj.x *= 2
        w_myobj = space.wrap(myobj)
        w_x = space.wrap(myobj.x)
        return space.newtuple([w_myobj, w_x])

    def fn(obj):
        w_obj = W_Object(obj)
        w_res = mytest(w_obj)
        return w_res.value
    fn.allow_someobjects = True

    fn = compile(fn, [object],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res, x = fn(None)
    assert type(res).__name__ == 'MyType'
    assert x == 2
    assert res.x == 2
    res.x += 100
    assert res.x == 102

    res2, x = fn(res)
    assert res2 is res
    assert x == 204
    assert res.x == 204

def test_expose_types():
    W_MyType.typedef = TypeDef("MyType")

    class W_MyType2(Wrappable):
        def __init__(self, space, x=1):
            self.space = space
            self.x = x
    W_MyType2.typedef = TypeDef("MyType2")
    space = CPyObjSpace()

    def get_mytype(n):
        if n:
            return space.gettypefor(W_MyType2)
        else:
            return space.gettypefor(W_MyType)
        return None
    fn = compile(get_mytype, [int],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    w_mytype2 = get_mytype(1)
    w_name = space.getattr(w_mytype2, space.wrap('__name__'))
    assert space.unwrap(w_name) == 'MyType2'
    w_mytype = get_mytype(0)
    w_name = space.getattr(w_mytype, space.wrap('__name__'))
    assert space.unwrap(w_name) == 'MyType'

    res2 = fn(1)
    assert type(res2) == type
    assert res2.__name__ == 'MyType2'
    res = fn(0)
    assert res.__name__ == 'MyType'

def test_with_new():
    def mytype_new(space, w_subtype, x):
        return space.wrap(W_MyType(space, x))
    mytype_new.unwrap_spec = [ObjSpace, W_Root, int]

    W_MyType.typedef = TypeDef("MyType",
                               __new__ = interp2app(mytype_new),
                               x = interp_attrproperty("x", W_MyType))
    space = CPyObjSpace()

    def build():
        w_type = space.gettypefor(W_MyType)
        return space.call_function(w_type, space.wrap(42))

    w_obj = build()
    w_name = space.getattr(space.type(w_obj), space.wrap('__name__'))
    assert space.unwrap(w_name) == 'MyType'
    assert space.int_w(space.getattr(w_obj, space.wrap('x'))) == 42

    fn = compile(build, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    res = fn()
    assert type(res).__name__ == 'MyType'
    assert res.x == 42

def test_with_new_with_allocate_instance():
    def mytype_new(space, w_subtype, x):
        w_obj = space.allocate_instance(W_MyType, w_subtype)
        W_MyType.__init__(space.interp_w(W_MyType, w_obj), space, x)
        return w_obj
    mytype_new.unwrap_spec = [ObjSpace, W_Root, int]

    W_MyType.typedef = TypeDef("MyType",
                               __new__ = interp2app(mytype_new),
                               x = interp_attrproperty("x", W_MyType))
    space = CPyObjSpace()

    def build():
        w_type = space.gettypefor(W_MyType)
        return space.call_function(w_type, space.wrap(42))

    w_obj = build()
    w_name = space.getattr(space.type(w_obj), space.wrap('__name__'))
    assert space.unwrap(w_name) == 'MyType'
    assert space.int_w(space.getattr(w_obj, space.wrap('x'))) == 42

    fn = compile(build, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    res = fn()
    assert type(res).__name__ == 'MyType'
    assert res.x == 42

def test_with_new_with_allocate_instance_subclass():
    py.test.skip("dealloction for now segfaults")
    def mytype_new(space, w_subtype, x):
        w_obj = space.allocate_instance(W_MyType, w_subtype)
        W_MyType.__init__(space.interp_w(W_MyType, w_obj), space, x)
        return w_obj
    mytype_new.unwrap_spec = [ObjSpace, W_Root, int]

    W_MyType.typedef = TypeDef("MyType",
                               __new__ = interp2app(mytype_new),
                               x = interp_attrproperty("x", W_MyType))
    space = CPyObjSpace()

    def build():
        w_type = space.gettypefor(W_MyType)
        return space.call_function(w_type, space.wrap(42))

    fn = compile(build, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    res = fn()
    assert type(res).__name__ == 'MyType'
    assert res.x == 42

    class MyType2(type(res)):
        pass

    res2 = MyType2(42)
    assert type(res2) is MyType2
    assert res2.x == 42

    del res2
    import gc
    gc.collect()

def test_prebuilt_type():
    def mytype_new(space, w_subtype, x):
        return space.wrap(W_MyType(space, x))
    mytype_new.unwrap_spec = [ObjSpace, W_Root, int]

    W_MyType.typedef = TypeDef("MyType",
                               __new__ = interp2app(mytype_new))
    space = CPyObjSpace()

    w_type = space.gettypefor(W_MyType)
    def build():
        return space.call_function(w_type, space.wrap(42))

    w_obj = build()
    w_name = space.getattr(space.type(w_obj), space.wrap('__name__'))
    assert space.unwrap(w_name) == 'MyType'

    fn = compile(build, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    res = fn()
    assert type(res).__name__ == 'MyType'

def test_prebuilt_instance():
    def mytype_new(space, w_subtype, x):
        return space.wrap(W_MyType(space, x))
    mytype_new.unwrap_spec = [ObjSpace, W_Root, int]

    W_MyType.typedef = TypeDef("MyType",
                               __new__ = interp2app(mytype_new))
    space = CPyObjSpace()

    w_type = space.gettypefor(W_MyType)
    w_obj = space.call_function(w_type, space.wrap(42))
    def build():
        return w_obj

    w_name = space.getattr(space.type(w_obj), space.wrap('__name__'))
    assert space.unwrap(w_name) == 'MyType'

    fn = compile(build, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    res = fn()
    assert type(res).__name__ == 'MyType'

def test_prebuilt_instance_inside_pyobj():
    def mytype_new(space, w_subtype, x):
        return space.wrap(W_MyType(space, x))
    mytype_new.unwrap_spec = [ObjSpace, W_Root, int]

    W_MyType.typedef = TypeDef("MyType",
                               __new__ = interp2app(mytype_new))
    space = CPyObjSpace()

    w_type = space.gettypefor(W_MyType)
    w_obj = space.call_function(w_type, space.wrap(42))
    w_mydict = space.newdict()
    space.setitem(w_mydict, space.wrap('hello'), w_obj)
    def build():
        return w_mydict

    fn = compile(build, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    res = fn()
    assert type(res) is dict
    assert res.keys() == ['hello']
    assert type(res['hello']).__name__ == 'MyType'

# ____________________________________________________________

def test_interp_dict():
    space = CPyObjSpace()
    W_MyType.typedef = TypeDef("MyType", hello = 7)

    def entry_point(x):
        d = {W_MyType(space, x): True}
        return space.wrap(d.keys()[0])

    fn = compile(entry_point, [int],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    res = fn(42)
    assert res.hello == 7
