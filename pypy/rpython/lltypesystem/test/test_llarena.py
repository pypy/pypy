import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.llmemory import cast_adr_to_ptr
from pypy.rpython.lltypesystem.llarena import arena_malloc, arena_reset
from pypy.rpython.lltypesystem.llarena import arena_reserve
from pypy.rpython.lltypesystem.llarena import ArenaError

def test_arena():
    S = lltype.Struct('S', ('x',lltype.Signed))
    SPTR = lltype.Ptr(S)
    ssize = llmemory.raw_malloc_usage(llmemory.sizeof(S))
    myarenasize = 2*ssize+1
    a = arena_malloc(myarenasize, False)
    assert a != llmemory.NULL
    assert a + 3 != llmemory.NULL

    arena_reserve(a, llmemory.sizeof(S))
    s1_ptr1 = cast_adr_to_ptr(a, SPTR)
    s1_ptr1.x = 1
    s1_ptr2 = cast_adr_to_ptr(a, SPTR)
    assert s1_ptr2.x == 1
    assert s1_ptr1 == s1_ptr2

    arena_reserve(a + ssize + 1, llmemory.sizeof(S))
    s2_ptr1 = cast_adr_to_ptr(a + ssize + 1, SPTR)
    py.test.raises(lltype.UninitializedMemoryAccess, 's2_ptr1.x')
    s2_ptr1.x = 2
    s2_ptr2 = cast_adr_to_ptr(a + ssize + 1, SPTR)
    assert s2_ptr2.x == 2
    assert s2_ptr1 == s2_ptr2
    assert s1_ptr1 != s2_ptr1
    assert not (s2_ptr2 == s1_ptr2)
    assert s1_ptr1 == cast_adr_to_ptr(a, SPTR)

    S2 = lltype.Struct('S2', ('y',lltype.Char))
    S2PTR = lltype.Ptr(S2)
    py.test.raises(lltype.InvalidCast, cast_adr_to_ptr, a, S2PTR)
    py.test.raises(ArenaError, cast_adr_to_ptr, a+1, SPTR)
    py.test.raises(ArenaError, cast_adr_to_ptr, a+ssize, SPTR)
    py.test.raises(ArenaError, cast_adr_to_ptr, a+2*ssize, SPTR)
    py.test.raises(ArenaError, cast_adr_to_ptr, a+2*ssize+1, SPTR)
    py.test.raises(ArenaError, arena_reserve, a+1, llmemory.sizeof(S))
    py.test.raises(ArenaError, arena_reserve, a+ssize, llmemory.sizeof(S))
    py.test.raises(ArenaError, arena_reserve, a+2*ssize, llmemory.sizeof(S))
    py.test.raises(ArenaError, arena_reserve, a+2*ssize+1, llmemory.sizeof(S))

    arena_reset(a, myarenasize, True)
    py.test.raises(ArenaError, cast_adr_to_ptr, a, SPTR)
    arena_reserve(a, llmemory.sizeof(S))
    s1_ptr1 = cast_adr_to_ptr(a, SPTR)
    assert s1_ptr1.x == 0
    s1_ptr1.x = 5

    arena_reserve(a + ssize, llmemory.sizeof(S2))
    s2_ptr1 = cast_adr_to_ptr(a + ssize, S2PTR)
    assert s2_ptr1.y == '\x00'
    s2_ptr1.y = 'X'

    assert cast_adr_to_ptr(a + 0, SPTR).x == 5
    assert cast_adr_to_ptr((a + ssize + 1) - 1, S2PTR).y == 'X'

    assert (a + 4) - (a + 1) == 3


def lt(x, y):
    if x < y:
        assert     (x < y)  and     (y > x)
        assert     (x <= y) and     (y >= x)
        assert not (x == y) and not (y == x)
        assert     (x != y) and     (y != x)
        assert not (x > y)  and not (y < x)
        assert not (x >= y) and not (y <= x)
        return True
    else:
        assert (x >= y) and (y <= x)
        assert (x == y) == (not (x != y)) == (y == x) == (not (y != x))
        assert (x > y) == (not (x == y)) == (y < x)
        return False

def eq(x, y):
    if x == y:
        assert not (x != y) and not (y != x)
        assert not (x < y)  and not (y > x)
        assert not (x > y)  and not (y < x)
        assert     (x <= y) and     (y >= x)
        assert     (x >= y) and     (y <= x)
        return True
    else:
        assert (x != y) and (y != x)
        assert ((x < y) == (x <= y) == (not (x > y)) == (not (x >= y)) ==
                (y > x) == (y >= x) == (not (y < x)) == (not (y <= x)))
        return False


def test_address_order():
    a = arena_malloc(20, False)
    assert eq(a, a)
    assert lt(a, a+1)
    assert lt(a+5, a+20)

    b = arena_malloc(20, False)
    if a > b:
        a, b = b, a
    assert lt(a, b)
    assert lt(a+19, b)
    assert lt(a, b+19)


def test_look_inside_object():
    S = lltype.Struct('S', ('x',lltype.Signed))
    SPTR = lltype.Ptr(S)
    a = arena_malloc(50, False)
    b = a + 4
    arena_reserve(b, llmemory.sizeof(S))
    (b + llmemory.offsetof(S, 'x')).signed[0] = 123
    assert llmemory.cast_adr_to_ptr(b, SPTR).x == 123
    llmemory.cast_adr_to_ptr(b, SPTR).x += 1
    assert (b + llmemory.offsetof(S, 'x')).signed[0] == 124
