from pypy.objspace.cpy.objspace import CPyObjSpace

def test_simple():
    space = CPyObjSpace()
    wk1 = space.wrap('key')
    wone = space.wrap(1)
    d = space.newdict([(space.wrap('zero'),space.wrap(0))])
    space.setitem(d,wk1,wone)
    wback = space.getitem(d,wk1)
    assert space.eq_w(wback,wone)

def test_demo():
    from pypy.module._demo import demo
    space = CPyObjSpace()
    w_time = demo.measuretime(space, 10, CPyObjSpace.W_Object(int))
    assert isinstance(w_time, CPyObjSpace.W_Object)
    assert isinstance(w_time.value, int)
