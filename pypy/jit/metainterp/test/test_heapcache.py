from pypy.jit.metainterp.heapcache import HeapCache
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import ConstInt

box1 = object()
box2 = object()
box3 = object()
box4 = object()
lengthbox1 = object()
lengthbox2 = object()
descr1 = object()
descr2 = object()
descr3 = object()

index1 = ConstInt(0)
index2 = ConstInt(1)


class FakeEffektinfo(object):
    EF_ELIDABLE_CANNOT_RAISE           = 0 #elidable function (and cannot raise)
    EF_LOOPINVARIANT                   = 1 #special: call it only once per loop
    EF_CANNOT_RAISE                    = 2 #a function which cannot raise
    EF_ELIDABLE_CAN_RAISE              = 3 #elidable function (but can raise)
    EF_CAN_RAISE                       = 4 #normal function (can raise)
    EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE = 5 #can raise and force virtualizables
    EF_RANDOM_EFFECTS                  = 6 #can do whatever

    OS_ARRAYCOPY = 0

    def __init__(self, extraeffect, oopspecindex):
        self.extraeffect = extraeffect
        self.oopspecindex = oopspecindex

class FakeCallDescr(object):
    def __init__(self, extraeffect, oopspecindex=None):
        self.extraeffect = extraeffect
        self.oopspecindex = oopspecindex

    def get_extra_info(self):
        return FakeEffektinfo(self.extraeffect, self.oopspecindex)

class TestHeapCache(object):
    def test_known_class_box(self):
        h = HeapCache()
        assert not h.is_class_known(1)
        assert not h.is_class_known(2)
        h.class_now_known(1)
        assert h.is_class_known(1)
        assert not h.is_class_known(2)

        h.reset()
        assert not h.is_class_known(1)
        assert not h.is_class_known(2)

    def test_nonstandard_virtualizable(self):
        h = HeapCache()
        assert not h.is_nonstandard_virtualizable(1)
        assert not h.is_nonstandard_virtualizable(2)
        h.nonstandard_virtualizables_now_known(1)
        assert h.is_nonstandard_virtualizable(1)
        assert not h.is_nonstandard_virtualizable(2)

        h.reset()
        assert not h.is_nonstandard_virtualizable(1)
        assert not h.is_nonstandard_virtualizable(2)


    def test_heapcache_fields(self):
        h = HeapCache()
        assert h.getfield(box1, descr1) is None
        assert h.getfield(box1, descr2) is None
        h.setfield(box1, descr1, box2)
        assert h.getfield(box1, descr1) is box2
        assert h.getfield(box1, descr2) is None
        h.setfield(box1, descr2, box3)
        assert h.getfield(box1, descr1) is box2
        assert h.getfield(box1, descr2) is box3
        h.setfield(box1, descr1, box3)
        assert h.getfield(box1, descr1) is box3
        assert h.getfield(box1, descr2) is box3
        h.setfield(box3, descr1, box1)
        assert h.getfield(box3, descr1) is box1
        assert h.getfield(box1, descr1) is None
        assert h.getfield(box1, descr2) is box3

        h.reset()
        assert h.getfield(box1, descr1) is None
        assert h.getfield(box1, descr2) is None
        assert h.getfield(box3, descr1) is None

    def test_heapcache_read_fields_multiple(self):
        h = HeapCache()
        h.getfield_now_known(box1, descr1, box2)
        h.getfield_now_known(box3, descr1, box4)
        assert h.getfield(box1, descr1) is box2
        assert h.getfield(box1, descr2) is None
        assert h.getfield(box3, descr1) is box4
        assert h.getfield(box3, descr2) is None

        h.reset()
        assert h.getfield(box1, descr1) is None
        assert h.getfield(box1, descr2) is None
        assert h.getfield(box3, descr1) is None
        assert h.getfield(box3, descr2) is None

    def test_heapcache_write_fields_multiple(self):
        h = HeapCache()
        h.setfield(box1, descr1, box2)
        assert h.getfield(box1, descr1) is box2
        h.setfield(box3, descr1, box4)
        assert h.getfield(box3, descr1) is box4
        assert h.getfield(box1, descr1) is None # box1 and box3 can alias

        h = HeapCache()
        h.new(box1)
        h.setfield(box1, descr1, box2)
        assert h.getfield(box1, descr1) is box2
        h.setfield(box3, descr1, box4)
        assert h.getfield(box3, descr1) is box4
        assert h.getfield(box1, descr1) is None # box1 and box3 can alias

        h = HeapCache()
        h.new(box1)
        h.new(box3)
        h.setfield(box1, descr1, box2)
        assert h.getfield(box1, descr1) is box2
        h.setfield(box3, descr1, box4)
        assert h.getfield(box3, descr1) is box4
        assert h.getfield(box1, descr1) is box2 # box1 and box3 cannot alias
        h.setfield(box1, descr1, box3)
        assert h.getfield(box1, descr1) is box3


    def test_heapcache_arrays(self):
        h = HeapCache()
        assert h.getarrayitem(box1, descr1, index1) is None
        assert h.getarrayitem(box1, descr2, index1) is None
        assert h.getarrayitem(box1, descr1, index2) is None
        assert h.getarrayitem(box1, descr2, index2) is None

        h.setarrayitem(box1, descr1, index1, box2)
        assert h.getarrayitem(box1, descr1, index1) is box2
        assert h.getarrayitem(box1, descr2, index1) is None
        assert h.getarrayitem(box1, descr1, index2) is None
        assert h.getarrayitem(box1, descr2, index2) is None
        h.setarrayitem(box1, descr1, index2, box4)
        assert h.getarrayitem(box1, descr1, index1) is box2
        assert h.getarrayitem(box1, descr2, index1) is None
        assert h.getarrayitem(box1, descr1, index2) is box4
        assert h.getarrayitem(box1, descr2, index2) is None

        h.setarrayitem(box1, descr2, index1, box3)
        assert h.getarrayitem(box1, descr1, index1) is box2
        assert h.getarrayitem(box1, descr2, index1) is box3
        assert h.getarrayitem(box1, descr1, index2) is box4
        assert h.getarrayitem(box1, descr2, index2) is None

        h.setarrayitem(box1, descr1, index1, box3)
        assert h.getarrayitem(box1, descr1, index1) is box3
        assert h.getarrayitem(box1, descr2, index1) is box3
        assert h.getarrayitem(box1, descr1, index2) is box4
        assert h.getarrayitem(box1, descr2, index2) is None

        h.setarrayitem(box3, descr1, index1, box1)
        assert h.getarrayitem(box3, descr1, index1) is box1
        assert h.getarrayitem(box1, descr1, index1) is None
        assert h.getarrayitem(box1, descr2, index1) is box3
        assert h.getarrayitem(box1, descr1, index2) is box4
        assert h.getarrayitem(box1, descr2, index2) is None

        h.reset()
        assert h.getarrayitem(box1, descr1, index1) is None
        assert h.getarrayitem(box1, descr2, index1) is None
        assert h.getarrayitem(box3, descr1, index1) is None

    def test_heapcache_array_nonconst_index(self):
        h = HeapCache()
        h.setarrayitem(box1, descr1, index1, box2)
        h.setarrayitem(box1, descr1, index2, box4)
        assert h.getarrayitem(box1, descr1, index1) is box2
        assert h.getarrayitem(box1, descr1, index2) is box4
        h.setarrayitem(box1, descr1, box2, box3)
        assert h.getarrayitem(box1, descr1, index1) is None
        assert h.getarrayitem(box1, descr1, index2) is None

    def test_heapcache_read_fields_multiple_array(self):
        h = HeapCache()
        h.getarrayitem_now_known(box1, descr1, index1, box2)
        h.getarrayitem_now_known(box3, descr1, index1, box4)
        assert h.getarrayitem(box1, descr1, index1) is box2
        assert h.getarrayitem(box1, descr2, index1) is None
        assert h.getarrayitem(box3, descr1, index1) is box4
        assert h.getarrayitem(box3, descr2, index1) is None

        h.reset()
        assert h.getarrayitem(box1, descr1, index1) is None
        assert h.getarrayitem(box1, descr2, index1) is None
        assert h.getarrayitem(box3, descr1, index1) is None
        assert h.getarrayitem(box3, descr2, index1) is None

    def test_heapcache_write_fields_multiple_array(self):
        h = HeapCache()
        h.setarrayitem(box1, descr1, index1, box2)
        assert h.getarrayitem(box1, descr1, index1) is box2
        h.setarrayitem(box3, descr1, index1, box4)
        assert h.getarrayitem(box3, descr1, index1) is box4
        assert h.getarrayitem(box1, descr1, index1) is None # box1 and box3 can alias

        h = HeapCache()
        h.new(box1)
        h.setarrayitem(box1, descr1, index1, box2)
        assert h.getarrayitem(box1, descr1, index1) is box2
        h.setarrayitem(box3, descr1, index1, box4)
        assert h.getarrayitem(box3, descr1, index1) is box4
        assert h.getarrayitem(box1, descr1, index1) is None # box1 and box3 can alias

        h = HeapCache()
        h.new(box1)
        h.new(box3)
        h.setarrayitem(box1, descr1, index1, box2)
        assert h.getarrayitem(box1, descr1, index1) is box2
        h.setarrayitem(box3, descr1, index1, box4)
        assert h.getarrayitem(box3, descr1, index1) is box4
        assert h.getarrayitem(box1, descr1, index1) is box2 # box1 and box3 cannot alias
        h.setarrayitem(box1, descr1, index1, box3)
        assert h.getarrayitem(box3, descr1, index1) is box4
        assert h.getarrayitem(box1, descr1, index1) is box3 # box1 and box3 cannot alias

    def test_length_cache(self):
        h = HeapCache()
        h.new_array(box1, lengthbox1)
        assert h.arraylen(box1) is lengthbox1

        assert h.arraylen(box2) is None
        h.arraylen_now_known(box2, lengthbox2)
        assert h.arraylen(box2) is lengthbox2


    def test_invalidate_cache(self):
        h = HeapCache()
        h.setfield(box1, descr1, box2)
        h.setarrayitem(box1, descr1, index1, box2)
        h.setarrayitem(box1, descr1, index2, box4)
        h.invalidate_caches(rop.INT_ADD, None, [])
        h.invalidate_caches(rop.INT_ADD_OVF, None, [])
        h.invalidate_caches(rop.SETFIELD_RAW, None, [])
        h.invalidate_caches(rop.SETARRAYITEM_RAW, None, [])
        assert h.getfield(box1, descr1) is box2
        assert h.getarrayitem(box1, descr1, index1) is box2
        assert h.getarrayitem(box1, descr1, index2) is box4

        h.invalidate_caches(
            rop.CALL, FakeCallDescr(FakeEffektinfo.EF_ELIDABLE_CANNOT_RAISE), [])
        assert h.getfield(box1, descr1) is box2
        assert h.getarrayitem(box1, descr1, index1) is box2
        assert h.getarrayitem(box1, descr1, index2) is box4

        h.invalidate_caches(
            rop.CALL_LOOPINVARIANT, FakeCallDescr(FakeEffektinfo.EF_LOOPINVARIANT), [])

        h.invalidate_caches(
            rop.CALL, FakeCallDescr(FakeEffektinfo.EF_RANDOM_EFFECTS), [])
        assert h.getfield(box1, descr1) is None
        assert h.getarrayitem(box1, descr1, index1) is None
        assert h.getarrayitem(box1, descr1, index2) is None


    def test_replace_box(self):
        h = HeapCache()
        h.setfield(box1, descr1, box2)
        h.setfield(box1, descr2, box3)
        h.setfield(box2, descr3, box3)
        h.replace_box(box1, box4)
        assert h.getfield(box1, descr1) is None
        assert h.getfield(box1, descr2) is None
        assert h.getfield(box4, descr1) is box2
        assert h.getfield(box4, descr2) is box3
        assert h.getfield(box2, descr3) is box3

    def test_replace_box_array(self):
        h = HeapCache()
        h.setarrayitem(box1, descr1, index1, box2)
        h.setarrayitem(box1, descr2, index1, box3)
        h.arraylen_now_known(box1, lengthbox1)
        h.setarrayitem(box2, descr1, index2, box1)
        h.setarrayitem(box3, descr2, index2, box1)
        h.setarrayitem(box2, descr3, index2, box3)
        h.replace_box(box1, box4)
        assert h.getarrayitem(box1, descr1, index1) is None
        assert h.getarrayitem(box1, descr2, index1) is None
        assert h.arraylen(box1) is None
        assert h.arraylen(box4) is lengthbox1
        assert h.getarrayitem(box4, descr1, index1) is box2
        assert h.getarrayitem(box4, descr2, index1) is box3
        assert h.getarrayitem(box2, descr1, index2) is box4
        assert h.getarrayitem(box3, descr2, index2) is box4
        assert h.getarrayitem(box2, descr3, index2) is box3

        h.replace_box(lengthbox1, lengthbox2)
        assert h.arraylen(box4) is lengthbox2

    def test_ll_arraycopy(self):
        h = HeapCache()
        h.new_array(box1, lengthbox1)
        h.setarrayitem(box1, descr1, index1, box2)
        h.new_array(box2, lengthbox1)
        # Just need the destination box for this call
        h.invalidate_caches(
            rop.CALL,
            FakeCallDescr(FakeEffektinfo.EF_CANNOT_RAISE, FakeEffektinfo.OS_ARRAYCOPY),
            [None, None, box2, None, None]
        )
        assert h.getarrayitem(box1, descr1, index1) is box2
        h.invalidate_caches(
            rop.CALL,
            FakeCallDescr(FakeEffektinfo.EF_CANNOT_RAISE, FakeEffektinfo.OS_ARRAYCOPY),
            [None, None, box3, None, None]
        )
        assert h.getarrayitem(box1, descr1, index1) is None

        h.setarrayitem(box4, descr1, index1, box2)
        assert h.getarrayitem(box4, descr1, index1) is box2
        h.invalidate_caches(
            rop.CALL,
            FakeCallDescr(FakeEffektinfo.EF_CANNOT_RAISE, FakeEffektinfo.OS_ARRAYCOPY),
            [None, None, box2, None, None]
        )
        assert h.getarrayitem(box4, descr1, index1) is None

    def test_unescaped(self):
        h = HeapCache()
        assert not h.is_unescaped(box1)
        h.new(box2)
        assert h.is_unescaped(box2)
        h.invalidate_caches(rop.SETFIELD_GC, None, [box2, box1])
        assert h.is_unescaped(box2)
        h.invalidate_caches(rop.SETFIELD_GC, None, [box1, box2])
        assert not h.is_unescaped(box2)

    def test_unescaped_testing(self):
        h = HeapCache()
        h.new(box1)
        h.new(box2)
        assert h.is_unescaped(box1)
        assert h.is_unescaped(box2)
        # Putting a virtual inside of another virtual doesn't escape it.
        h.invalidate_caches(rop.SETFIELD_GC, None, [box1, box2])
        assert h.is_unescaped(box2)
        # Reading a field from a virtual doesn't escape it.
        h.invalidate_caches(rop.GETFIELD_GC, None, [box1])
        assert h.is_unescaped(box1)
        # Escaping a virtual transitively escapes anything inside of it.
        assert not h.is_unescaped(box3)
        h.invalidate_caches(rop.SETFIELD_GC, None, [box3, box1])
        assert not h.is_unescaped(box1)
        assert not h.is_unescaped(box2)

    def test_unescaped_array(self):
        h = HeapCache()
        h.new_array(box1, lengthbox1)
        assert h.is_unescaped(box1)
        h.invalidate_caches(rop.SETARRAYITEM_GC, None, [box1, index1, box2])
        assert h.is_unescaped(box1)
        h.invalidate_caches(rop.SETARRAYITEM_GC, None, [box2, index1, box1])
        assert not h.is_unescaped(box1)