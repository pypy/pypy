from rpython.flowspace.model import Variable, const
from rpython.flowspace.expression import V_Type

def test_type():
    v1, v2 = Variable(), Variable()
    assert V_Type(v1) == V_Type(v1)
    assert V_Type(v1) != V_Type(v2)
    assert hash(V_Type(v1)) == hash(V_Type(v1))
    assert hash(V_Type(v1)) != hash(V_Type(v2))

def test_type_replace():
    v1, v2 = Variable(), Variable()
    assert V_Type(v1).replace({v1: v2}) == V_Type(v2)
    assert V_Type(const(1)).replace({v1: v2}) == V_Type(const(1))
    assert V_Type(v1).replace({v2: v1}) == V_Type(v1)
