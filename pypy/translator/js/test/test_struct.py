import py
from pypy.rpython.lltypesystem import lltype
from pypy.translator.js.test.runtest import compile_function

S = lltype.GcStruct("mystruct",
    ('myvar1', lltype.Unsigned),
    ('myvar2', lltype.Signed),
    ('myvar3', lltype.Float),
    ('myvar4', lltype.Char),
    ('myvar5', lltype.Void),
    ('myvar7', lltype.Bool),
    )
#Array
#Struct

def test_struct2():
    def struct2():
        s = lltype.malloc(S)
        return s.myvar1
    f = compile_function(struct2, [])
    assert f() == struct2()
