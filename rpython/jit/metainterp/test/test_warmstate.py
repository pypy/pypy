from rpython.rtyper.test.test_llinterp import interpret
from rpython.rtyper.lltypesystem import lltype, llmemory, rstr, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.metainterp.warmstate import wrap, unwrap, specialize_value
from rpython.jit.metainterp.warmstate import equal_whatever, hash_whatever
from rpython.jit.metainterp.warmstate import WarmEnterState
from rpython.jit.metainterp.resoperation import InputArgInt, InputArgRef,\
     InputArgFloat
from rpython.jit.metainterp.history import ConstInt, ConstFloat, ConstPtr,\
     IntFrontendOp, FloatFrontendOp, RefFrontendOp
from rpython.jit.metainterp.counter import DeterministicJitCounter
from rpython.jit.codewriter import longlong
from rpython.rlib.rarithmetic import r_singlefloat

def boxfloat(x):
    return InputArgFloat(longlong.getfloatstorage(x))

def constfloat(x):
    return ConstFloat(longlong.getfloatstorage(x))


def test_unwrap():
    S = lltype.GcStruct('S')
    RS = lltype.Struct('S')
    p = lltype.malloc(S)
    po = lltype.cast_opaque_ptr(llmemory.GCREF, p)
    assert unwrap(lltype.Void, InputArgInt(42)) is None
    assert unwrap(lltype.Signed, InputArgInt(42)) == 42
    assert unwrap(lltype.Char, InputArgInt(42)) == chr(42)
    assert unwrap(lltype.Float, boxfloat(42.5)) == 42.5
    assert unwrap(lltype.Ptr(S), InputArgRef(po)) == p
    assert unwrap(lltype.Ptr(RS), InputArgInt(0)) == lltype.nullptr(RS)

def test_wrap():
    def InputArgInt(a):
        i = IntFrontendOp(0, a)
        return i

    def InputArgFloat(a):
        i = FloatFrontendOp(0, a)
        return i

    def InputArgRef(a):
        i = RefFrontendOp(0, a)
        return i

    def boxfloat(x):
        return InputArgFloat(longlong.getfloatstorage(x))

    def _is(box1, box2):
        return (box1.__class__ == box2.__class__ and
                box1.getvalue() == box2.getvalue())
    p = lltype.malloc(lltype.GcStruct('S'))
    po = lltype.cast_opaque_ptr(llmemory.GCREF, p)
    assert _is(wrap(None, 42, 0), InputArgInt(42))
    assert _is(wrap(None, 42.5, 0), boxfloat(42.5))
    assert _is(wrap(None, p, 0), InputArgRef(po))
    assert _is(wrap(None, 42, -1), ConstInt(42))
    assert _is(wrap(None, 42.5, -1), constfloat(42.5))
    assert _is(wrap(None, p, -1), ConstPtr(po))
    if longlong.supports_longlong:
        import sys
        from rpython.rlib.rarithmetic import r_longlong, r_ulonglong
        value = r_longlong(-sys.maxint*17)
        assert _is(wrap(None, value, 0), InputArgFloat(value))
        assert _is(wrap(None, value, -1), ConstFloat(value))
        value_unsigned = r_ulonglong(-sys.maxint*17)
        assert _is(wrap(None, value_unsigned, 0), InputArgFloat(value))
    sfval = r_singlefloat(42.5)
    ival = longlong.singlefloat2int(sfval)
    assert _is(wrap(None, sfval, 0), InputArgInt(ival))
    assert _is(wrap(None, sfval, -1), ConstInt(ival))

def test_specialize_value():
    assert specialize_value(lltype.Char, 0x41) == '\x41'
    if longlong.supports_longlong:
        import sys
        value = longlong.r_float_storage(sys.maxint*17)
        assert specialize_value(lltype.SignedLongLong, value) == sys.maxint*17
    sfval = r_singlefloat(42.5)
    ival = longlong.singlefloat2int(sfval)
    assert specialize_value(rffi.FLOAT, ival) == sfval

def test_hash_equal_whatever_lltype():
    s1 = rstr.mallocstr(2)
    s2 = rstr.mallocstr(2)
    s1.chars[0] = 'x'; s1.chars[1] = 'y'
    s2.chars[0] = 'x'; s2.chars[1] = 'y'
    def fn(x):
        assert hash_whatever(lltype.typeOf(x), x) == 42
        assert (hash_whatever(lltype.typeOf(s1), s1) ==
                hash_whatever(lltype.typeOf(s2), s2))
        assert equal_whatever(lltype.typeOf(s1), s1, s2)
    fn(42)
    interpret(fn, [42])


def test_make_unwrap_greenkey():
    class FakeJitDriverSD:
        _green_args_spec = [lltype.Signed, lltype.Float]
    state = WarmEnterState(None, FakeJitDriverSD())
    unwrap_greenkey = state.make_unwrap_greenkey()
    greenargs = unwrap_greenkey([ConstInt(42), constfloat(42.5)])
    assert greenargs == (42, 42.5)
    assert type(greenargs[0]) is int

class FakeWarmRunnerDesc:
    cpu = None
    memory_manager = None
    rtyper = None
    jitcounter = DeterministicJitCounter()
    class metainterp_sd:
        pass

def test_make_jitdriver_callbacks_1():
    class FakeJitDriverSD:
        jitdriver = None
        _green_args_spec = [lltype.Signed, lltype.Float]
        _get_printable_location_ptr = None
        _confirm_enter_jit_ptr = None
        _get_unique_id_ptr = None
        _can_never_inline_ptr = None
        _should_unroll_one_iteration_ptr = None
        red_args_types = []
    class FakeCell:
        dont_trace_here = False
    state = WarmEnterState(FakeWarmRunnerDesc(), FakeJitDriverSD())
    def jit_getter(build, *args):
        return FakeCell()
    state.jit_getter = jit_getter
    state.make_jitdriver_callbacks()
    res = state.get_location_str([ConstInt(5), constfloat(42.5)])
    assert res == '(<unknown jitdriver>: no get_printable_location)'

def test_make_jitdriver_callbacks_3():
    def get_location(x, y):
        assert x == 5
        assert y == 42.5
        return "hi there"    # abuse the return type, but nobody checks it
    GET_LOCATION = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Float],
                                              lltype.Ptr(rstr.STR)))
    class FakeJitDriverSD:
        jitdriver = None
        _green_args_spec = [lltype.Signed, lltype.Float]
        _get_printable_location_ptr = llhelper(GET_LOCATION, get_location)
        _confirm_enter_jit_ptr = None
        _can_never_inline_ptr = None
        _get_unique_id_ptr = None
        _should_unroll_one_iteration_ptr = None
        red_args_types = []
    state = WarmEnterState(FakeWarmRunnerDesc(), FakeJitDriverSD())
    state.make_jitdriver_callbacks()
    res = state.get_location_str([ConstInt(5), constfloat(42.5)])
    assert res == "hi there"

def test_make_jitdriver_callbacks_4():
    def confirm_enter_jit(x, y, z):
        assert x == 5
        assert y == 42.5
        assert z == 3
        return True
    ENTER_JIT = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Float,
                                            lltype.Signed], lltype.Bool))
    class FakeJitDriverSD:
        jitdriver = None
        _green_args_spec = [lltype.Signed, lltype.Float]
        _get_printable_location_ptr = None
        _confirm_enter_jit_ptr = llhelper(ENTER_JIT, confirm_enter_jit)
        _can_never_inline_ptr = None
        _get_unique_id_ptr = None
        _should_unroll_one_iteration_ptr = None
        red_args_types = []

    state = WarmEnterState(FakeWarmRunnerDesc(), FakeJitDriverSD())
    state.make_jitdriver_callbacks()
    res = state.confirm_enter_jit(5, 42.5, 3)
    assert res is True

def test_make_jitdriver_callbacks_5():
    def can_never_inline(x, y):
        assert x == 5
        assert y == 42.5
        return True
    CAN_NEVER_INLINE = lltype.Ptr(lltype.FuncType(
        [lltype.Signed, lltype.Float], lltype.Bool))
    class FakeJitDriverSD:
        jitdriver = None
        _green_args_spec = [lltype.Signed, lltype.Float]
        _get_printable_location_ptr = None
        _confirm_enter_jit_ptr = None
        _get_unique_id_ptr = None
        _can_never_inline_ptr = llhelper(CAN_NEVER_INLINE, can_never_inline)
        _should_unroll_one_iteration_ptr = None
        red_args_types = []

    state = WarmEnterState(FakeWarmRunnerDesc(), FakeJitDriverSD())
    state.make_jitdriver_callbacks()
    res = state.can_never_inline(5, 42.5)
    assert res is True
