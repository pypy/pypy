from pypy.objspace.cpy.objspace import CPyObjSpace
from pypy.tool.pytest.appsupport import raises_w
from pypy.rlib.rarithmetic import r_longlong, r_ulonglong
from pypy.rlib.rbigint import rbigint
import py

def test_simple():
    space = CPyObjSpace()
    wk1 = space.wrap('key')
    wone = space.wrap(1)
    d = space.newdict()
    space.setitem(d,space.wrap('zero'),space.wrap(0))
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

def test_wrapstring():
    space = CPyObjSpace()
    w = space.wrap('AB')
    assert space.str_w(w) == 'AB'

def test_wrapunicode():
    py.test.skip("fix me")
    space = CPyObjSpace()
    w = space.wrap(unichr(65) + unichr(66))
    assert space.is_w(space.type(w), space.w_unicode)
    for i in range(2):
        code = space.int_w(space.ord(space.getitem(w, space.wrap(i))))
        assert code == 65+i

def test_ord():
    py.test.skip("fix me")
    space = CPyObjSpace()
    w = space.wrap('A')
    assert space.int_w(space.ord(w)) == 65
    w = space.wrap('\x00')
    assert space.int_w(space.ord(w)) == 0
    w = space.wrap(unichr(65))
    assert space.int_w(space.ord(w)) == 65
    w = space.wrap(unichr(0))
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

def test_lookup():
    space = CPyObjSpace()
    class X(object):
        def f():
            return 5
    def g():
        return 7
    x = X()
    x.f = g
    w = space.W_Object(x)
    w_f = space.lookup(w, "f")
    w_5 = space.call_function(w_f)
    assert space.int_w(w_5) == 5

def test_callable():
    space = CPyObjSpace()
    assert space.is_true(space.callable(space.w_int))
    assert not space.is_true(space.callable(space.w_Ellipsis))

def test_newfloat():
    space = CPyObjSpace()
    fl1 = space.wrap(1.4)
    fl2 = space.newfloat(1.4)
    assert space.is_true(space.eq(fl1, fl2))

def test_newlong():
    space = CPyObjSpace()
    i1 = space.newlong(42)
    i2 = space.newint(42)
    assert space.is_true(space.eq(i1, i2))
    assert space.is_true(space.ne(space.type(i1), space.type(i2)))

def test_bigint_w():
    space = CPyObjSpace()
    r1 = space.bigint_w(space.newlong(42))
    assert isinstance(r1, rbigint)
    assert r1.eq(rbigint.fromint(42))
    # cpython digit size
    assert space.bigint_w(space.newlong(2**8)).eq(rbigint.fromint(2**8))
    # rpython digit size
    assert space.bigint_w(space.newlong(2**15)).eq(rbigint.fromint(2**15))
    # and negative numbers
    assert space.bigint_w(space.newlong(-1)).eq(rbigint.fromint(-1))
    assert space.bigint_w(space.newlong(-2**8)).eq(rbigint.fromint(-2**8))
    assert space.bigint_w(space.newlong(-2**15)).eq(rbigint.fromlong(-2**15))

