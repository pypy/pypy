import py
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.memory.gc.incminimark import IncrementalMiniMarkGC
from rpython.memory.gc.test.test_direct import BaseDirectGCTest
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT

PYOBJ_HDR = IncrementalMiniMarkGC.PYOBJ_HDR
PYOBJ_HDR_PTR = IncrementalMiniMarkGC.PYOBJ_HDR_PTR

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
            self.gc.minor_collection()
        count1 = len(self.trigger)
        self.gc.rrc_invoke_callback()
        count2 = len(self.trigger)
        assert count2 - count1 == expected_trigger

    def create_gcobj(self, intval, old=False, immortal=False):
        if immortal:
            p1 = lltype.malloc(S, immortal=True)
            p1.x = intval
            self.consider_constant(p1)
            return p1
        p1 = self.malloc(S)
        p1.x = intval
        if old:
            self.stackroots.append(p1)
            self._collect(major=False)
            p1 = self.stackroots.pop()
        return p1

    def create_rawobj(self, immortal=False):
        r1 = lltype.malloc(PYOBJ_HDR, flavor='raw', immortal=immortal)
        r1.ob_refcnt = 0
        r1.ob_pypy_link = 0
        return r1

    def create_link(self, rawobj, gcobj, is_light=False, is_pyobj=False):
        if is_light:
            rawobj.ob_refcnt += REFCNT_FROM_PYPY_LIGHT
        else:
            rawobj.ob_refcnt += REFCNT_FROM_PYPY
        rawaddr = llmemory.cast_ptr_to_adr(rawobj)
        gcref = lltype.cast_opaque_ptr(llmemory.GCREF, gcobj)
        if is_pyobj:
            assert not is_light
            self.gc.rawrefcount_create_link_pyobj(gcref, rawaddr)
        else:
            self.gc.rawrefcount_create_link_pypy(gcref, rawaddr)

    def _rawrefcount_pair(self, intval, is_light=False, is_pyobj=False,
                          create_old=False, create_immortal=False):
        self.trigger = []
        self.gc.rawrefcount_init(lambda: self.trigger.append(1))
        #
        p1 = self.create_gcobj(intval, old=create_old, immortal=create_immortal)
        r1 = self.create_rawobj(immortal=create_immortal)
        self.create_link(r1, p1, is_light=is_light, is_pyobj=is_pyobj)
        if is_light:
            rc = REFCNT_FROM_PYPY_LIGHT
        else:
            rc = REFCNT_FROM_PYPY
        assert r1.ob_refcnt == rc
        assert r1.ob_pypy_link != 0

        def check_alive(extra_refcount):
            assert r1.ob_refcnt == rc + extra_refcount
            assert r1.ob_pypy_link != 0
            r1addr = llmemory.cast_ptr_to_adr(r1)
            p1ref = self.gc.rawrefcount_to_obj(r1addr)
            p1 = lltype.cast_opaque_ptr(lltype.Ptr(S), p1ref)
            assert p1.x == intval
            if not is_pyobj:
                assert self.gc.rawrefcount_from_obj(p1ref) == r1addr
            else:
                assert self.gc.rawrefcount_from_obj(p1ref) == llmemory.NULL
            return p1
        return p1, r1, check_alive

    @py.test.mark.parametrize('old', [True, False])
    def test_rawrefcount_objects_basic(self, old):
        p1, r1, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        p1ref = lltype.cast_opaque_ptr(llmemory.GCREF, p1)
        r1addr = llmemory.cast_ptr_to_adr(r1)
        assert r1.ob_pypy_link != 0
        assert self.gc.rawrefcount_from_obj(p1ref) == r1addr
        assert self.gc.rawrefcount_to_obj(r1addr) == p1ref
        p2 = self.create_gcobj(84)
        r2 = self.create_rawobj()
        r2.ob_refcnt += 1
        p2ref = lltype.cast_opaque_ptr(llmemory.GCREF, p2)
        r2addr = llmemory.cast_ptr_to_adr(r2)
        # p2 and r2 are not linked
        assert r2.ob_pypy_link == 0
        assert self.gc.rawrefcount_from_obj(p2ref) == llmemory.NULL
        assert self.gc.rawrefcount_to_obj(r2addr) == lltype.nullptr(
            llmemory.GCREF.TO)
        lltype.free(r1, flavor='raw')
        lltype.free(r2, flavor='raw')

    @py.test.mark.parametrize('old', [True, False])
    def test_rawrefcount_objects_collection_survives_from_raw(self, old):
        p1, r1, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        check_alive(0)
        r1.ob_refcnt += 1
        self._collect(major=False)
        check_alive(+1)
        self._collect(major=True)
        check_alive(+1)
        r1.ob_refcnt -= 1
        self._collect(major=False)
        p1 = check_alive(0)
        self._collect(major=True)
        py.test.raises(RuntimeError, "r1.ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()
        assert self.trigger == []
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL

    @py.test.mark.parametrize('old', [True, False])
    def test_rawrefcount_dies_quickly(self, old):
        p1, r1, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        check_alive(0)
        self._collect(major=False)
        if old:
            check_alive(0)
            self._collect(major=True)
        py.test.raises(RuntimeError, "r1.ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()

    @py.test.mark.parametrize('old', [True, False])
    def test_rawrefcount_objects_collection_survives_from_obj(self, old):
        p1, r1, check_alive = (
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
        py.test.raises(RuntimeError, "r1.ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()

    @py.test.mark.parametrize('old', [True, False])
    def test_pypy_nonlight_survives_from_raw(self, old):
        p1, r1, check_alive = (
            self._rawrefcount_pair(42, is_light=False, create_old=old))
        check_alive(0)
        r1.ob_refcnt += 1
        self._collect(major=False)
        check_alive(+1)
        self._collect(major=True)
        check_alive(+1)
        r1.ob_refcnt -= 1
        self._collect(major=False)
        p1 = check_alive(0)
        self._collect(major=True, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.ob_refcnt == 0
        assert r1.ob_pypy_link == 0
        r1addr = llmemory.cast_ptr_to_adr(r1)
        assert self.gc.rawrefcount_next_dead() == r1addr
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    @py.test.mark.parametrize('old', [True, False])
    def test_pypy_nonlight_survives_from_obj(self, old):
        p1, r1, check_alive = (
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
        assert r1.ob_refcnt == 0
        assert r1.ob_pypy_link == 0
        r1addr = llmemory.cast_ptr_to_adr(r1)
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    @py.test.mark.parametrize('old', [True, False])
    def test_pypy_nonlight_dies_quickly(self, old):
        p1, r1, check_alive = (
            self._rawrefcount_pair(42, is_light=False, create_old=old))
        check_alive(0)
        if old:
            self._collect(major=False)
            check_alive(0)
            self._collect(major=True, expected_trigger=1)
        else:
            self._collect(major=False, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.ob_refcnt == 0
        assert r1.ob_pypy_link == 0
        r1addr = llmemory.cast_ptr_to_adr(r1)
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pyobject_pypy_link_dies_on_minor_collection(self):
        p1, r1, check_alive = (
            self._rawrefcount_pair(42, is_pyobj=True))
        check_alive(0)
        r1.ob_refcnt += 1            # the pyobject is kept alive
        self._collect(major=False)
        assert r1.ob_refcnt == 1     # refcnt dropped to 1
        assert r1.ob_pypy_link == 0  # detached
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    @py.test.mark.parametrize('old', [True, False])
    def test_pyobject_dies(self, old):
        p1, r1, check_alive = (
            self._rawrefcount_pair(42, is_pyobj=True, create_old=old))
        check_alive(0)
        if old:
            self._collect(major=False)
            check_alive(0)
            self._collect(major=True, expected_trigger=1)
        else:
            self._collect(major=False, expected_trigger=1)
        assert r1.ob_refcnt == 0     # refcnt dropped to 0
        assert r1.ob_pypy_link == 0  # detached
        r1addr = llmemory.cast_ptr_to_adr(r1)
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    @py.test.mark.parametrize('old', [True, False])
    def test_pyobject_survives_from_obj(self, old):
        p1, r1, check_alive = (
            self._rawrefcount_pair(42, is_pyobj=True, create_old=old))
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
        assert r1.ob_refcnt == 0
        assert r1.ob_pypy_link == 0
        r1addr = llmemory.cast_ptr_to_adr(r1)
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pyobject_attached_to_prebuilt_obj(self):
        p1, r1, check_alive = (
            self._rawrefcount_pair(42, create_immortal=True))
        check_alive(0)
        self._collect(major=True)
        check_alive(0)
