from pypy.objspace.cpy.objspace import CPyObjSpace
from pypy.tool.pytest.appsupport import raises_w
from pypy.rpython.rarithmetic import r_longlong, r_ulonglong

def test_simple():
    space = CPyObjSpace()
    wk1 = space.wrap('key')
    wone = space.wrap(1)
    d = space.newdict([(space.wrap('zero'),space.wrap(0))])
    space.setitem(d,wk1,wone)
    wback = space.getitem(d,wk1)
    assert space.eq_w(wback,wone)
    assert space.is_true(space.contains(d,wk1))
    space.delitem(d,wk1)
    assert not space.is_true(space.contains(d,wk1))

def test_wrap():
    space = CPyObjSpace()
    w_res = space.add(space.wrap(1.0), space.wrap(1.5))
    assert space.eq_w(w_res, space.wrap(2.5))
    res = space.float_w(w_res)
    assert res == 2.5

def test_wraplonglongs():
    space = CPyObjSpace()
    w = space.wrap
    w_res = space.add(w(r_longlong(1)), w(r_ulonglong(1)))
    assert space.eq_w(w_res, w(2))
    res = space.int_w(w_res)
    assert res == 2

def test_str_w():
    space = CPyObjSpace()
    w_string = space.wrap('abc\x00def')
    assert space.str_w(w_string) == 'abc\x00def'

def test_demo():
    from pypy.module._demo import demo
    space = CPyObjSpace()
    w_time = demo.measuretime(space, 10, CPyObjSpace.W_Object(int))
    assert isinstance(w_time, CPyObjSpace.W_Object)
    assert isinstance(w_time.value, int)

def test_exception():
    space = CPyObjSpace()
    w1 = space.wrap('abc')
    w2 = space.wrap(11)
    raises_w(space, space.w_TypeError, space.sub, w1, w2)

def test_newstring():
    space = CPyObjSpace()
    w = space.newstring([space.wrap(65), space.wrap(66)])
    assert space.str_w(w) == 'AB'

def test_newunicode():
    space = CPyObjSpace()
    w = space.newunicode([65, 66])
    assert space.is_w(space.type(w), space.w_unicode)
    for i in range(2):
        code = space.int_w(space.ord(space.getitem(w, space.wrap(i))))
        assert code == 65+i

def test_ord():
    space = CPyObjSpace()
    w = space.wrap('A')
    assert space.int_w(space.ord(w)) == 65
    w = space.wrap('\x00')
    assert space.int_w(space.ord(w)) == 0
    w = space.newunicode([65])
    assert space.int_w(space.ord(w)) == 65
    w = space.newunicode([0])
    assert space.int_w(space.ord(w)) == 0

def test_id():
    space = CPyObjSpace()
    x = []
    w = space.W_Object(x)
    w_id = space.id(w)
    assert space.eq_w(w_id, space.wrap(id(x)))

def test_hash():
    space = CPyObjSpace()
    x = ("hello", 123)
    w = space.W_Object(x)
    w_hash = space.hash(w)
    assert space.eq_w(w_hash, space.wrap(hash(x)))

def test_setattr():
    space = CPyObjSpace()
    class X:
        pass
    w = space.W_Object(X)
    space.setattr(w, space.wrap('hello'), space.wrap(42))
    assert X.hello == 42
    space.delattr(w, space.wrap('hello'))
    assert not hasattr(X, 'hello')

def test_some_more_ops():
    space = CPyObjSpace()
    assert space.eq_w(space.nonzero(space.wrap(17)), space.w_True)
    assert space.eq_w(space.nonzero(space.wrap(0)), space.w_False)
    assert space.eq_w(space.hex(space.wrap(18)), space.wrap("0x12"))
    assert space.eq_w(space.oct(space.wrap(11)), space.wrap("013"))
    assert space.eq_w(space.cmp(space.wrap(6), space.wrap(9)), space.wrap(-1))

def test_complete():
    from pypy.interpreter.baseobjspace import ObjSpace
    space = CPyObjSpace()
    for name, symbol, arity, specialmethods in ObjSpace.MethodTable:
        assert hasattr(space, name)
    for name in ObjSpace.ConstantTable:
        assert hasattr(space, 'w_' + name)
    for name in ObjSpace.ExceptionTable:
        assert hasattr(space, 'w_' + name)
    for name in ObjSpace.IrregularOpTable:
        assert hasattr(space, name)
