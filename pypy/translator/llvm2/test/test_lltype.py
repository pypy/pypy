import py

from pypy.rpython import lltype

from pypy.translator.llvm2.genllvm import compile_function
from pypy.translator.llvm2 import database, codewriter

py.log.setconsumer("genllvm", py.log.STDOUT)
py.log.setconsumer("genllvm database prepare", None)

P = lltype.GcStruct("s",
                    ('signed', lltype.Signed),
                    ('unsigned', lltype.Unsigned),
                    ('float', lltype.Float),
                    ('char', lltype.Char),
                    ('bool', lltype.Bool),
                    ('unichar', lltype.UniChar)
                    )

def test_struct1():
    # struct of primitives
    def simple1():
        s = lltype.malloc(P)
        return s.signed# + s.unsigned + s.float + s.char + s.bool + s.unichar
    fn = compile_function(simple1, [], embedexterns=False)
    assert fn() == 0

# def test_struct2():
#     S = lltype.Struct("s", ('v', lltype.Signed))
#     S2 = lltype.GcStruct("s2", ('a', S), ('b', S))
#     def simple2():
#         s = lltype.malloc(S2)
#         s.a.v = 6
#         s.b.v = 12
#         return s.a.v + s.b.v
#     fn = compile_function(simple2, [], embedexterns=False, view=True)
#     assert fn() == 18

# def test_simple_struct():
#     S0 = lltype.GcStruct("s0", ('a', lltype.Signed), ('b', lltype.Signed))
#     c0 = lltype.malloc(S0)
#     c0.a, c0.b = 1, 2
#     def simple_struct():
#         return c0.a + c0.b
#     f = compile_function(simple_struct, [], embedexterns=False, view=True)
#     assert f() == 3

# def test_simple_struct2():
#     S0 = lltype.GcStruct("s0", ('a', lltype.Char), ('b', lltype.Signed))
#     def build():
#         s0 = lltype.malloc(S0)
#         s0.a = "l"
#         s0.b = 2
#         return s0
#     c0 = build()
#     def simple_struct2():
#         return c0.a + c0.b
#     f = compile_function(simple_struct, [], embedexterns=False, view=True)
#     assert f() == 3

