import py
from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.jit.metainterp.support import decode_builtin_call

def newconst(x):
    return Constant(x, lltype.typeOf(x))

def voidconst(x):
    return Constant(x, lltype.Void)

# ____________________________________________________________

def test_decode_builtin_call_nomethod():
    def myfoobar(i, marker, c):
        assert marker == 'mymarker'
        return i * ord(c)
    myfoobar.oopspec = 'foobar(2, c, i)'
    TYPE = lltype.FuncType([lltype.Signed, lltype.Void, lltype.Char],
                           lltype.Signed)
    fnobj = lltype.functionptr(TYPE, 'foobar', _callable=myfoobar)
    vi = Variable('i')
    vi.concretetype = lltype.Signed
    vc = Variable('c')
    vc.concretetype = lltype.Char
    v_result = Variable('result')
    v_result.concretetype = lltype.Signed
    op = SpaceOperation('direct_call', [newconst(fnobj),
                                        vi,
                                        voidconst('mymarker'),
                                        vc],
                        v_result)
    oopspec, opargs = decode_builtin_call(op)
    assert oopspec == 'foobar'
    assert opargs == [newconst(2), vc, vi]
    #impl = runner.get_oopspec_impl('foobar', lltype.Signed)
    #assert impl(2, 'A', 5) == 5 * ord('A')

def test_decode_builtin_call_method():
    A = lltype.GcArray(lltype.Signed)
    def myfoobar(a, i, marker, c):
        assert marker == 'mymarker'
        return a[i] * ord(c)
    myfoobar.oopspec = 'spam.foobar(a, 2, c, i)'
    TYPE = lltype.FuncType([lltype.Ptr(A), lltype.Signed,
                            lltype.Void, lltype.Char],
                           lltype.Signed)
    fnobj = lltype.functionptr(TYPE, 'foobar', _callable=myfoobar)
    vi = Variable('i')
    vi.concretetype = lltype.Signed
    vc = Variable('c')
    vc.concretetype = lltype.Char
    v_result = Variable('result')
    v_result.concretetype = lltype.Signed
    myarray = lltype.malloc(A, 10)
    myarray[5] = 42
    op = SpaceOperation('direct_call', [newconst(fnobj),
                                        newconst(myarray),
                                        vi,
                                        voidconst('mymarker'),
                                        vc],
                        v_result)
    oopspec, opargs = decode_builtin_call(op)
    assert oopspec == 'spam.foobar'
    assert opargs == [newconst(myarray), newconst(2), vc, vi]
    #impl = runner.get_oopspec_impl('spam.foobar', lltype.Ptr(A))
    #assert impl(myarray, 2, 'A', 5) == 42 * ord('A')
