import py
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.memory.gc.incminimark import IncrementalMiniMarkGC
from rpython.memory.gc.test.test_direct import BaseDirectGCTest
from rpython.rlib import rawrefcount
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT

# The prefix relocation trips two untranslated-only fakeaddress/ll2ctypes limits:
# a symbolic link (a moved object's address) can't round-trip through the raw prefix,
# and lltype.free of the prefixed allocation doesn't invalidate the test's cast pointer.
# Both moving-GC paths are covered translated by
# rpython/rlib/test/test_rawrefcount.py::TestTranslated::test_full_translation.
_SKIP_UNTRANSLATED = "prefix: untranslated fakeaddress/ll2ctypes limitation, see comment"

S = lltype.GcForwardReference()
S.become(lltype.GcStruct('S',
                         ('x', lltype.Signed),
                         ('prev', lltype.Ptr(S)),
                         ('next', lltype.Ptr(S))))


class TestRawRefCount(BaseDirectGCTest):
    GCClass = IncrementalMiniMarkGC
    # TestRawRefCountNoPrefix below reruns everything here with the opposite
    # rawrefcount_link_prefix mode -- both must actually be exercised, since
    # rpython.rlib.rawrefcount (used directly by this file) and self.gc (built
    # from BaseDirectGCTest's generic, prefix-less-by-default config) each
    # need to agree on the same mode or link reads/writes land at different
    # offsets. See the "must be kept in sync by hand" note in rawrefcount.py.
    link_prefix = True

    def setup_method(self, meth):
        BaseDirectGCTest.setup_method(self, meth)
        rawrefcount.configure(self.link_prefix)
        class _Config(object):
            rawrefcount_link_prefix = self.link_prefix
        self.gc._setup_rawrefcount_pyobj_hdr(_Config())

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
        self.gc.rawrefcount_init(lambda: self.trigger.append(1))
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
        # r1 points at ob_refcnt; the ob_pypy_link prefix is reserved before it
        r1 = rawrefcount._pyobject_alloc(immortal=create_immortal)
        r1.c_ob_refcnt = rc
        r1addr = llmemory.cast_ptr_to_adr(r1)
        if is_pyobj:
            assert not is_light
            self.gc.rawrefcount_create_link_pyobj(p1ref, r1addr)
        else:
            self.gc.rawrefcount_create_link_pypy(p1ref, r1addr)
        assert r1.c_ob_refcnt == rc
        assert rawrefcount._ob_link_get(r1) != 0

        def check_alive(extra_refcount):
            assert r1.c_ob_refcnt == rc + extra_refcount
            assert rawrefcount._ob_link_get(r1) != 0
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
        r2 = rawrefcount._pyobject_alloc()
        r2.c_ob_refcnt = 1
        r2addr = llmemory.cast_ptr_to_adr(r2)
        # p2 and r2 are not linked
        assert rawrefcount._ob_link_get(r1) != 0
        assert rawrefcount._ob_link_get(r2) == 0
        assert self.gc.rawrefcount_from_obj(p1ref) == r1addr
        assert self.gc.rawrefcount_from_obj(p2ref) == llmemory.NULL
        assert self.gc.rawrefcount_to_obj(r1addr) == p1ref
        assert self.gc.rawrefcount_to_obj(r2addr) == lltype.nullptr(
            llmemory.GCREF.TO)
        rawrefcount._ob_free(r1)
        rawrefcount._ob_free(r2)

    @py.test.mark.skipif(True, reason=_SKIP_UNTRANSLATED)
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

    @py.test.mark.skipif(True, reason=_SKIP_UNTRANSLATED)
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

    @py.test.mark.skipif(True, reason=_SKIP_UNTRANSLATED)
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
    @py.test.mark.skipif(True, reason=_SKIP_UNTRANSLATED)
    def test_rawrefcount_objects_collection_survives_from_raw_old(self):
        self.test_rawrefcount_objects_collection_survives_from_raw(old=True)
    @py.test.mark.skipif(True, reason=_SKIP_UNTRANSLATED)
    def test_rawrefcount_dies_quickly_old(self):
        self.test_rawrefcount_dies_quickly(old=True)
    @py.test.mark.skipif(True, reason=_SKIP_UNTRANSLATED)
    def test_rawrefcount_objects_collection_survives_from_obj_old(self):
        self.test_rawrefcount_objects_collection_survives_from_obj(old=True)

    @py.test.mark.skipif(True, reason=_SKIP_UNTRANSLATED)   # only old=False fails
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
        assert r1.c_ob_refcnt == REFCNT_FROM_PYPY + 1       # in the pending list
        assert rawrefcount._ob_link_get(r1) == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        self.gc.check_no_more_rawrefcount_state()
        rawrefcount._ob_free(r1)

    @py.test.mark.skipif(True, reason=_SKIP_UNTRANSLATED)   # only old=False fails
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
        assert r1.c_ob_refcnt == REFCNT_FROM_PYPY + 1
        assert rawrefcount._ob_link_get(r1) == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        rawrefcount._ob_free(r1)

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
        assert r1.c_ob_refcnt == REFCNT_FROM_PYPY + 1
        assert rawrefcount._ob_link_get(r1) == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        rawrefcount._ob_free(r1)

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
        assert r1.c_ob_refcnt == REFCNT_FROM_PYPY + 1     # refcnt dropped to 1
        assert rawrefcount._ob_link_get(r1) == 0  # detached
        self.gc.check_no_more_rawrefcount_state()
        rawrefcount._ob_free(r1)

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
        assert r1.c_ob_refcnt == REFCNT_FROM_PYPY + 1     # refcnt 1, in the pending list
        assert rawrefcount._ob_link_get(r1) == 0  # detached
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        rawrefcount._ob_free(r1)

    @py.test.mark.parametrize('old,external', [
        (False, False), (True, False), (False, True)])
    def test_pyobject_survives_from_obj(self, old, external):
        if not old and not external:
            py.test.skip(_SKIP_UNTRANSLATED)   # nursery-move symbolic link only
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
        assert r1.c_ob_refcnt == REFCNT_FROM_PYPY + 1
        assert rawrefcount._ob_link_get(r1) == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        rawrefcount._ob_free(r1)

    def test_pyobject_attached_to_prebuilt_obj(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, create_immortal=True))
        check_alive(0)
        self._collect(major=True)
        check_alive(0)

    def test_rawrefcount_next_dead_robust_against_non_init(self):
        # does not crash despite not calling init
        assert not self.gc.rawrefcount_next_dead()


class TestRawRefCountNoPrefix(TestRawRefCount):
    link_prefix = False
