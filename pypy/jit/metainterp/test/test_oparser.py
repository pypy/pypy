
from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.metainterp.resoperation import rop

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
