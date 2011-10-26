from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rffi
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.metainterp.warmstate import wrap, unwrap, specialize_value
from pypy.jit.metainterp.warmstate import equal_whatever, hash_whatever
from pypy.jit.metainterp.warmstate import WarmEnterState, JitCell
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr
from pypy.jit.metainterp.history import ConstInt, ConstFloat, ConstPtr
from pypy.jit.codewriter import longlong
from pypy.rlib.rarithmetic import r_singlefloat

def boxfloat(x):
    return BoxFloat(longlong.getfloatstorage(x))

def constfloat(x):
    return ConstFloat(longlong.getfloatstorage(x))


def test_unwrap():
    S = lltype.GcStruct('S')
    RS = lltype.Struct('S')
    p = lltype.malloc(S)
    po = lltype.cast_opaque_ptr(llmemory.GCREF, p)
    assert unwrap(lltype.Void, BoxInt(42)) is None
    assert unwrap(lltype.Signed, BoxInt(42)) == 42
    assert unwrap(lltype.Char, BoxInt(42)) == chr(42)
    assert unwrap(lltype.Float, boxfloat(42.5)) == 42.5
    assert unwrap(lltype.Ptr(S), BoxPtr(po)) == p
    assert unwrap(lltype.Ptr(RS), BoxInt(0)) == lltype.nullptr(RS)

def test_wrap():
    def _is(box1, box2):
        return (box1.__class__ == box2.__class__ and
                box1.value == box2.value)
    p = lltype.malloc(lltype.GcStruct('S'))
    po = lltype.cast_opaque_ptr(llmemory.GCREF, p)
    assert _is(wrap(None, 42), BoxInt(42))
    assert _is(wrap(None, 42.5), boxfloat(42.5))
    assert _is(wrap(None, p), BoxPtr(po))
    assert _is(wrap(None, 42, in_const_box=True), ConstInt(42))
    assert _is(wrap(None, 42.5, in_const_box=True), constfloat(42.5))
    assert _is(wrap(None, p, in_const_box=True), ConstPtr(po))
    if longlong.supports_longlong:
        import sys
        from pypy.rlib.rarithmetic import r_longlong, r_ulonglong
        value = r_longlong(-sys.maxint*17)
        assert _is(wrap(None, value), BoxFloat(value))
        assert _is(wrap(None, value, in_const_box=True), ConstFloat(value))
        value_unsigned = r_ulonglong(-sys.maxint*17)
        assert _is(wrap(None, value_unsigned), BoxFloat(value))
    sfval = r_singlefloat(42.5)
    ival = longlong.singlefloat2int(sfval)
    assert _is(wrap(None, sfval), BoxInt(ival))
    assert _is(wrap(None, sfval, in_const_box=True), ConstInt(ival))

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
    interpret(fn, [42], type_system='lltype')

def test_hash_equal_whatever_ootype():
    def fn(c):
        s1 = ootype.oostring("xy", -1)
        s2 = ootype.oostring("x" + chr(c), -1)
        assert (hash_whatever(ootype.typeOf(s1), s1) ==
                hash_whatever(ootype.typeOf(s2), s2))
        assert equal_whatever(ootype.typeOf(s1), s1, s2)
    fn(ord('y'))
    interpret(fn, [ord('y')], type_system='ootype')


def test_make_jitcell_getter_default():
    class FakeJitDriverSD:
        _green_args_spec = [lltype.Signed, lltype.Float]
    state = WarmEnterState(None, FakeJitDriverSD())
    get_jitcell = state._make_jitcell_getter_default()
    cell1 = get_jitcell(True, 42, 42.5)
    assert isinstance(cell1, JitCell)
    cell2 = get_jitcell(True, 42, 42.5)
    assert cell1 is cell2
    cell3 = get_jitcell(True, 41, 42.5)
    assert get_jitcell(False, 42, 0.25) is None
    cell4 = get_jitcell(True, 42, 0.25)
    assert get_jitcell(False, 42, 0.25) is cell4
    assert cell1 is not cell3 is not cell4 is not cell1

def test_make_jitcell_getter():
    class FakeJitDriverSD:
        _green_args_spec = [lltype.Float]
        _get_jitcell_at_ptr = None
    state = WarmEnterState(None, FakeJitDriverSD())
    get_jitcell = state.make_jitcell_getter()
    cell1 = get_jitcell(True, 1.75)
    cell2 = get_jitcell(True, 1.75)
    assert cell1 is cell2
    assert get_jitcell is state.make_jitcell_getter()

def test_make_jitcell_getter_custom():
    from pypy.rpython.typesystem import LowLevelTypeSystem
    class FakeRTyper:
        type_system = LowLevelTypeSystem.instance
    celldict = {}
    def getter(x, y):
        return celldict.get((x, y))
    def setter(newcell, x, y):
        newcell.x = x
        newcell.y = y
        celldict[x, y] = newcell
    GETTER = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Float],
                                        llmemory.GCREF))
    SETTER = lltype.Ptr(lltype.FuncType([llmemory.GCREF, lltype.Signed,
                                         lltype.Float], lltype.Void))
    class FakeWarmRunnerDesc:
        rtyper = FakeRTyper()
        cpu = None
        memory_manager = None
    class FakeJitDriverSD:
        _get_jitcell_at_ptr = llhelper(GETTER, getter)
        _set_jitcell_at_ptr = llhelper(SETTER, setter)
    #
    state = WarmEnterState(FakeWarmRunnerDesc(), FakeJitDriverSD())
    get_jitcell = state._make_jitcell_getter_custom()
    cell1 = get_jitcell(True, 5, 42.5)
    assert isinstance(cell1, JitCell)
    assert cell1.x == 5
    assert cell1.y == 42.5
    cell2 = get_jitcell(True, 5, 42.5)
    assert cell2 is cell1
    cell3 = get_jitcell(True, 41, 42.5)
    assert get_jitcell(False, 42, 0.25) is None
    cell4 = get_jitcell(True, 42, 0.25)
    assert get_jitcell(False, 42, 0.25) is cell4
    assert cell1 is not cell3 is not cell4 is not cell1

def test_make_unwrap_greenkey():
    class FakeJitDriverSD:
        _green_args_spec = [lltype.Signed, lltype.Float]
    state = WarmEnterState(None, FakeJitDriverSD())
    unwrap_greenkey = state.make_unwrap_greenkey()
    greenargs = unwrap_greenkey([ConstInt(42), constfloat(42.5)])
    assert greenargs == (42, 42.5)
    assert type(greenargs[0]) is int

def test_attach_unoptimized_bridge_from_interp():
    class FakeJitDriverSD:
        _green_args_spec = [lltype.Signed, lltype.Float]
        _get_jitcell_at_ptr = None
    state = WarmEnterState(None, FakeJitDriverSD())
    get_jitcell = state.make_jitcell_getter()
    class FakeLoopToken(object):
        pass
    looptoken = FakeLoopToken()
    state.attach_unoptimized_bridge_from_interp([ConstInt(5),
                                                 constfloat(2.25)],
                                                looptoken)
    cell1 = get_jitcell(True, 5, 2.25)
    assert cell1.counter < 0
    assert cell1.get_entry_loop_token() is looptoken

def test_make_jitdriver_callbacks_1():
    class FakeWarmRunnerDesc:
        cpu = None
        memory_manager = None
    class FakeJitDriverSD:
        jitdriver = None
        _green_args_spec = [lltype.Signed, lltype.Float]
        _get_printable_location_ptr = None
        _confirm_enter_jit_ptr = None
        _can_never_inline_ptr = None
        _should_unroll_one_iteration_ptr = None
    class FakeCell:
        dont_trace_here = False
    state = WarmEnterState(FakeWarmRunnerDesc(), FakeJitDriverSD())
    def jit_getter(build, *args):
        return FakeCell()
    state.jit_getter = jit_getter
    state.make_jitdriver_callbacks()
    res = state.get_location_str([ConstInt(5), constfloat(42.5)])
    assert res == '(no jitdriver.get_printable_location!)'

def test_make_jitdriver_callbacks_3():
    def get_location(x, y):
        assert x == 5
        assert y == 42.5
        return "hi there"    # abuse the return type, but nobody checks it
    GET_LOCATION = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Float],
                                              lltype.Ptr(rstr.STR)))
    class FakeWarmRunnerDesc:
        rtyper = None
        cpu = None
        memory_manager = None
    class FakeJitDriverSD:
        jitdriver = None
        _green_args_spec = [lltype.Signed, lltype.Float]
        _get_printable_location_ptr = llhelper(GET_LOCATION, get_location)
        _confirm_enter_jit_ptr = None
        _can_never_inline_ptr = None
        _get_jitcell_at_ptr = None
        _should_unroll_one_iteration_ptr = None
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
    class FakeWarmRunnerDesc:
        rtyper = None
        cpu = None
        memory_manager = None
    class FakeJitDriverSD:
        jitdriver = None
        _green_args_spec = [lltype.Signed, lltype.Float]
        _get_printable_location_ptr = None
        _confirm_enter_jit_ptr = llhelper(ENTER_JIT, confirm_enter_jit)
        _can_never_inline_ptr = None
        _get_jitcell_at_ptr = None
        _should_unroll_one_iteration_ptr = None

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
    class FakeWarmRunnerDesc:
        rtyper = None
        cpu = None
        memory_manager = None
    class FakeJitDriverSD:
        jitdriver = None
        _green_args_spec = [lltype.Signed, lltype.Float]
        _get_printable_location_ptr = None
        _confirm_enter_jit_ptr = None
        _can_never_inline_ptr = llhelper(CAN_NEVER_INLINE, can_never_inline)
        _get_jitcell_at_ptr = None
        _should_unroll_one_iteration_ptr = None

    state = WarmEnterState(FakeWarmRunnerDesc(), FakeJitDriverSD())
    state.make_jitdriver_callbacks()
    res = state.can_never_inline(5, 42.5)
    assert res is True
