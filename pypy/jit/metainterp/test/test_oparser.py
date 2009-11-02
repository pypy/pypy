
from pypy.rpython.lltypesystem import lltype, llmemory

from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import AbstractDescr, BoxInt, LoopToken,\
     BoxFloat

def test_basic_parse():
    x = """
    [i0, i1]
    # a comment
    i2 = int_add(i0, i1)
    i3 = int_sub(i2, 3) # another comment
    finish() # (tricky)
    """
    loop = parse(x)
    assert len(loop.operations) == 3
    assert [op.opnum for op in loop.operations] == [rop.INT_ADD, rop.INT_SUB,
                                                    rop.FINISH]
    assert len(loop.inputargs) == 2
    assert loop.operations[-1].descr

def test_const_ptr_subops():
    x = """
    [p0]
    guard_class(p0, ConstClass(vtable)) []
    """
    S = lltype.Struct('S')
    vtable = lltype.nullptr(S)
    loop = parse(x, None, locals())
    assert len(loop.operations) == 1
    assert loop.operations[0].descr
    assert loop.operations[0].fail_args == []

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
    guard_value(i0, 3) []
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
    
def test_getvar_const_ptr():
    x = '''
    []
    call(ConstPtr(func_ptr))
    '''
    TP = lltype.GcArray(lltype.Signed)
    NULL = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(TP))
    loop = parse(x, None, {'func_ptr' : NULL})
    assert loop.operations[0].args[0].value == NULL

def test_jump_target():
    x = '''
    []
    jump()
    '''
    loop = parse(x)
    assert loop.operations[0].descr is loop.token

def test_jump_target_other():
    looptoken = LoopToken()
    x = '''
    []
    jump(descr=looptoken)
    '''
    loop = parse(x, namespace=locals())
    assert loop.operations[0].descr is looptoken

def test_floats():
    x = '''
    [f0]
    f1 = float_add(f0, 3.5)
    '''
    loop = parse(x)
    assert isinstance(loop.operations[0].args[0], BoxFloat)
    
def test_debug_merge_point():
    x = '''
    []
    debug_merge_point("info")
    debug_merge_point('info')
    debug_merge_point('<some ('other,')> info')
    debug_merge_point('(stuff) #1')
    '''
    loop = parse(x)
    assert loop.operations[0].args[0]._get_str() == 'info'
    assert loop.operations[1].args[0]._get_str() == 'info'
    assert loop.operations[2].args[0]._get_str() == "<some ('other,')> info"
    assert loop.operations[3].args[0]._get_str() == "(stuff) #1"
    

def test_descr_with_obj_print():
    x = '''
    [p0]
    setfield_gc(p0, 1, descr=<SomeDescr>)
    '''
    loop = parse(x)
    # assert did not explode

example_loop_log = '''\
# bridge out of Guard12, 6 ops
[i0, i1, i2]
i4 = int_add(i0, 2)
i6 = int_sub(i1, 1)
i8 = int_gt(i6, 3)
guard_true(i8, descr=<Guard15>) [i4, i6]
debug_merge_point('(no jitdriver.get_printable_location!)')
jump(i6, i4, descr=<Loop0>)
'''

def test_parse_no_namespace():
    loop = parse(example_loop_log, no_namespace=True)
