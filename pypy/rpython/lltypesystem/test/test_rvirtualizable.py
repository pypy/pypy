from pypy.rpython.lltypesystem import lltype, rclass
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr

class V(object):
    _virtualizable_ = True

    def __init__(self, v):
        self.v = v

def test_simple():
    def f(v):
        vinst = V(v)
        return vinst, vinst.v
    res = interpret(f, [42])
    assert res.item1 == 42
    res = lltype.normalizeptr(res.item0)
    assert res.inst_v == 42
    assert not res.vable_access
    LLV = lltype.typeOf(res)
    ACCESS = lltype.typeOf(res.vable_access).TO
    assert ACCESS.get_inst_v == lltype.Ptr(lltype.FuncType([LLV],
                                                           lltype.Signed))
    assert ACCESS.set_inst_v == lltype.Ptr(lltype.FuncType([LLV, lltype.Signed],
                                                           lltype.Void))    

def test_accessors():

    G = lltype.FuncType([rclass.OBJECTPTR], lltype.Void)

    witness = []
    
    def getv(vinst):
        value = vinst.inst_v
        witness.append(value)
        return value

    def g(vobj):
        vobj = lltype.normalizeptr(vobj)
        LLV = lltype.typeOf(vobj).TO
        ACCESS = LLV.vable_access.TO
        access = lltype.malloc(ACCESS, immortal=True)
        access.get_inst_v = lltype.functionptr(ACCESS.get_inst_v.TO,
                                               'getv', _callable=getv)
        vobj.vable_access = access
        
    gptr = lltype.functionptr(G, 'g', _callable=g)
    
    def f(v):
        vinst = V(v)
        vobj = cast_instance_to_base_ptr(vinst)
        gptr(vobj)
        x = vinst.v
        return x
    res = interpret(f, [42])
    assert res == 42

    assert witness == [42]
