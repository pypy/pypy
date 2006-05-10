import py.test
from pypy.rpython.rctypes.rcarithmetic import *
from pypy.rpython.lltypesystem import lltype
from pypy.rpython import rarithmetic
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.error import TyperError
from pypy.translator.translator import TranslationContext

def specialize(func, types):
    t = TranslationContext()
    t.buildannotator().build_types(func, types)
    t.buildrtyper().specialize()
    t.checkgraphs()    

def test_signedness():
    assert rcbyte(-1) < 0
    assert rcubyte(-1) > 0

def test_promotion():
    assert type(rcbyte(1) + 1) is rcbyte
    assert type(1 + rcbyte(1)) is rcbyte
    
    assert type(rcbyte(1) + rcshort(1)) is rcshort
    assert type(rcshort(1) + rcbyte(1)) is rcshort

    assert type(rcubyte(1) + rcshort(1)) is rcushort
    assert type(rcshort(1) + rcubyte(1)) is rcushort

    
def test_typeof():
    assert lltype.typeOf(rarithmetic.r_int(0)) == lltype.Signed
    assert lltype.typeOf(rclong(0)) == lltype.Signed
    assert lltype.Signed == CLong
    assert lltype.typeOf(rarithmetic.r_uint(0)) == lltype.Unsigned
    assert lltype.typeOf(rculong(0)) == lltype.Unsigned
    assert lltype.Unsigned == CULong

    assert lltype.typeOf(rcbyte(0)) == CByte
    assert lltype.typeOf(rcshort(0)) == CShort

    assert lltype.typeOf(rcushort(0)) == CUShort

inttypes = [rcbyte, rcubyte, rcshort, rcushort, rcint, rcuint,
            rclong, rculong, rclonglong, rculonglong]

def test_annotate():
    for inttype in inttypes:
        c = inttype()
        def f():
            return c
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeInteger)
        assert s.knowntype == inttype
        assert s.unsigned == (inttype(-1) > 0)

    for inttype in inttypes:
        def f():
            return inttype(0)
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeInteger)
        assert s.knowntype == inttype
        assert s.unsigned == (inttype(-1) > 0)

    for inttype in inttypes:
        def f(x):
            return x
        a = RPythonAnnotator()
        s = a.build_types(f, [inttype])
        assert isinstance(s, annmodel.SomeInteger)
        assert s.knowntype == inttype
        assert s.unsigned == (inttype(-1) > 0)

def test_specialize():
    for inttype in inttypes:
        c = inttype()
        def f():
            return c
        res = interpret(f, [])
        assert res == f()
        assert lltype.typeOf(res) == lltype.build_number(None, inttype)

    for inttype in inttypes:
        def f():
            return inttype(0)
        res = interpret(f, [])
        assert res == f()
        assert lltype.typeOf(res) == lltype.build_number(None, inttype)        

    for inttype in inttypes:
        def f(x):
            return x
        res = interpret(f, [inttype(0)])
        assert res == f(inttype(0))
        assert lltype.typeOf(res) == lltype.build_number(None, inttype)

        
def test_unsupported_op():
    def f(x, y):
        return x + y

    py.test.raises(TyperError, specialize, f, [rcbyte, rcbyte])
    
