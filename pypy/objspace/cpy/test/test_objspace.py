from pypy.objspace.cpy.objspace import CPyObjSpace

def test_simple():
    space = CPyObjSpace()
    wk1 = space.wrap('key')
    wone = space.wrap(1)
    d = space.newdict([(space.wrap('zero'),space.wrap(0))])
    space.setitem(d,wk1,wone)
    wback = space.getitem(d,wk1)
    assert space.eq_w(wback,wone)
