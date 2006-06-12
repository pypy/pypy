from pypy.objspace.cpy.objspace import CPyObjSpace
from pypy.tool.pytest.appsupport import raises_w

def test_simple():
    space = CPyObjSpace()
    wk1 = space.wrap('key')
    wone = space.wrap(1)
    d = space.newdict([(space.wrap('zero'),space.wrap(0))])
    space.setitem(d,wk1,wone)
    wback = space.getitem(d,wk1)
    assert space.eq_w(wback,wone)

def test_wrap():
    space = CPyObjSpace()
    w_res = space.add(space.wrap(1.0), space.wrap(1.5))
    assert space.eq_w(w_res, space.wrap(2.5))
    res = space.float_w(w_res)
    assert res == 2.5

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
