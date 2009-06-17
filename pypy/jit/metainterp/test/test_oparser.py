
from pypy.rpython.lltypesystem import lltype

from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import AbstractDescr, BoxInt

def test_basic_parse():
    x = """
    [i0, i1]
    i2 = int_add(i0, i1)
    # a comment
    i3 = int_sub(i2, 3)
    fail()
    """
    loop = parse(x)
    assert len(loop.operations) == 3
    assert [op.opnum for op in loop.operations] == [rop.INT_ADD, rop.INT_SUB,
                                                    rop.FAIL]
    assert len(loop.inputargs) == 2

def test_const_ptr_subops():
    x = """
    [p0]
    guard_class(p0, ConstClass(vtable))
        fail()
    """
    S = lltype.Struct('S')
    vtable = lltype.nullptr(S)
    loop = parse(x, None, locals())
    assert len(loop.operations) == 1
    assert len(loop.operations[0].suboperations) == 1

def test_descr():
    class Xyz(AbstractDescr):
        pass
    
    x = """
    [p0]
    i1 = getfield_gc(p0, descr=stuff)
    """
    stuff = Xyz()
    loop = parse(x, None, locals())
    assert loop.operations[0].descr is stuff

def test_after_fail():
    x = """
    [i0]
    guard_value(i0, 3)
       fail()
    i1 = int_add(1, 2)
    """
    loop = parse(x, None, {})
    assert len(loop.operations) == 2

def test_descr_setfield():
    class Xyz(AbstractDescr):
        pass
    
    x = """
    [p0]
    setfield_gc(p0, 3, descr=stuff)
    """
    stuff = Xyz()
    loop = parse(x, None, locals())
    assert loop.operations[0].descr is stuff

def test_boxname():
    x = """
    [i42]
    i50 = int_add(i42, 1)
    """
    loop = parse(x, None, {})
    assert str(loop.inputargs[0]) == 'i42'
    assert str(loop.operations[0].result) == 'i50'

def test_getboxes():
    x = """
    [i0]
    i1 = int_add(i0, 10)
    """
    loop = parse(x, None, {})
    boxes = loop.getboxes()
    assert boxes.i0 is loop.inputargs[0]
    assert boxes.i1 is loop.operations[0].result
    
def test_setvalues():
    x = """
    [i0]
    i1 = int_add(i0, 10)
    """
    loop = parse(x, None, {})
    loop.setvalues(i0=32, i1=42)
    assert loop.inputargs[0].value == 32
    assert loop.operations[0].result.value == 42

def test_boxkind():
    x = """
    [sum0]
    """
    loop = parse(x, None, {}, boxkinds={'sum': BoxInt})
    b = loop.getboxes()
    assert isinstance(b.sum0, BoxInt)
