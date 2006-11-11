from pypy.rlib.rctypesobject import *

def test_primitive():
    x = rc_int.allocate()
    assert x.get_value() == 0
    x.set_value(17)
    assert x.get_value() == 17

def test_ptr():
    x = rc_int.allocate()
    p1 = pointer(x)
    p2 = pointer(x)
    x.set_value(17)
    assert p1.get_contents().get_value() == 17
    p2.get_contents().set_value(18)
    assert x.get_value() == 18
    del x
    assert p1.get_contents().get_value() == 18

def test_struct():
    x = rc_int.allocate()
    x.set_value(42)
    S = makeRStruct('S', [('x', rc_int),
                          ('y', makeRPointer(rc_int))])
    s = S.allocate()
    s.ref_x().set_value(12)
    s.ref_y().set_contents(x)
    assert s.ref_x().get_value() == 12
    assert s.ref_y().get_contents().get_value() == 42

def test_copyfrom():
    x1 = rc_int.allocate()
    x1.set_value(101)
    p1 = pointer(x1)
    x2 = rc_int.allocate()
    x2.set_value(202)
    p2 = pointer(x2)
    del x1, x2
    p1.copyfrom(p2)
    assert p1.get_contents().sameaddr(p2.get_contents())
    p1.get_contents().set_value(303)
    assert p2.get_contents().get_value() == 303
    del p2
    import gc; gc.collect()
    assert p1.get_contents().get_value() == 303
