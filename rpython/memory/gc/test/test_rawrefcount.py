import py
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.memory.gc.incminimark import IncrementalMiniMarkGC
from rpython.memory.gc.test.test_direct import BaseDirectGCTest
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
PYOBJ_HDR = IncrementalMiniMarkGC.PYOBJ_HDR
PYOBJ_HDR_PTR = IncrementalMiniMarkGC.PYOBJ_HDR_PTR
RAWREFCOUNT_VISIT = IncrementalMiniMarkGC.RAWREFCOUNT_VISIT
PYOBJ_GC_HDR = IncrementalMiniMarkGC.PYOBJ_GC_HDR
PYOBJ_GC_HDR_PTR = IncrementalMiniMarkGC.PYOBJ_GC_HDR_PTR

S = lltype.GcForwardReference()
S.become(lltype.GcStruct('S',
                         ('x', lltype.Signed),
                         ('prev', lltype.Ptr(S)),
                         ('next', lltype.Ptr(S))))


class TestRawRefCount(BaseDirectGCTest):
    GCClass = IncrementalMiniMarkGC

    def _collect(self, major, expected_trigger=0):
        if major:
            self.gc.collect()
        else:
            self.gc._minor_collection()
        count1 = len(self.trigger)
        self.gc.rrc_invoke_callback()
        count2 = len(self.trigger)
        assert count2 - count1 == expected_trigger

    def _rawrefcount_pair(self, intval, is_light=False, is_pyobj=False,
                          create_old=False, create_immortal=False,
                          force_external=False):
        if is_light:
            rc = REFCNT_FROM_PYPY_LIGHT
        else:
            rc = REFCNT_FROM_PYPY
        self.trigger = []
        visit = self.gc._rrc_visit
        self.pyobj_gc_map = {}
        self.gc_pyobj_map = {}

        def rawrefcount_tp_traverse(obj, foo, args):
            print "VISITED!!!!!!!!!!!!!!!!!!!!!1"
            test = rffi.cast(S, obj)
            if llmemory.cast_ptr_to_adr(test.next).ptr is not None:
                next = rffi.cast(PYOBJ_HDR_PTR, test.next)
                vret = visit(next, args)
                if vret != 0:
                    return
            if llmemory.cast_ptr_to_adr(test.prev).ptr is not None:
                next = rffi.cast(PYOBJ_HDR_PTR, test.prev)
                visit(next, args)

        def rawrefcount_gc_as_pyobj(gc):
            return self.gc_pyobj_map[1] # TODO fix

        def rawrefcount_pyobj_as_gc(pyobj):
            return self.pyobj_gc_map[1] # TODO fix

        self.pyobj_list = lltype.malloc(PYOBJ_GC_HDR_PTR.TO, flavor='raw',
                                        immortal=True)
        self.pyobj_list.c_gc_next = self.pyobj_list
        self.pyobj_list.c_gc_next = self.pyobj_list
        self.gc.rawrefcount_init(lambda: self.trigger.append(1),
                                 rawrefcount_tp_traverse,
                                 llmemory.cast_ptr_to_adr(self.pyobj_list),
                                 rawrefcount_gc_as_pyobj,
                                 rawrefcount_pyobj_as_gc)
        #
        if create_immortal:
            p1 = lltype.malloc(S, immortal=True)
        else:
            saved = self.gc.nonlarge_max
            try:
                if force_external:
                    self.gc.nonlarge_max = 1
                p1 = self.malloc(S)
            finally:
                self.gc.nonlarge_max = saved
        p1.x = intval
        if create_immortal:
            self.consider_constant(p1)
        elif create_old:
            self.stackroots.append(p1)
            self._collect(major=False)
            p1 = self.stackroots.pop()
        p1ref = lltype.cast_opaque_ptr(llmemory.GCREF, p1)
        r1 = lltype.malloc(PYOBJ_HDR, flavor='raw',
                           immortal=create_immortal)
        r1.c_ob_refcnt = rc
        r1.c_ob_pypy_link = 0
        r1addr = llmemory.cast_ptr_to_adr(r1)

        r1gc = lltype.malloc(PYOBJ_GC_HDR, flavor='raw',
                             immortal=True)
        r1gc.c_gc_next = self.pyobj_list
        r1gc.c_gc_prev = self.pyobj_list
        self.pyobj_list.c_gc_next = r1gc
        self.pyobj_list.c_gc_prev = r1gc

        self.pyobj_gc_map[1] = r1gc
        self.gc_pyobj_map[1] = r1

        if is_pyobj:
            assert not is_light
            self.gc.rawrefcount_create_link_pyobj(p1ref, r1addr)
        else:
            self.gc.rawrefcount_create_link_pypy(p1ref, r1addr)
        assert r1.c_ob_refcnt == rc
        assert r1.c_ob_pypy_link != 0

        def check_alive(extra_refcount):
            assert r1.c_ob_refcnt == rc + extra_refcount
            assert r1.c_ob_pypy_link != 0
            p1ref = self.gc.rawrefcount_to_obj(r1addr)
            p1 = lltype.cast_opaque_ptr(lltype.Ptr(S), p1ref)
            assert p1.x == intval
            if not is_pyobj:
                assert self.gc.rawrefcount_from_obj(p1ref) == r1addr
            else:
                assert self.gc.rawrefcount_from_obj(p1ref) == llmemory.NULL
            return p1
        return p1, p1ref, r1, r1addr, check_alive

    def test_rawrefcount_objects_basic(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        p2 = self.malloc(S)
        p2.x = 84
        p2ref = lltype.cast_opaque_ptr(llmemory.GCREF, p2)
        r2 = lltype.malloc(PYOBJ_HDR_PTR.TO, flavor='raw')
        r2.c_ob_refcnt = 1
        r2.c_ob_pypy_link = 0
        r2addr = llmemory.cast_ptr_to_adr(r2)
        # p2 and r2 are not linked
        assert r1.c_ob_pypy_link != 0
        assert r2.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_from_obj(p1ref) == r1addr
        assert self.gc.rawrefcount_from_obj(p2ref) == llmemory.NULL
        assert self.gc.rawrefcount_to_obj(r1addr) == p1ref
        assert self.gc.rawrefcount_to_obj(r2addr) == lltype.nullptr(
            llmemory.GCREF.TO)
        lltype.free(r1, flavor='raw')
        lltype.free(r2, flavor='raw')

    def test_rawrefcount_objects_collection_survives_from_raw(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        check_alive(0)
        r1.c_ob_refcnt += 1
        self._collect(major=False)
        check_alive(+1)
        self._collect(major=True)
        check_alive(+1)
        r1.c_ob_refcnt -= 1
        self._collect(major=False)
        p1 = check_alive(0)
        self._collect(major=True)
        py.test.raises(RuntimeError, "r1.c_ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()
        assert self.trigger == []
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL

    def test_rawrefcount_dies_quickly(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        check_alive(0)
        self._collect(major=False)
        if old:
            check_alive(0)
            self._collect(major=True)
        py.test.raises(RuntimeError, "r1.c_ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()

    def test_rawrefcount_objects_collection_survives_from_obj(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        check_alive(0)
        self.stackroots.append(p1)
        self._collect(major=False)
        check_alive(0)
        self._collect(major=True)
        check_alive(0)
        p1 = self.stackroots.pop()
        self._collect(major=False)
        check_alive(0)
        assert p1.x == 42
        self._collect(major=True)
        py.test.raises(RuntimeError, "r1.c_ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()

    def test_rawrefcount_objects_basic_old(self):
        self.test_rawrefcount_objects_basic(old=True)
    def test_rawrefcount_objects_collection_survives_from_raw_old(self):
        self.test_rawrefcount_objects_collection_survives_from_raw(old=True)
    def test_rawrefcount_dies_quickly_old(self):
        self.test_rawrefcount_dies_quickly(old=True)
    def test_rawrefcount_objects_collection_survives_from_obj_old(self):
        self.test_rawrefcount_objects_collection_survives_from_obj(old=True)

    def test_pypy_nonlight_survives_from_raw(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=False, create_old=old))
        check_alive(0)
        r1.c_ob_refcnt += 1
        self._collect(major=False)
        check_alive(+1)
        self._collect(major=True)
        check_alive(+1)
        r1.c_ob_refcnt -= 1
        self._collect(major=False)
        p1 = check_alive(0)
        self._collect(major=True, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.c_ob_refcnt == 1       # in the pending list
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pypy_nonlight_survives_from_obj(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=False, create_old=old))
        check_alive(0)
        self.stackroots.append(p1)
        self._collect(major=False)
        check_alive(0)
        self._collect(major=True)
        check_alive(0)
        p1 = self.stackroots.pop()
        self._collect(major=False)
        check_alive(0)
        assert p1.x == 42
        self._collect(major=True, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.c_ob_refcnt == 1
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pypy_nonlight_dies_quickly(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=False, create_old=old))
        check_alive(0)
        if old:
            self._collect(major=False)
            check_alive(0)
            self._collect(major=True, expected_trigger=1)
        else:
            self._collect(major=False, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.c_ob_refcnt == 1
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pypy_nonlight_survives_from_raw_old(self):
        self.test_pypy_nonlight_survives_from_raw(old=True)
    def test_pypy_nonlight_survives_from_obj_old(self):
        self.test_pypy_nonlight_survives_from_obj(old=True)
    def test_pypy_nonlight_dies_quickly_old(self):
        self.test_pypy_nonlight_dies_quickly(old=True)

    @py.test.mark.parametrize('external', [False, True])
    def test_pyobject_pypy_link_dies_on_minor_collection(self, external):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_pyobj=True, force_external=external))
        check_alive(0)
        r1.c_ob_refcnt += 1            # the pyobject is kept alive
        self._collect(major=False)
        assert r1.c_ob_refcnt == 1     # refcnt dropped to 1
        assert r1.c_ob_pypy_link == 0  # detached
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    @py.test.mark.parametrize('old,external', [
        (False, False), (True, False), (False, True)])
    def test_pyobject_dies(self, old, external):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_pyobj=True, create_old=old,
                                   force_external=external))
        check_alive(0)
        if old:
            self._collect(major=False)
            check_alive(0)
            self._collect(major=True, expected_trigger=1)
        else:
            self._collect(major=False, expected_trigger=1)
        assert r1.c_ob_refcnt == 1     # refcnt 1, in the pending list
        assert r1.c_ob_pypy_link == 0  # detached
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    @py.test.mark.parametrize('old,external', [
        (False, False), (True, False), (False, True)])
    def test_pyobject_survives_from_obj(self, old, external):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_pyobj=True, create_old=old,
                                   force_external=external))
        check_alive(0)
        self.stackroots.append(p1)
        self._collect(major=False)
        check_alive(0)
        self._collect(major=True)
        check_alive(0)
        p1 = self.stackroots.pop()
        self._collect(major=False)
        check_alive(0)
        assert p1.x == 42
        assert self.trigger == []
        self._collect(major=True, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.c_ob_refcnt == 1
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pyobject_attached_to_prebuilt_obj(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, create_immortal=True))
        check_alive(0)
        self._collect(major=True)
        check_alive(0)

    def test_linked_cycle_self_reference_dies_without_external_reference(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42))
        r1.c_ob_refcnt += 1
        p1.next = p1
        check_alive(+1)
        self._collect(major=True, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")  # dead
        assert r1.c_ob_refcnt == 1  # in the pending list
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_linked_cycle_self_reference_survives_with_pyobj_reference(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, create_immortal=True))
        r1.c_ob_refcnt += 2  # the pyobject is kept alive
        p1.next = p1
        check_alive(+2)
        self._collect(major=True)
        check_alive(+2)
        r1.c_ob_refcnt -= 1 # the external reference from pyobj is removed
        check_alive(+1)
        self._collect(major=True, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")  # dead
        assert r1.c_ob_refcnt == 1  # in the pending list
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_linked_cycle_self_reference_survives_with_pypy_reference(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, create_immortal=True))
        r1.c_ob_refcnt += 1
        p1.next = p1
        self.stackroots.append(p1)
        check_alive(+1)
        self._collect(major=True)
        assert p1.x == 42
        assert self.trigger == []
        check_alive(+1)
        p1 = self.stackroots.pop()
        check_alive(+1)
        self._collect(major=True, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")  # dead
        assert r1.c_ob_refcnt == 1
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

# TODO: pyobj_cycle_self_reference (without linked pypy object)
# TODO: linked_cycle_simple
# TODO: pyobj_cycle_simple
# TODO: linked_cycle_complex
# TODO: pyobj_cycle_complex
# TODO: pyobj_cycle_dies_including_linked_pypy
