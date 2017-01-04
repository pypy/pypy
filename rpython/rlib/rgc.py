from __future__ import absolute_import

import gc
import types

from rpython.rlib import jit
from rpython.rlib.objectmodel import we_are_translated, enforceargs, specialize
from rpython.rlib.objectmodel import CDefinedIntSymbolic, not_rpython
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.lltypesystem import lltype, llmemory

# ____________________________________________________________
# General GC features

collect = gc.collect

def set_max_heap_size(nbytes):
    """Limit the heap size to n bytes.
    """
    pass

# for test purposes we allow objects to be pinned and use
# the following list to keep track of the pinned objects
_pinned_objects = []

def pin(obj):
    """If 'obj' can move, then attempt to temporarily fix it.  This
    function returns True if and only if 'obj' could be pinned; this is
    a special state in the GC.  Note that can_move(obj) still returns
    True even on pinned objects, because once unpinned it will indeed be
    able to move again.  In other words, the code that succeeded in
    pinning 'obj' can assume that it won't move until the corresponding
    call to unpin(obj), despite can_move(obj) still being True.  (This
    is important if multiple threads try to os.write() the same string:
    only one of them will succeed in pinning the string.)

    It is expected that the time between pinning and unpinning an object
    is short. Therefore the expected use case is a single function
    invoking pin(obj) and unpin(obj) only a few lines of code apart.

    Note that this can return False for any reason, e.g. if the 'obj' is
    already non-movable or already pinned, if the GC doesn't support
    pinning, or if there are too many pinned objects.

    Note further that pinning an object does not prevent it from being
    collected if it is not used anymore.
    """
    _pinned_objects.append(obj)
    return True
        

class PinEntry(ExtRegistryEntry):
    _about_ = pin

    def compute_result_annotation(self, s_obj):
        from rpython.annotator import model as annmodel
        return annmodel.SomeBool()

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.genop('gc_pin', hop.args_v, resulttype=hop.r_result)

def unpin(obj):
    """Unpin 'obj', allowing it to move again.
    Must only be called after a call to pin(obj) returned True.
    """
    for i in range(len(_pinned_objects)):
        try:
            if _pinned_objects[i] == obj:
                del _pinned_objects[i]
                return
        except TypeError:
            pass


class UnpinEntry(ExtRegistryEntry):
    _about_ = unpin

    def compute_result_annotation(self, s_obj):
        pass

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        hop.genop('gc_unpin', hop.args_v)

def _is_pinned(obj):
    """Method to check if 'obj' is pinned."""
    for i in range(len(_pinned_objects)):
        try:
            if _pinned_objects[i] == obj:
                return True
        except TypeError:
            pass
    return False


class IsPinnedEntry(ExtRegistryEntry):
    _about_ = _is_pinned

    def compute_result_annotation(self, s_obj):
        from rpython.annotator import model as annmodel
        return annmodel.SomeBool()

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.genop('gc__is_pinned', hop.args_v, resulttype=hop.r_result)

# ____________________________________________________________
# Annotation and specialization

# Support for collection.

class CollectEntry(ExtRegistryEntry):
    _about_ = gc.collect

    def compute_result_annotation(self, s_gen=None):
        from rpython.annotator import model as annmodel
        return annmodel.s_None

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        args_v = []
        if len(hop.args_s) == 1:
            args_v = hop.inputargs(lltype.Signed)
        return hop.genop('gc__collect', args_v, resulttype=hop.r_result)

class SetMaxHeapSizeEntry(ExtRegistryEntry):
    _about_ = set_max_heap_size

    def compute_result_annotation(self, s_nbytes):
        from rpython.annotator import model as annmodel
        return annmodel.s_None

    def specialize_call(self, hop):
        [v_nbytes] = hop.inputargs(lltype.Signed)
        hop.exception_cannot_occur()
        return hop.genop('gc_set_max_heap_size', [v_nbytes],
                         resulttype=lltype.Void)

def can_move(p):
    """Check if the GC object 'p' is at an address that can move.
    Must not be called with None.  With non-moving GCs, it is always False.
    With some moving GCs like the SemiSpace GC, it is always True.
    With other moving GCs like the MiniMark GC, it can be True for some
    time, then False for the same object, when we are sure that it won't
    move any more.
    """
    return True

class CanMoveEntry(ExtRegistryEntry):
    _about_ = can_move

    def compute_result_annotation(self, s_p):
        from rpython.annotator import model as annmodel
        return annmodel.SomeBool()

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.genop('gc_can_move', hop.args_v, resulttype=hop.r_result)

def _make_sure_does_not_move(p):
    """'p' is a non-null GC object.  This (tries to) make sure that the
    object does not move any more, by forcing collections if needed.
    Warning: should ideally only be used with the minimark GC, and only
    on objects that are already a bit old, so have a chance to be
    already non-movable."""
    assert p
    if not we_are_translated():
        # for testing purpose
        return not _is_pinned(p)
    #
    if _is_pinned(p):
        # although a pinned object can't move we must return 'False'.  A pinned
        # object can be unpinned any time and becomes movable.
        return False
    i = -1
    while can_move(p):
        if i > 6:
            raise NotImplementedError("can't make object non-movable!")
        collect(i)
        i += 1
    return True

def needs_write_barrier(obj):
    """ We need to emit write barrier if the right hand of assignment
    is in nursery, used by the JIT for handling set*_gc(Const)
    """
    if not obj:
        return False
    # XXX returning can_move() here might acidentally work for the use
    # cases (see issue #2212), but this is not really safe.  Now we
    # just return True for any non-NULL pointer, and too bad for the
    # few extra 'cond_call_gc_wb'.  It could be improved e.g. to return
    # False if 'obj' is a static prebuilt constant, or if we're not
    # running incminimark...
    return True #can_move(obj)

def _heap_stats():
    raise NotImplementedError # can't be run directly

class DumpHeapEntry(ExtRegistryEntry):
    _about_ = _heap_stats

    def compute_result_annotation(self):
        from rpython.rtyper.llannotation import SomePtr
        from rpython.memory.gc.base import ARRAY_TYPEID_MAP
        return SomePtr(lltype.Ptr(ARRAY_TYPEID_MAP))

    def specialize_call(self, hop):
        hop.exception_is_here()
        return hop.genop('gc_heap_stats', [], resulttype=hop.r_result)


def copy_struct_item(source, dest, si, di):
    TP = lltype.typeOf(source).TO.OF
    i = 0
    while i < len(TP._names):
        setattr(dest[di], TP._names[i], getattr(source[si], TP._names[i]))
        i += 1

class CopyStructEntry(ExtRegistryEntry):
    _about_ = copy_struct_item

    def compute_result_annotation(self, s_source, s_dest, si, di):
        pass

    def specialize_call(self, hop):
        v_source, v_dest, v_si, v_di = hop.inputargs(hop.args_r[0],
                                                     hop.args_r[1],
                                                     lltype.Signed,
                                                     lltype.Signed)
        hop.exception_cannot_occur()
        TP = v_source.concretetype.TO.OF
        for name, TP in TP._flds.iteritems():
            c_name = hop.inputconst(lltype.Void, name)
            v_fld = hop.genop('getinteriorfield', [v_source, v_si, c_name],
                              resulttype=TP)
            hop.genop('setinteriorfield', [v_dest, v_di, c_name, v_fld])


@specialize.ll()
def copy_item(source, dest, si, di):
    TP = lltype.typeOf(source)
    if isinstance(TP.TO.OF, lltype.Struct):
        copy_struct_item(source, dest, si, di)
    else:
        dest[di] = source[si]

@specialize.memo()
def _contains_gcptr(TP):
    if not isinstance(TP, lltype.Struct):
        if isinstance(TP, lltype.Ptr) and TP.TO._gckind == 'gc':
            return True
        return False
    for TP in TP._flds.itervalues():
        if _contains_gcptr(TP):
            return True
    return False


@jit.oopspec('list.ll_arraycopy(source, dest, source_start, dest_start, length)')
@enforceargs(None, None, int, int, int)
@specialize.ll()
def ll_arraycopy(source, dest, source_start, dest_start, length):
    from rpython.rtyper.lltypesystem.lloperation import llop
    from rpython.rlib.objectmodel import keepalive_until_here

    # XXX: Hack to ensure that we get a proper effectinfo.write_descrs_arrays
    # and also, maybe, speed up very small cases
    if length <= 1:
        if length == 1:
            copy_item(source, dest, source_start, dest_start)
        return

    # supports non-overlapping copies only
    if not we_are_translated():
        if source == dest:
            assert (source_start + length <= dest_start or
                    dest_start + length <= source_start)

    TP = lltype.typeOf(source).TO
    assert TP == lltype.typeOf(dest).TO
    if _contains_gcptr(TP.OF):
        # perform a write barrier that copies necessary flags from
        # source to dest
        if not llop.gc_writebarrier_before_copy(lltype.Bool, source, dest,
                                                source_start, dest_start,
                                                length):
            # if the write barrier is not supported, copy by hand
            i = 0
            while i < length:
                copy_item(source, dest, i + source_start, i + dest_start)
                i += 1
            return
    source_addr = llmemory.cast_ptr_to_adr(source)
    dest_addr   = llmemory.cast_ptr_to_adr(dest)
    cp_source_addr = (source_addr + llmemory.itemoffsetof(TP, 0) +
                      llmemory.sizeof(TP.OF) * source_start)
    cp_dest_addr = (dest_addr + llmemory.itemoffsetof(TP, 0) +
                    llmemory.sizeof(TP.OF) * dest_start)

    llmemory.raw_memcopy(cp_source_addr, cp_dest_addr,
                         llmemory.sizeof(TP.OF) * length)
    keepalive_until_here(source)
    keepalive_until_here(dest)


@jit.oopspec('rgc.ll_shrink_array(p, smallerlength)')
@enforceargs(None, int)
@specialize.ll()
def ll_shrink_array(p, smallerlength):
    from rpython.rtyper.lltypesystem.lloperation import llop
    from rpython.rlib.objectmodel import keepalive_until_here

    if llop.shrink_array(lltype.Bool, p, smallerlength):
        return p    # done by the GC
    # XXX we assume for now that the type of p is GcStruct containing a
    # variable array, with no further pointers anywhere, and exactly one
    # field in the fixed part -- like STR and UNICODE.

    TP = lltype.typeOf(p).TO
    newp = lltype.malloc(TP, smallerlength)

    assert len(TP._names) == 2
    field = getattr(p, TP._names[0])
    setattr(newp, TP._names[0], field)

    ARRAY = getattr(TP, TP._arrayfld)
    offset = (llmemory.offsetof(TP, TP._arrayfld) +
              llmemory.itemoffsetof(ARRAY, 0))
    source_addr = llmemory.cast_ptr_to_adr(p) + offset
    dest_addr = llmemory.cast_ptr_to_adr(newp) + offset
    llmemory.raw_memcopy(source_addr, dest_addr,
                         llmemory.sizeof(ARRAY.OF) * smallerlength)

    keepalive_until_here(p)
    keepalive_until_here(newp)
    return newp

@jit.dont_look_inside
@specialize.ll()
def ll_arrayclear(p):
    # Equivalent to memset(array, 0).  Only for GcArray(primitive-type) for now.
    from rpython.rlib.objectmodel import keepalive_until_here

    length = len(p)
    ARRAY = lltype.typeOf(p).TO
    offset = llmemory.itemoffsetof(ARRAY, 0)
    dest_addr = llmemory.cast_ptr_to_adr(p) + offset
    llmemory.raw_memclear(dest_addr, llmemory.sizeof(ARRAY.OF) * length)
    keepalive_until_here(p)


def no_release_gil(func):
    func._dont_inline_ = True
    func._no_release_gil_ = True
    return func

def no_collect(func):
    func._dont_inline_ = True
    func._gc_no_collect_ = True
    return func

def must_be_light_finalizer(func):
    """Mark a __del__ method as being a destructor, calling only a limited
    set of operations.  See pypy/doc/discussion/finalizer-order.rst.  

    If you use the same decorator on a class, this class and all its
    subclasses are only allowed to have __del__ methods which are
    similarly decorated (or no __del__ at all).  It prevents a class
    hierarchy from having destructors in some parent classes, which are
    overridden in subclasses with (non-light, old-style) finalizers.  
    (This case is the original motivation for FinalizerQueue.)
    """
    func._must_be_light_finalizer_ = True
    return func


class FinalizerQueue(object):
    """A finalizer queue.  See pypy/doc/discussion/finalizer-order.rst.
    Note: only works with the framework GCs (like minimark).  It is
    ignored with Boehm or with refcounting (used by tests).
    """
    # Must be subclassed, and the subclass needs these attributes:
    #
    #    Class:
    #        the class (or base class) of finalized objects
    #
    #    def finalizer_trigger(self):
    #        called to notify that new items have been put in the queue

    def _freeze_(self):
        return True

    @specialize.arg(0)
    @jit.dont_look_inside
    def next_dead(self):
        if we_are_translated():
            from rpython.rtyper.lltypesystem.lloperation import llop
            from rpython.rtyper.rclass import OBJECTPTR
            from rpython.rtyper.annlowlevel import cast_base_ptr_to_instance
            tag = FinalizerQueue._get_tag(self)
            ptr = llop.gc_fq_next_dead(OBJECTPTR, tag)
            return cast_base_ptr_to_instance(self.Class, ptr)
        try:
            return self._queue.popleft()
        except (AttributeError, IndexError):
            return None

    @specialize.arg(0)
    @jit.dont_look_inside
    def register_finalizer(self, obj):
        assert isinstance(obj, self.Class)
        if we_are_translated():
            from rpython.rtyper.lltypesystem.lloperation import llop
            from rpython.rtyper.rclass import OBJECTPTR
            from rpython.rtyper.annlowlevel import cast_instance_to_base_ptr
            tag = FinalizerQueue._get_tag(self)
            ptr = cast_instance_to_base_ptr(obj)
            llop.gc_fq_register(lltype.Void, tag, ptr)
            return
        else:
            self._untranslated_register_finalizer(obj)

    @not_rpython
    def _get_tag(self):
        "special-cased below"

    def _reset(self):
        import collections
        self._weakrefs = set()
        self._queue = collections.deque()

    def _already_registered(self, obj):
        return hasattr(obj, '__enable_del_for_id')

    def _untranslated_register_finalizer(self, obj):
        assert not self._already_registered(obj)

        if not hasattr(self, '_queue'):
            self._reset()

        # Fetch and check the type of 'obj'
        objtyp = obj.__class__
        assert isinstance(objtyp, type), (
            "%r: to run register_finalizer() untranslated, "
            "the object's class must be new-style" % (obj,))
        assert hasattr(obj, '__dict__'), (
            "%r: to run register_finalizer() untranslated, "
            "the object must have a __dict__" % (obj,))
        assert (not hasattr(obj, '__slots__') or
                type(obj).__slots__ == () or
                type(obj).__slots__ == ('__weakref__',)), (
            "%r: to run register_finalizer() untranslated, "
            "the object must not have __slots__" % (obj,))

        # The first time, patch the method __del__ of the class, if
        # any, so that we can disable it on the original 'obj' and
        # enable it only on the 'newobj'
        _fq_patch_class(objtyp)

        # Build a new shadow object with the same class and dict
        newobj = object.__new__(objtyp)
        obj.__dict__ = obj.__dict__.copy() #PyPy: break the dict->obj dependency
        newobj.__dict__ = obj.__dict__

        # A callback that is invoked when (or after) 'obj' is deleted;
        # 'newobj' is still kept alive here
        def callback(wr):
            self._weakrefs.discard(wr)
            self._queue.append(newobj)
            self.finalizer_trigger()

        import weakref
        wr = weakref.ref(obj, callback)
        self._weakrefs.add(wr)

        # Disable __del__ on the original 'obj' and enable it only on
        # the 'newobj'.  Use id() and not a regular reference, because
        # that would make a cycle between 'newobj' and 'obj.__dict__'
        # (which is 'newobj.__dict__' too).
        setattr(obj, '__enable_del_for_id', id(newobj))


def _fq_patch_class(Cls):
    if Cls in _fq_patched_classes:
        return
    if '__del__' in Cls.__dict__:
        def __del__(self):
            if not we_are_translated():
                try:
                    if getattr(self, '__enable_del_for_id') != id(self):
                        return
                except AttributeError:
                    pass
            original_del(self)
        original_del = Cls.__del__
        Cls.__del__ = __del__
        _fq_patched_classes.add(Cls)
    for BaseCls in Cls.__bases__:
        _fq_patch_class(BaseCls)

_fq_patched_classes = set()

class FqTagEntry(ExtRegistryEntry):
    _about_ = FinalizerQueue._get_tag.im_func

    def compute_result_annotation(self, s_fq):
        assert s_fq.is_constant()
        fq = s_fq.const
        s_func = self.bookkeeper.immutablevalue(fq.finalizer_trigger)
        self.bookkeeper.emulate_pbc_call(self.bookkeeper.position_key,
                                         s_func, [])
        if not hasattr(fq, '_fq_tag'):
            fq._fq_tag = CDefinedIntSymbolic(
                '0 /*FinalizerQueue TAG for %s*/' % fq.__class__.__name__,
                default=fq)
        return self.bookkeeper.immutablevalue(fq._fq_tag)

    def specialize_call(self, hop):
        from rpython.rtyper.rclass import InstanceRepr
        translator = hop.rtyper.annotator.translator
        fq = hop.args_s[0].const
        graph = translator._graphof(fq.finalizer_trigger.im_func)
        InstanceRepr.check_graph_of_del_does_not_call_too_much(hop.rtyper,
                                                               graph)
        hop.exception_cannot_occur()
        return hop.inputconst(lltype.Signed, hop.s_result.const)

@jit.dont_look_inside
@specialize.argtype(0)
def may_ignore_finalizer(obj):
    """Optimization hint: says that it is valid for any finalizer
    for 'obj' to be ignored, depending on the GC."""
    from rpython.rtyper.lltypesystem.lloperation import llop
    llop.gc_ignore_finalizer(lltype.Void, obj)

@jit.dont_look_inside
def move_out_of_nursery(obj):
    """ Returns another object which is a copy of obj; but at any point
        (either now or in the future) the returned object might suddenly
        become identical to the one returned.

        NOTE: Only use for immutable objects!
    """
    pass

class MoveOutOfNurseryEntry(ExtRegistryEntry):
    _about_ = move_out_of_nursery

    def compute_result_annotation(self, s_obj):
        return s_obj

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.genop('gc_move_out_of_nursery', hop.args_v, resulttype=hop.r_result)

# ____________________________________________________________


@not_rpython
def get_rpy_roots():
    # Return the 'roots' from the GC.
    # The gc typically returns a list that ends with a few NULL_GCREFs.
    return [_GcRef(x) for x in gc.get_objects()]

@not_rpython
def get_rpy_referents(gcref):
    x = gcref._x
    if isinstance(x, list):
        d = x
    elif isinstance(x, dict):
        d = x.keys() + x.values()
    else:
        d = []
        if hasattr(x, '__dict__'):
            d = x.__dict__.values()
        if hasattr(type(x), '__slots__'):
            for slot in type(x).__slots__:
                try:
                    d.append(getattr(x, slot))
                except AttributeError:
                    pass
    # discard objects that are too random or that are _freeze_=True
    return [_GcRef(x) for x in d if _keep_object(x)]

def _keep_object(x):
    if isinstance(x, type) or type(x) is types.ClassType:
        return False      # don't keep any type
    if isinstance(x, (list, dict, str)):
        return True       # keep lists and dicts and strings
    if hasattr(x, '_freeze_'):
        return False
    return type(x).__module__ != '__builtin__'   # keep non-builtins

def add_memory_pressure(estimate):
    """Add memory pressure for OpaquePtrs."""
    pass

class AddMemoryPressureEntry(ExtRegistryEntry):
    _about_ = add_memory_pressure

    def compute_result_annotation(self, s_nbytes):
        from rpython.annotator import model as annmodel
        return annmodel.s_None

    def specialize_call(self, hop):
        [v_size] = hop.inputargs(lltype.Signed)
        hop.exception_cannot_occur()
        return hop.genop('gc_add_memory_pressure', [v_size],
                         resulttype=lltype.Void)


@not_rpython
def get_rpy_memory_usage(gcref):
    # approximate implementation using CPython's type info
    Class = type(gcref._x)
    size = Class.__basicsize__
    if Class.__itemsize__ > 0:
        size += Class.__itemsize__ * len(gcref._x)
    return size

@not_rpython
def get_rpy_type_index(gcref):
    from rpython.rlib.rarithmetic import intmask
    Class = gcref._x.__class__
    return intmask(id(Class))

def cast_gcref_to_int(gcref):
    # This is meant to be used on cast_instance_to_gcref results.
    # Don't use this on regular gcrefs obtained e.g. with
    # lltype.cast_opaque_ptr().
    if we_are_translated():
        return lltype.cast_ptr_to_int(gcref)
    else:
        return id(gcref._x)

@not_rpython
def dump_rpy_heap(fd):
    raise NotImplementedError

@not_rpython
def get_typeids_z():
    raise NotImplementedError

@not_rpython
def get_typeids_list():
    raise NotImplementedError

@not_rpython
def has_gcflag_extra():
    return True
has_gcflag_extra._subopnum = 1

_gcflag_extras = set()

@not_rpython
def get_gcflag_extra(gcref):
    assert gcref   # not NULL!
    return gcref in _gcflag_extras
get_gcflag_extra._subopnum = 2

@not_rpython
def toggle_gcflag_extra(gcref):
    assert gcref   # not NULL!
    try:
        _gcflag_extras.remove(gcref)
    except KeyError:
        _gcflag_extras.add(gcref)
toggle_gcflag_extra._subopnum = 3

def assert_no_more_gcflags():
    if not we_are_translated():
        assert not _gcflag_extras

ARRAY_OF_CHAR = lltype.Array(lltype.Char)
NULL_GCREF = lltype.nullptr(llmemory.GCREF.TO)

class _GcRef(object):
    # implementation-specific: there should not be any after translation
    __slots__ = ['_x', '_handle']
    _TYPE = llmemory.GCREF
    def __init__(self, x):
        self._x = x
    def __hash__(self):
        return object.__hash__(self._x)
    def __eq__(self, other):
        if isinstance(other, lltype._ptr):
            assert other == NULL_GCREF, (
                "comparing a _GcRef with a non-NULL lltype ptr")
            return False
        assert isinstance(other, _GcRef)
        return self._x is other._x
    def __ne__(self, other):
        return not self.__eq__(other)
    def __repr__(self):
        return "_GcRef(%r)" % (self._x, )
    def _freeze_(self):
        raise Exception("instances of rlib.rgc._GcRef cannot be translated")

def cast_instance_to_gcref(x):
    # Before translation, casts an RPython instance into a _GcRef.
    # After translation, it is a variant of cast_object_to_ptr(GCREF).
    if we_are_translated():
        from rpython.rtyper import annlowlevel
        x = annlowlevel.cast_instance_to_base_ptr(x)
        return lltype.cast_opaque_ptr(llmemory.GCREF, x)
    else:
        return _GcRef(x)
cast_instance_to_gcref._annspecialcase_ = 'specialize:argtype(0)'

def try_cast_gcref_to_instance(Class, gcref):
    # Before translation, unwraps the RPython instance contained in a _GcRef.
    # After translation, it is a type-check performed by the GC.
    if we_are_translated():
        from rpython.rtyper.rclass import OBJECTPTR, ll_isinstance
        from rpython.rtyper.annlowlevel import cast_base_ptr_to_instance
        if _is_rpy_instance(gcref):
            objptr = lltype.cast_opaque_ptr(OBJECTPTR, gcref)
            if objptr.typeptr:   # may be NULL, e.g. in rdict's dummykeyobj
                clsptr = _get_llcls_from_cls(Class)
                if ll_isinstance(objptr, clsptr):
                    return cast_base_ptr_to_instance(Class, objptr)
        return None
    else:
        if isinstance(gcref._x, Class):
            return gcref._x
        return None
try_cast_gcref_to_instance._annspecialcase_ = 'specialize:arg(0)'

_ffi_cache = None
def _fetch_ffi():
    global _ffi_cache
    if _ffi_cache is None:
        try:
            import _cffi_backend
            _ffi_cache = _cffi_backend.FFI()
        except (ImportError, AttributeError):
            import py
            py.test.skip("need CFFI >= 1.0")
    return _ffi_cache

@jit.dont_look_inside
def hide_nonmovable_gcref(gcref):
    from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
    if we_are_translated():
        assert lltype.typeOf(gcref) == llmemory.GCREF
        assert not can_move(gcref)
        return rffi.cast(llmemory.Address, gcref)
    else:
        assert isinstance(gcref, _GcRef)
        x = gcref._x
        ffi = _fetch_ffi()
        if not hasattr(x, '__handle'):
            x.__handle = ffi.new_handle(x)
        addr = int(ffi.cast("intptr_t", x.__handle))
        return rffi.cast(llmemory.Address, addr)

@jit.dont_look_inside
def reveal_gcref(addr):
    from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
    assert lltype.typeOf(addr) == llmemory.Address
    if we_are_translated():
        return rffi.cast(llmemory.GCREF, addr)
    else:
        addr = rffi.cast(lltype.Signed, addr)
        if addr == 0:
            return lltype.nullptr(llmemory.GCREF.TO)
        ffi = _fetch_ffi()
        x = ffi.from_handle(ffi.cast("void *", addr))
        return _GcRef(x)

# ------------------- implementation -------------------

_cache_s_list_of_gcrefs = None

def s_list_of_gcrefs():
    global _cache_s_list_of_gcrefs
    if _cache_s_list_of_gcrefs is None:
        from rpython.annotator import model as annmodel
        from rpython.rtyper.llannotation import SomePtr
        from rpython.annotator.listdef import ListDef
        s_gcref = SomePtr(llmemory.GCREF)
        _cache_s_list_of_gcrefs = annmodel.SomeList(
            ListDef(None, s_gcref, mutated=True, resized=False))
    return _cache_s_list_of_gcrefs

class Entry(ExtRegistryEntry):
    _about_ = get_rpy_roots
    def compute_result_annotation(self):
        return s_list_of_gcrefs()
    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.genop('gc_get_rpy_roots', [], resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = get_rpy_referents

    def compute_result_annotation(self, s_gcref):
        from rpython.rtyper.llannotation import SomePtr
        assert SomePtr(llmemory.GCREF).contains(s_gcref)
        return s_list_of_gcrefs()

    def specialize_call(self, hop):
        vlist = hop.inputargs(hop.args_r[0])
        hop.exception_cannot_occur()
        return hop.genop('gc_get_rpy_referents', vlist,
                         resulttype=hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = get_rpy_memory_usage
    def compute_result_annotation(self, s_gcref):
        from rpython.annotator import model as annmodel
        return annmodel.SomeInteger()
    def specialize_call(self, hop):
        vlist = hop.inputargs(hop.args_r[0])
        hop.exception_cannot_occur()
        return hop.genop('gc_get_rpy_memory_usage', vlist,
                         resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = get_rpy_type_index
    def compute_result_annotation(self, s_gcref):
        from rpython.annotator import model as annmodel
        return annmodel.SomeInteger()
    def specialize_call(self, hop):
        vlist = hop.inputargs(hop.args_r[0])
        hop.exception_cannot_occur()
        return hop.genop('gc_get_rpy_type_index', vlist,
                         resulttype = hop.r_result)

@not_rpython
def _is_rpy_instance(gcref):
    raise NotImplementedError

@not_rpython
def _get_llcls_from_cls(Class):
    raise NotImplementedError

class Entry(ExtRegistryEntry):
    _about_ = _is_rpy_instance
    def compute_result_annotation(self, s_gcref):
        from rpython.annotator import model as annmodel
        return annmodel.SomeBool()
    def specialize_call(self, hop):
        vlist = hop.inputargs(hop.args_r[0])
        hop.exception_cannot_occur()
        return hop.genop('gc_is_rpy_instance', vlist,
                         resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = _get_llcls_from_cls
    def compute_result_annotation(self, s_Class):
        from rpython.rtyper.llannotation import SomePtr
        from rpython.rtyper.rclass import CLASSTYPE
        assert s_Class.is_constant()
        return SomePtr(CLASSTYPE)

    def specialize_call(self, hop):
        from rpython.rtyper.rclass import getclassrepr, CLASSTYPE
        from rpython.flowspace.model import Constant
        Class = hop.args_s[0].const
        classdef = hop.rtyper.annotator.bookkeeper.getuniqueclassdef(Class)
        classrepr = getclassrepr(hop.rtyper, classdef)
        vtable = classrepr.getvtable()
        assert lltype.typeOf(vtable) == CLASSTYPE
        hop.exception_cannot_occur()
        return Constant(vtable, concretetype=CLASSTYPE)

class Entry(ExtRegistryEntry):
    _about_ = dump_rpy_heap
    def compute_result_annotation(self, s_fd):
        from rpython.annotator.model import s_Bool
        return s_Bool
    def specialize_call(self, hop):
        vlist = hop.inputargs(lltype.Signed)
        hop.exception_is_here()
        return hop.genop('gc_dump_rpy_heap', vlist, resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = get_typeids_z

    def compute_result_annotation(self):
        from rpython.rtyper.llannotation import SomePtr
        return SomePtr(lltype.Ptr(ARRAY_OF_CHAR))

    def specialize_call(self, hop):
        hop.exception_is_here()
        return hop.genop('gc_typeids_z', [], resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = get_typeids_list

    def compute_result_annotation(self):
        from rpython.rtyper.llannotation import SomePtr
        from rpython.rtyper.lltypesystem import llgroup
        return SomePtr(lltype.Ptr(lltype.Array(llgroup.HALFWORD)))

    def specialize_call(self, hop):
        hop.exception_is_here()
        return hop.genop('gc_typeids_list', [], resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = (has_gcflag_extra, get_gcflag_extra, toggle_gcflag_extra)
    def compute_result_annotation(self, s_arg=None):
        from rpython.annotator.model import s_Bool
        return s_Bool
    def specialize_call(self, hop):
        subopnum = self.instance._subopnum
        vlist = [hop.inputconst(lltype.Signed, subopnum)]
        vlist += hop.inputargs(*hop.args_r)
        hop.exception_cannot_occur()
        return hop.genop('gc_gcflag_extra', vlist, resulttype = hop.r_result)

def lltype_is_gc(TP):
    return getattr(getattr(TP, "TO", None), "_gckind", "?") == 'gc'

def register_custom_trace_hook(TP, lambda_func):
    """ This function does not do anything, but called from any annotated
    place, will tell that "func" is used to trace GC roots inside any instance
    of the type TP.  The func must be specified as "lambda: func" in this
    call, for internal reasons.  Note that the func will be automatically
    specialized on the 'callback' argument value.  Example:

        def customtrace(gc, obj, callback, arg):
            gc._trace_callback(callback, arg, obj + offset_of_x)
        lambda_customtrace = lambda: customtrace
    """

@specialize.ll()
def ll_writebarrier(gc_obj):
    """Use together with custom tracers.  When you update some object pointer
    stored in raw memory, you must call this function on 'gc_obj', which must
    be the object of type TP with the custom tracer (*not* the value stored!).
    This makes sure that the custom hook will be called again."""
    from rpython.rtyper.lltypesystem.lloperation import llop
    llop.gc_writebarrier(lltype.Void, gc_obj)

class RegisterGcTraceEntry(ExtRegistryEntry):
    _about_ = register_custom_trace_hook

    def compute_result_annotation(self, s_tp, s_lambda_func):
        pass

    def specialize_call(self, hop):
        TP = hop.args_s[0].const
        lambda_func = hop.args_s[1].const
        hop.exception_cannot_occur()
        hop.rtyper.custom_trace_funcs.append((TP, lambda_func()))

def register_custom_light_finalizer(TP, lambda_func):
    """ This function does not do anything, but called from any annotated
    place, will tell that "func" is used as a lightweight finalizer for TP.
    The func must be specified as "lambda: func" in this call, for internal
    reasons.
    """

@specialize.arg(0)
def do_get_objects(callback):
    """ Get all the objects that satisfy callback(gcref) -> obj
    """
    roots = get_rpy_roots()
    if not roots:      # is always None on translations using Boehm or None GCs
        return []
    roots = [gcref for gcref in roots if gcref]
    result_w = []
    #
    if not we_are_translated():   # fast path before translation
        seen = set()
        while roots:
            gcref = roots.pop()
            if gcref not in seen:
                seen.add(gcref)
                w_obj = callback(gcref)
                if w_obj is not None:
                    result_w.append(w_obj)
                roots.extend(get_rpy_referents(gcref))
        return result_w
    #
    pending = roots[:]
    while pending:
        gcref = pending.pop()
        if not get_gcflag_extra(gcref):
            toggle_gcflag_extra(gcref)
            w_obj = callback(gcref)
            if w_obj is not None:
                result_w.append(w_obj)
            pending.extend(get_rpy_referents(gcref))
    clear_gcflag_extra(roots)
    assert_no_more_gcflags()
    return result_w

class RegisterCustomLightFinalizer(ExtRegistryEntry):
    _about_ = register_custom_light_finalizer

    def compute_result_annotation(self, s_tp, s_lambda_func):
        pass

    def specialize_call(self, hop):
        from rpython.rtyper.llannotation import SomePtr
        TP = hop.args_s[0].const
        lambda_func = hop.args_s[1].const
        ll_func = lambda_func()
        args_s = [SomePtr(lltype.Ptr(TP))]
        funcptr = hop.rtyper.annotate_helper_fn(ll_func, args_s)
        hop.exception_cannot_occur()
        lltype.attachRuntimeTypeInfo(TP, destrptr=funcptr)

def clear_gcflag_extra(fromlist):
    pending = fromlist[:]
    while pending:
        gcref = pending.pop()
        if get_gcflag_extra(gcref):
            toggle_gcflag_extra(gcref)
            pending.extend(get_rpy_referents(gcref))

all_typeids = {}
        
def get_typeid(obj):
    raise Exception("does not work untranslated")

class GetTypeidEntry(ExtRegistryEntry):
    _about_ = get_typeid

    def compute_result_annotation(self, s_obj):
        from rpython.annotator import model as annmodel
        return annmodel.SomeInteger()

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.genop('gc_gettypeid', hop.args_v, resulttype=lltype.Signed)

# ____________________________________________________________


class _rawptr_missing_item(object):
    pass
_rawptr_missing_item = _rawptr_missing_item()


class _ResizableListSupportingRawPtr(list):
    """Calling this class is a no-op after translation.

    Before translation, it returns a new instance of
    _ResizableListSupportingRawPtr, on which
    rgc.nonmoving_raw_ptr_for_resizable_list() might be
    used if needed.  For now, only supports lists of chars.
    """
    __slots__ = ('_raw_items',)   # either None or a rffi.CCHARP

    def __init__(self, lst):
        self._raw_items = None
        self.__from_list(lst)

    def __resize(self):
        """Called before an operation changes the size of the list"""
        if self._raw_items is not None:
            list.__init__(self, self.__as_list())
            self._raw_items = None

    def __from_list(self, lst):
        """Initialize the list from a copy of the list 'lst'."""
        assert isinstance(lst, list)
        for x in lst:
            assert isinstance(x, str) and len(x) == 1
        if self is lst:
            return
        if len(self) != len(lst):
            self.__resize()
        if self._raw_items is None:
            list.__init__(self, lst)
        else:
            assert len(self) == self._raw_items._obj.getlength() == len(lst)
            for i in range(len(self)):
                self._raw_items[i] = lst[i]

    def __as_list(self):
        """Return a list (the same or a different one) which contains the
        items in the regular way."""
        if self._raw_items is None:
            return self
        length = self._raw_items._obj.getlength()
        assert length == len(self)
        return [self._raw_items[i] for i in range(length)]

    def __getitem__(self, index):
        if self._raw_items is None:
            return list.__getitem__(self, index)
        if index < 0:
            index += len(self)
        if not (0 <= index < len(self)):
            raise IndexError
        return self._raw_items[index]

    def __setitem__(self, index, new):
        if self._raw_items is None:
            return list.__setitem__(self, index, new)
        if index < 0:
            index += len(self)
        if not (0 <= index < len(self)):
            raise IndexError
        self._raw_items[index] = new

    def __delitem__(self, index):
        self.__resize()
        list.__delitem__(self, index)

    def __getslice__(self, i, j):
        return list.__getslice__(self.__as_list(), i, j)

    def __setslice__(self, i, j, new):
        lst = self.__as_list()
        list.__setslice__(lst, i, j, new)
        self.__from_list(lst)

    def __delslice__(self, i, j):
        lst = self.__as_list()
        list.__delslice__(lst, i, j)
        self.__from_list(lst)

    def __iter__(self):
        try:
            i = 0
            while True:
                yield self[i]
                i += 1
        except IndexError:
            pass

    def __reversed__(self):
        i = len(self)
        while i > 0:
            i -= 1
            yield self[i]

    def __contains__(self, item):
        return list.__contains__(self.__as_list(), item)

    def __add__(self, other):
        if isinstance(other, _ResizableListSupportingRawPtr):
            other = other.__as_list()
        return list.__add__(self.__as_list(), other)

    def __radd__(self, other):
        if isinstance(other, _ResizableListSupportingRawPtr):
            other = other.__as_list()
        return list.__add__(other, self.__as_list())

    def __iadd__(self, other):
        self.__resize()
        return list.__iadd__(self, other)

    def __eq__(self, other):
        return list.__eq__(self.__as_list(), other)
    def __ne__(self, other):
        return list.__ne__(self.__as_list(), other)
    def __ge__(self, other):
        return list.__ge__(self.__as_list(), other)
    def __gt__(self, other):
        return list.__gt__(self.__as_list(), other)
    def __le__(self, other):
        return list.__le__(self.__as_list(), other)
    def __lt__(self, other):
        return list.__lt__(self.__as_list(), other)

    def __mul__(self, other):
        return list.__mul__(self.__as_list(), other)

    def __rmul__(self, other):
        return list.__mul__(self.__as_list(), other)

    def __imul__(self, other):
        self.__resize()
        return list.__imul__(self, other)

    def __repr__(self):
        return '_ResizableListSupportingRawPtr(%s)' % (
            list.__repr__(self.__as_list()),)

    def append(self, object):
        self.__resize()
        return list.append(self, object)

    def count(self, value):
        return list.count(self.__as_list(), value)

    def extend(self, iterable):
        self.__resize()
        return list.extend(self, iterable)

    def index(self, value, *start_stop):
        return list.index(self.__as_list(), value, *start_stop)

    def insert(self, index, object):
        self.__resize()
        return list.insert(self, index, object)

    def pop(self, *opt_index):
        self.__resize()
        return list.pop(self, *opt_index)

    def remove(self, value):
        self.__resize()
        return list.remove(self, value)

    def reverse(self):
        lst = self.__as_list()
        list.reverse(lst)
        self.__from_list(lst)

    def sort(self, *args, **kwds):
        lst = self.__as_list()
        list.sort(lst, *args, **kwds)
        self.__from_list(lst)

    def _nonmoving_raw_ptr_for_resizable_list(self):
        if self._raw_items is None:
            existing_items = list(self)
            from rpython.rtyper.lltypesystem import lltype, rffi
            self._raw_items = lltype.malloc(rffi.CCHARP.TO, len(self),
                                           flavor='raw', immortal=True)
            self.__from_list(existing_items)
            assert self._raw_items is not None
        return self._raw_items

def resizable_list_supporting_raw_ptr(lst):
    return _ResizableListSupportingRawPtr(lst)

def nonmoving_raw_ptr_for_resizable_list(lst):
    assert isinstance(lst, _ResizableListSupportingRawPtr)
    return lst._nonmoving_raw_ptr_for_resizable_list()


def _check_resizable_list_of_chars(s_list):
    from rpython.annotator import model as annmodel
    from rpython.rlib import debug
    if annmodel.s_None.contains(s_list):
        return    # "None", will likely be generalized later
    if not isinstance(s_list, annmodel.SomeList):
        raise Exception("not a list, got %r" % (s_list,))
    if not isinstance(s_list.listdef.listitem.s_value,
                      (annmodel.SomeChar, annmodel.SomeImpossibleValue)):
        raise debug.NotAListOfChars
    s_list.listdef.resize()    # must be resizable

class Entry(ExtRegistryEntry):
    _about_ = resizable_list_supporting_raw_ptr

    def compute_result_annotation(self, s_list):
        _check_resizable_list_of_chars(s_list)
        return s_list

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.inputarg(hop.args_r[0], 0)

class Entry(ExtRegistryEntry):
    _about_ = nonmoving_raw_ptr_for_resizable_list

    def compute_result_annotation(self, s_list):
        from rpython.rtyper.lltypesystem import lltype, rffi
        from rpython.rtyper.llannotation import SomePtr
        _check_resizable_list_of_chars(s_list)
        return SomePtr(rffi.CCHARP)

    def specialize_call(self, hop):
        v_list = hop.inputarg(hop.args_r[0], 0)
        hop.exception_cannot_occur()   # ignoring MemoryError
        return hop.gendirectcall(ll_nonmovable_raw_ptr_for_resizable_list,
                                 v_list)

@jit.dont_look_inside
def ll_nonmovable_raw_ptr_for_resizable_list(ll_list):
    """
    WARNING: dragons ahead.
    Return the address of the internal char* buffer of 'll_list', which
    must be a resizable list of chars.

    This makes sure that the list items are non-moving, if necessary by
    first copying the GcArray inside 'll_list.items' outside the GC
    nursery.  The returned 'char *' pointer is guaranteed to be valid
    until one of these occurs:

       * 'll_list' gets garbage-collected; or
       * you do an operation on 'll_list' that changes its size.
    """
    from rpython.rtyper.lltypesystem import lltype, rffi
    array = ll_list.items
    if can_move(array):
        length = ll_list.length
        new_array = lltype.malloc(lltype.typeOf(ll_list).TO.items.TO, length,
                                  nonmovable=True)
        ll_arraycopy(array, new_array, 0, 0, length)
        ll_list.items = new_array
        array = new_array
    ptr = lltype.direct_arrayitems(array)
    # ptr is a Ptr(FixedSizeArray(Char, 1)).  Cast it to a rffi.CCHARP
    return rffi.cast(rffi.CCHARP, ptr)

@jit.dont_look_inside
@no_collect
@specialize.ll()
def ll_write_final_null_char(s):
    """'s' is a low-level STR; writes a terminating NULL character after
    the other characters in 's'.  Warning, this only works because of
    the 'extra_item_after_alloc' hack inside the definition of STR.
    """
    from rpython.rtyper.lltypesystem import rffi
    PSTR = lltype.typeOf(s)
    assert has_final_null_char(PSTR) == 1
    n = llmemory.offsetof(PSTR.TO, 'chars')
    n += llmemory.itemoffsetof(PSTR.TO.chars, 0)
    n = llmemory.raw_malloc_usage(n)
    n += len(s.chars)
    # no GC operation from here!
    ptr = rffi.cast(rffi.CCHARP, s)
    ptr[n] = '\x00'

@specialize.memo()
def has_final_null_char(PSTR):
    return PSTR.TO.chars._hints.get('extra_item_after_alloc', 0)
