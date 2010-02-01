from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.metainterp.warmstate import wrap, unwrap
from pypy.jit.metainterp.warmstate import equal_whatever, hash_whatever
from pypy.jit.metainterp.warmstate import WarmEnterState
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr
from pypy.jit.metainterp.history import ConstInt, ConstFloat, ConstPtr
from pypy.rlib.jit import BaseJitCell


def test_unwrap():
    S = lltype.GcStruct('S')
    p = lltype.malloc(S)
    po = lltype.cast_opaque_ptr(llmemory.GCREF, p)
    assert unwrap(lltype.Void, BoxInt(42)) is None
    assert unwrap(lltype.Signed, BoxInt(42)) == 42
    assert unwrap(lltype.Char, BoxInt(42)) == chr(42)
    assert unwrap(lltype.Float, BoxFloat(42.5)) == 42.5
    assert unwrap(lltype.Ptr(S), BoxPtr(po)) == p

def test_wrap():
    def _is(box1, box2):
        return (box1.__class__ == box2.__class__ and
                box1.value == box2.value)
    p = lltype.malloc(lltype.GcStruct('S'))
    po = lltype.cast_opaque_ptr(llmemory.GCREF, p)
    assert _is(wrap(None, 42), BoxInt(42))
    assert _is(wrap(None, 42.5), BoxFloat(42.5))
    assert _is(wrap(None, p), BoxPtr(po))
    assert _is(wrap(None, 42, in_const_box=True), ConstInt(42))
    assert _is(wrap(None, 42.5, in_const_box=True), ConstFloat(42.5))
    assert _is(wrap(None, p, in_const_box=True), ConstPtr(po))

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
    class FakeWarmRunnerDesc:
        green_args_spec = [lltype.Signed, lltype.Float]
    class FakeJitCell(BaseJitCell):
        pass
    state = WarmEnterState(FakeWarmRunnerDesc())
    get_jitcell = state._make_jitcell_getter_default(FakeJitCell)
    cell1 = get_jitcell(42, 42.5)
    assert isinstance(cell1, FakeJitCell)
    cell2 = get_jitcell(42, 42.5)
    assert cell1 is cell2
    cell3 = get_jitcell(41, 42.5)
    cell4 = get_jitcell(42, 0.25)
    assert cell1 is not cell3 is not cell4 is not cell1

def test_make_jitcell_getter():
    class FakeWarmRunnerDesc:
        green_args_spec = [lltype.Float]
        get_jitcell_at_ptr = None
    state = WarmEnterState(FakeWarmRunnerDesc())
    get_jitcell = state.make_jitcell_getter()
    cell1 = get_jitcell(1.75)
    cell2 = get_jitcell(1.75)
    assert cell1 is cell2
    assert get_jitcell is state.make_jitcell_getter()

def test_make_jitcell_getter_custom():
    from pypy.rpython.typesystem import LowLevelTypeSystem
    class FakeRTyper:
        type_system = LowLevelTypeSystem.instance
    class FakeJitCell(BaseJitCell):
        pass
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
        get_jitcell_at_ptr = llhelper(GETTER, getter)
        set_jitcell_at_ptr = llhelper(SETTER, setter)
    #
    state = WarmEnterState(FakeWarmRunnerDesc())
    get_jitcell = state._make_jitcell_getter_custom(FakeJitCell)
    cell1 = get_jitcell(5, 42.5)
    assert isinstance(cell1, FakeJitCell)
    assert cell1.x == 5
    assert cell1.y == 42.5
    cell2 = get_jitcell(5, 42.5)
    assert cell2 is cell1
    cell3 = get_jitcell(41, 42.5)
    cell4 = get_jitcell(42, 0.25)
    assert cell1 is not cell3 is not cell4 is not cell1

def test_make_set_future_values():
    future_values = {}
    class FakeCPU:
        def set_future_value_int(self, j, value):
            future_values[j] = "int", value
        def set_future_value_float(self, j, value):
            future_values[j] = "float", value
    class FakeWarmRunnerDesc:
        cpu = FakeCPU()
        red_args_types = ["int", "float"]
        class metainterp_sd:
            virtualizable_info = None
    #
    state = WarmEnterState(FakeWarmRunnerDesc())
    set_future_values = state.make_set_future_values()
    set_future_values(5, 42.5)
    assert future_values == {
        0: ("int", 5),
        1: ("float", 42.5),
    }
    assert set_future_values is state.make_set_future_values()

def test_make_unwrap_greenkey():
    class FakeWarmRunnerDesc:
        green_args_spec = [lltype.Signed, lltype.Float]
    state = WarmEnterState(FakeWarmRunnerDesc())
    unwrap_greenkey = state.make_unwrap_greenkey()
    greenargs = unwrap_greenkey([ConstInt(42), ConstFloat(42.5)])
    assert greenargs == (42, 42.5)
    assert type(greenargs[0]) is int

def test_attach_unoptimized_bridge_from_interp():
    class FakeWarmRunnerDesc:
        green_args_spec = [lltype.Signed, lltype.Float]
        get_jitcell_at_ptr = None
    state = WarmEnterState(FakeWarmRunnerDesc())
    get_jitcell = state.make_jitcell_getter()
    state.attach_unoptimized_bridge_from_interp([ConstInt(5),
                                                 ConstFloat(2.25)],
                                                "entry loop token")
    cell1 = get_jitcell(5, 2.25)
    assert cell1.counter < 0
    assert cell1.entry_loop_token == "entry loop token"

def test_make_jitdriver_callbacks_1():
    class FakeWarmRunnerDesc:
        can_inline_ptr = None
        get_printable_location_ptr = None
        confirm_enter_jit_ptr = None
        green_args_spec = [lltype.Signed, lltype.Float]
    class FakeCell:
        dont_trace_here = False
    state = WarmEnterState(FakeWarmRunnerDesc())
    def jit_getter(*args):
        return FakeCell()
    state.jit_getter = jit_getter
    state.make_jitdriver_callbacks()
    res = state.can_inline_callable([ConstInt(5), ConstFloat(42.5)])
    assert res is True
    res = state.get_location_str([ConstInt(5), ConstFloat(42.5)])
    assert res == '(no jitdriver.get_printable_location!)'

def test_make_jitdriver_callbacks_2():
    def can_inline(x, y):
        assert x == 5
        assert y == 42.5
        return False
    CAN_INLINE = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Float],
                                            lltype.Bool))
    class FakeCell:
        dont_trace_here = False
    class FakeWarmRunnerDesc:
        rtyper = None
        green_args_spec = [lltype.Signed, lltype.Float]
        can_inline_ptr = llhelper(CAN_INLINE, can_inline)
        get_printable_location_ptr = None
        confirm_enter_jit_ptr = None
    state = WarmEnterState(FakeWarmRunnerDesc())
    def jit_getter(*args):
        return FakeCell()
    state.jit_getter = jit_getter
    state.make_jitdriver_callbacks()
    res = state.can_inline_callable([ConstInt(5), ConstFloat(42.5)])
    assert res is False

def test_make_jitdriver_callbacks_3():
    def get_location(x, y):
        assert x == 5
        assert y == 42.5
        return "hi there"    # abuse the return type, but nobody checks it
    GET_LOCATION = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Float],
                                              lltype.Ptr(rstr.STR)))
    class FakeWarmRunnerDesc:
        rtyper = None
        green_args_spec = [lltype.Signed, lltype.Float]
        can_inline_ptr = None
        get_printable_location_ptr = llhelper(GET_LOCATION, get_location)
        confirm_enter_jit_ptr = None
        get_jitcell_at_ptr = None
    state = WarmEnterState(FakeWarmRunnerDesc())
    state.make_jitdriver_callbacks()
    res = state.get_location_str([ConstInt(5), ConstFloat(42.5)])
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
        green_args_spec = [lltype.Signed, lltype.Float]
        can_inline_ptr = None
        get_printable_location_ptr = None
        confirm_enter_jit_ptr = llhelper(ENTER_JIT, confirm_enter_jit)
        get_jitcell_at_ptr = None

    state = WarmEnterState(FakeWarmRunnerDesc())
    state.make_jitdriver_callbacks()
    res = state.confirm_enter_jit(5, 42.5, 3)
    assert res is True
