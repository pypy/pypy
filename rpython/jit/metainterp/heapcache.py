from rpython.jit.metainterp.history import Const, ConstInt
from rpython.jit.metainterp.history import FrontendOp, RefFrontendOp
from rpython.jit.metainterp.resoperation import rop, OpHelpers
from rpython.jit.metainterp.executor import constant_from_op
from rpython.rlib.rarithmetic import r_uint32, r_uint
from rpython.rlib.objectmodel import always_inline

""" A big note: we don't do heap caches on Consts, because it used
to be done with the identity of the Const instance. This gives very wonky
results at best, so we decided to not do it at all. Can be fixed with
interning of Consts (already done on trace anyway)
"""

# RefFrontendOp._heapc_flags:
HF_LIKELY_VIRTUAL  = 0x01
HF_KNOWN_CLASS     = 0x02
HF_KNOWN_NULLITY   = 0x04
HF_SEEN_ALLOCATION = 0x08   # did we see the allocation during tracing?
HF_IS_UNESCAPED    = 0x10
HF_NONSTD_VABLE    = 0x20

_HF_VERSION_INC    = 0x40   # must be last
_HF_VERSION_MAX    = r_uint(2 ** 32 - _HF_VERSION_INC)

@always_inline
def add_flags(ref_frontend_op, flags):
    f = ref_frontend_op._get_heapc_flags()
    f |= r_uint(flags)
    ref_frontend_op._set_heapc_flags(f)

@always_inline
def remove_flags(ref_frontend_op, flags):
    f = ref_frontend_op._get_heapc_flags()
    f &= r_uint(~flags)
    ref_frontend_op._set_heapc_flags(f)

@always_inline
def test_flags(ref_frontend_op, flags):
    f = ref_frontend_op._get_heapc_flags()
    return bool(f & r_uint(flags))

def maybe_replace_with_const(box):
    if not isinstance(box, Const) and box.is_replaced_with_const():
        return constant_from_op(box)
    else:
        return box


class CacheEntry(object):
    def __init__(self, heapcache):
        # both are {from_ref_box: to_field_box} dicts
        # the first is for boxes where we did not see the allocation, the
        # second for anything else. the reason that distinction makes sense is
        # because if we saw the allocation, we know it cannot alias with
        # anything else where we saw the allocation.
        self.heapcache = heapcache
        self.cache_anything = {}
        self.cache_seen_allocation = {}

        # set of boxes that we've seen a quasi-immut for the field on. cleared
        # on writes to the field.
        self.quasiimmut_seen = None

    def _clear_cache_on_write(self, seen_allocation_of_target):
        if not seen_allocation_of_target:
            self.cache_seen_allocation.clear()
        self.cache_anything.clear()
        if self.quasiimmut_seen is not None:
            self.quasiimmut_seen.clear()

    def _seen_alloc(self, ref_box):
        if not isinstance(ref_box, RefFrontendOp):
            return False
        return self.heapcache._check_flag(ref_box, HF_SEEN_ALLOCATION)

    def _getdict(self, seen_alloc):
        if seen_alloc:
            return self.cache_seen_allocation
        else:
            return self.cache_anything

    def do_write_with_aliasing(self, ref_box, fieldbox):
        seen_alloc = self._seen_alloc(ref_box)
        self._clear_cache_on_write(seen_alloc)
        self._getdict(seen_alloc)[ref_box] = fieldbox

    def read(self, ref_box):
        dict = self._getdict(self._seen_alloc(ref_box))
        try:
            res_box = dict[ref_box]
        except KeyError:
            return None
        return maybe_replace_with_const(res_box)

    def read_now_known(self, ref_box, fieldbox):
        self._getdict(self._seen_alloc(ref_box))[ref_box] = fieldbox

    def invalidate_unescaped(self):
        self._invalidate_unescaped(self.cache_anything)
        self._invalidate_unescaped(self.cache_seen_allocation)
        if self.quasiimmut_seen is not None:
            self.quasiimmut_seen.clear()

    def _invalidate_unescaped(self, d):
        for ref_box in d.keys():
            if not self.heapcache.is_unescaped(ref_box):
                del d[ref_box]


class FieldUpdater(object):
    def __init__(self, ref_box, cache, fieldbox):
        self.ref_box = ref_box
        self.cache = cache
        self.currfieldbox = fieldbox     # <= read directly from pyjitpl.py

    def getfield_now_known(self, fieldbox):
        self.cache.read_now_known(self.ref_box, fieldbox)

    def setfield(self, fieldbox):
        self.cache.do_write_with_aliasing(self.ref_box, fieldbox)

class DummyFieldUpdater(FieldUpdater):
    def __init__(self):
        self.currfieldbox = None

    def getfield_now_known(self, fieldbox):
        pass

    def setfield(self, fieldbox):
        pass

dummy_field_updater = DummyFieldUpdater()


class HeapCache(object):
    def __init__(self):
        # Works with flags stored on RefFrontendOp._heapc_flags.
        # There are two ways to do a global resetting of these flags:
        # reset() and reset_keep_likely_virtual().  The basic idea is
        # to use a version number in each RefFrontendOp, and in order
        # to reset the flags globally, we increment the global version
        # number in this class.  Then when we read '_heapc_flags' we
        # also check if the associated version number is up-to-date
        # or not.  More precisely, we have two global version numbers
        # here: 'head_version' and 'likely_virtual_version'.  Normally
        # we use 'head_version'.  For is_likely_virtual() though, we
        # use the other, older version number.
        self.head_version = r_uint(0)
        self.likely_virtual_version = r_uint(0)
        self.reset()

    def reset(self):
        # Global reset of all flags.  Update both version numbers so
        # that any access to '_heapc_flags' will be marked as outdated.
        assert self.head_version < _HF_VERSION_MAX
        self.head_version += _HF_VERSION_INC
        self.likely_virtual_version = self.head_version
        #
        # heap cache
        # maps descrs to CacheEntry
        self.heap_cache = {}
        # heap array cache
        # maps descrs to {index: CacheEntry} dicts
        self.heap_array_cache = {}

    def reset_keep_likely_virtuals(self):
        # Update only 'head_version', but 'likely_virtual_version' remains
        # at its older value.
        assert self.head_version < _HF_VERSION_MAX
        self.head_version += _HF_VERSION_INC
        self.heap_cache = {}
        self.heap_array_cache = {}

    @always_inline
    def test_head_version(self, ref_frontend_op):
        return ref_frontend_op._get_heapc_flags() >= self.head_version

    @always_inline
    def test_likely_virtual_version(self, ref_frontend_op):
        return ref_frontend_op._get_heapc_flags() >= self.likely_virtual_version

    def update_version(self, ref_frontend_op):
        """Ensure the version of 'ref_frontend_op' is current.  If not,
        it will update 'ref_frontend_op' (removing most flags currently set).
        """
        if not self.test_head_version(ref_frontend_op):
            f = self.head_version
            if (self.test_likely_virtual_version(ref_frontend_op) and
                test_flags(ref_frontend_op, HF_LIKELY_VIRTUAL)):
                f |= HF_LIKELY_VIRTUAL
            ref_frontend_op._set_heapc_flags(f)
            ref_frontend_op._heapc_deps = None

    def invalidate_caches(self, opnum, descr, argboxes):
        self.mark_escaped(opnum, descr, argboxes)
        self.clear_caches(opnum, descr, argboxes)

    def _escape_from_write(self, box, fieldbox):
        if self.is_unescaped(box) and self.is_unescaped(fieldbox):
            deps = self._get_deps(box)
            deps.append(fieldbox)
        elif fieldbox is not None:
            self._escape_box(fieldbox)

    def mark_escaped(self, opnum, descr, argboxes):
        if opnum == rop.SETFIELD_GC:
            assert len(argboxes) == 2
            box, fieldbox = argboxes
            self._escape_from_write(box, fieldbox)
        elif opnum == rop.SETARRAYITEM_GC:
            assert len(argboxes) == 3
            box, indexbox, fieldbox = argboxes
            self._escape_from_write(box, fieldbox)
        elif ((opnum == rop.CALL_R or opnum == rop.CALL_I or
               opnum == rop.CALL_N or opnum == rop.CALL_F) and
              descr.get_extra_info().oopspecindex == descr.get_extra_info().OS_ARRAYCOPY and
              isinstance(argboxes[3], ConstInt) and
              isinstance(argboxes[4], ConstInt) and
              isinstance(argboxes[5], ConstInt) and
              descr.get_extra_info().single_write_descr_array is not None):
            # ARRAYCOPY with constant starts and constant length doesn't escape
            # its argument
            # XXX really?
            pass
        # GETFIELD_GC, PTR_EQ, and PTR_NE don't escape their
        # arguments
        elif (opnum != rop.GETFIELD_GC_R and
              opnum != rop.GETFIELD_GC_I and
              opnum != rop.GETFIELD_GC_F and
              opnum != rop.PTR_EQ and
              opnum != rop.PTR_NE and
              opnum != rop.INSTANCE_PTR_EQ and
              opnum != rop.INSTANCE_PTR_NE):
            for box in argboxes:
                self._escape_box(box)

    def _escape_box(self, box):
        if isinstance(box, RefFrontendOp):
            remove_flags(box, HF_LIKELY_VIRTUAL | HF_IS_UNESCAPED)
            deps = box._heapc_deps
            if deps is not None:
                if not self.test_head_version(box):
                    box._heapc_deps = None
                else:
                    # 'deps[0]' is abused to store the array length, keep it
                    if deps[0] is None:
                        box._heapc_deps = None
                    else:
                        box._heapc_deps = [deps[0]]
                    for i in range(1, len(deps)):
                        self._escape_box(deps[i])

    def clear_caches(self, opnum, descr, argboxes):
        if (opnum == rop.SETFIELD_GC or
            opnum == rop.SETARRAYITEM_GC or
            opnum == rop.SETFIELD_RAW or
            opnum == rop.SETARRAYITEM_RAW or
            opnum == rop.SETINTERIORFIELD_GC or
            opnum == rop.COPYSTRCONTENT or
            opnum == rop.COPYUNICODECONTENT or
            opnum == rop.STRSETITEM or
            opnum == rop.UNICODESETITEM or
            opnum == rop.SETFIELD_RAW or
            opnum == rop.SETARRAYITEM_RAW or
            opnum == rop.SETINTERIORFIELD_RAW or
            opnum == rop.RAW_STORE):
            return
        if (rop._OVF_FIRST <= opnum <= rop._OVF_LAST or
            rop._NOSIDEEFFECT_FIRST <= opnum <= rop._NOSIDEEFFECT_LAST or
            rop._GUARD_FIRST <= opnum <= rop._GUARD_LAST):
            return
        if (OpHelpers.is_plain_call(opnum) or
            OpHelpers.is_call_loopinvariant(opnum) or
            opnum == rop.COND_CALL):
            effectinfo = descr.get_extra_info()
            ef = effectinfo.extraeffect
            if (ef == effectinfo.EF_LOOPINVARIANT or
                ef == effectinfo.EF_ELIDABLE_CANNOT_RAISE or
                ef == effectinfo.EF_ELIDABLE_OR_MEMORYERROR or
                ef == effectinfo.EF_ELIDABLE_CAN_RAISE):
                return
            # A special case for ll_arraycopy, because it is so common, and its
            # effects are so well defined.
            elif effectinfo.oopspecindex == effectinfo.OS_ARRAYCOPY:
                self._clear_caches_arraycopy(opnum, descr, argboxes, effectinfo)
                return
            else:
                # Only invalidate things that are escaped
                # XXX can do better, only do it for the descrs in the effectinfo
                for descr, cache in self.heap_cache.iteritems():
                    cache.invalidate_unescaped()
                for descr, indices in self.heap_array_cache.iteritems():
                    for cache in indices.itervalues():
                        cache.invalidate_unescaped()
                return

        # XXX not completely sure, but I *think* it is needed to reset() the
        # state at least in the 'CALL_*' operations that release the GIL.  We
        # tried to do only the kind of resetting done by the two loops just
        # above, but hit an assertion in "pypy test_multiprocessing.py".
        self.reset_keep_likely_virtuals()

    def _clear_caches_arraycopy(self, opnum, desrc, argboxes, effectinfo):
        seen_allocation_of_target = self._check_flag(
                                            argboxes[2], HF_SEEN_ALLOCATION)
        if (
            isinstance(argboxes[3], ConstInt) and
            isinstance(argboxes[4], ConstInt) and
            isinstance(argboxes[5], ConstInt) and
            effectinfo.single_write_descr_array is not None
        ):
            descr = effectinfo.single_write_descr_array
            cache = self.heap_array_cache.get(descr, None)
            srcstart = argboxes[3].getint()
            dststart = argboxes[4].getint()
            length = argboxes[5].getint()
            for i in xrange(length):
                value = self.getarrayitem(
                    argboxes[1],
                    ConstInt(srcstart + i),
                    descr,
                )
                if value is not None:
                    self.setarrayitem(
                        argboxes[2],
                        ConstInt(dststart + i),
                        value,
                        descr,
                    )
                elif cache is not None:
                    try:
                        idx_cache = cache[dststart + i]
                    except KeyError:
                        pass
                    else:
                        idx_cache._clear_cache_on_write(seen_allocation_of_target)
            return
        elif (
            effectinfo.single_write_descr_array is not None
        ):
            # Fish the descr out of the effectinfo
            cache = self.heap_array_cache.get(effectinfo.single_write_descr_array, None)
            if cache is not None:
                for idx, cache in cache.iteritems():
                    cache._clear_cache_on_write(seen_allocation_of_target)
            return
        self.reset_keep_likely_virtuals()

    def _get_deps(self, box):
        if not isinstance(box, RefFrontendOp):
            return None
        self.update_version(box)
        if box._heapc_deps is None:
            box._heapc_deps = [None]
        return box._heapc_deps

    def _check_flag(self, box, flag):
        return (isinstance(box, RefFrontendOp) and
                    self.test_head_version(box) and
                    test_flags(box, flag))

    def _set_flag(self, box, flag):
        assert isinstance(box, RefFrontendOp)
        self.update_version(box)
        add_flags(box, flag)

    def is_class_known(self, box):
        return self._check_flag(box, HF_KNOWN_CLASS)

    def class_now_known(self, box):
        if isinstance(box, Const):
            return
        self._set_flag(box, HF_KNOWN_CLASS)

    def is_nullity_known(self, box):
        if isinstance(box, Const):
            return bool(box.getref_base())
        return self._check_flag(box, HF_KNOWN_NULLITY)

    def nullity_now_known(self, box):
        if isinstance(box, Const):
            return
        self._set_flag(box, HF_KNOWN_NULLITY)

    def is_nonstandard_virtualizable(self, box):
        return self._check_flag(box, HF_NONSTD_VABLE)

    def nonstandard_virtualizables_now_known(self, box):
        self._set_flag(box, HF_NONSTD_VABLE)

    def is_unescaped(self, box):
        return self._check_flag(box, HF_IS_UNESCAPED)

    def is_likely_virtual(self, box):
        # note: this is different from _check_flag()
        return (isinstance(box, RefFrontendOp) and
                self.test_likely_virtual_version(box) and
                test_flags(box, HF_LIKELY_VIRTUAL))

    def new(self, box):
        assert isinstance(box, RefFrontendOp)
        self.update_version(box)
        add_flags(box, HF_LIKELY_VIRTUAL | HF_SEEN_ALLOCATION | HF_IS_UNESCAPED)

    def new_array(self, box, lengthbox):
        self.new(box)
        self.arraylen_now_known(box, lengthbox)

    def getfield(self, box, descr):
        cache = self.heap_cache.get(descr, None)
        if cache:
            return cache.read(box)
        return None

    def get_field_updater(self, box, descr):
        if not isinstance(box, RefFrontendOp):
            return dummy_field_updater
        cache = self.heap_cache.get(descr, None)
        if cache is None:
            cache = self.heap_cache[descr] = CacheEntry(self)
            fieldbox = None
        else:
            fieldbox = cache.read(box)
        return FieldUpdater(box, cache, fieldbox)

    def getfield_now_known(self, box, descr, fieldbox):
        upd = self.get_field_updater(box, descr)
        upd.getfield_now_known(fieldbox)

    def setfield(self, box, fieldbox, descr):
        upd = self.get_field_updater(box, descr)
        upd.setfield(fieldbox)

    def getarrayitem(self, box, indexbox, descr):
        if not isinstance(indexbox, ConstInt):
            return None
        index = indexbox.getint()
        cache = self.heap_array_cache.get(descr, None)
        if cache:
            indexcache = cache.get(index, None)
            if indexcache is not None:
                return indexcache.read(box)
        return None

    def _get_or_make_array_cache_entry(self, indexbox, descr):
        if not isinstance(indexbox, ConstInt):
            return None
        index = indexbox.getint()
        cache = self.heap_array_cache.setdefault(descr, {})
        indexcache = cache.get(index, None)
        if indexcache is None:
            cache[index] = indexcache = CacheEntry(self)
        return indexcache


    def getarrayitem_now_known(self, box, indexbox, fieldbox, descr):
        indexcache = self._get_or_make_array_cache_entry(indexbox, descr)
        if indexcache:
            indexcache.read_now_known(box, fieldbox)

    def setarrayitem(self, box, indexbox, fieldbox, descr):
        if not isinstance(indexbox, ConstInt):
            cache = self.heap_array_cache.get(descr, None)
            if cache is not None:
                cache.clear()
            return
        indexcache = self._get_or_make_array_cache_entry(indexbox, descr)
        if indexcache:
            indexcache.do_write_with_aliasing(box, fieldbox)

    def arraylen(self, box):
        if (isinstance(box, RefFrontendOp) and
            self.test_head_version(box) and
            box._heapc_deps is not None):
            res_box = box._heapc_deps[0]
            if res_box is not None:
                return maybe_replace_with_const(res_box)
        return None

    def arraylen_now_known(self, box, lengthbox):
        # we store in '_heapc_deps' a list of boxes: the *first* box is
        # the known length or None, and the remaining boxes are the
        # regular dependencies.
        if isinstance(box, Const):
            return
        deps = self._get_deps(box)
        assert deps is not None
        deps[0] = lengthbox

    def replace_box(self, oldbox, newbox):
        # here, only for replacing a box with a const
        if isinstance(oldbox, FrontendOp) and isinstance(newbox, Const):
            assert newbox.same_constant(constant_from_op(oldbox))
            oldbox.set_replaced_with_const()

    def is_quasi_immut_known(self, fielddescr, box):
        cache = self.heap_cache.get(fielddescr, None)
        if cache is not None and cache.quasiimmut_seen is not None:
            return box in cache.quasiimmut_seen
        return False

    def quasi_immut_now_known(self, fielddescr, box):
        cache = self.heap_cache.get(fielddescr, None)
        if cache is None:
            cache = self.heap_cache[fielddescr] = CacheEntry(self)
        if cache.quasiimmut_seen is not None:
            cache.quasiimmut_seen[box] = None
        else:
            cache.quasiimmut_seen = {box: None}
