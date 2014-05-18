from __future__ import absolute_import

import gc
import types

from rpython.rlib import jit
from rpython.rlib.objectmodel import we_are_translated, enforceargs, specialize
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.lltypesystem import lltype, llmemory

# ____________________________________________________________
# General GC features

collect = gc.collect

def set_max_heap_size(nbytes):
    """Limit the heap size to n bytes.
    """
    pass

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
    if not we_are_translated():
        return
    i = 0
    while can_move(p):
        if i > 6:
            raise NotImplementedError("can't make object non-movable!")
        collect(i)
        i += 1

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

def malloc_nonmovable(TP, n=None, zero=False):
    """ Allocate a non-moving buffer or return nullptr.
    When running directly, will pretend that gc is always
    moving (might be configurable in a future)
    """
    return lltype.nullptr(TP)

class MallocNonMovingEntry(ExtRegistryEntry):
    _about_ = malloc_nonmovable

    def compute_result_annotation(self, s_TP, s_n=None, s_zero=None):
        # basically return the same as malloc
        from rpython.annotator.builtin import BUILTIN_ANALYZERS
        return BUILTIN_ANALYZERS[lltype.malloc](s_TP, s_n, s_zero=s_zero)

    def specialize_call(self, hop, i_zero=None):
        # XXX assume flavor and zero to be None by now
        assert hop.args_s[0].is_constant()
        vlist = [hop.inputarg(lltype.Void, arg=0)]
        opname = 'malloc_nonmovable'
        flags = {'flavor': 'gc'}
        if i_zero is not None:
            flags['zero'] = hop.args_s[i_zero].const
            nb_args = hop.nb_args - 1
        else:
            nb_args = hop.nb_args
        vlist.append(hop.inputconst(lltype.Void, flags))

        if nb_args == 2:
            vlist.append(hop.inputarg(lltype.Signed, arg=1))
            opname += '_varsize'

        hop.exception_cannot_occur()
        return hop.genop(opname, vlist, resulttype = hop.r_result.lowleveltype)

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

def no_release_gil(func):
    func._dont_inline_ = True
    func._no_release_gil_ = True
    return func

def no_collect(func):
    func._dont_inline_ = True
    func._gc_no_collect_ = True
    return func

def must_be_light_finalizer(func):
    func._must_be_light_finalizer_ = True
    return func

# ____________________________________________________________

def get_rpy_roots():
    "NOT_RPYTHON"
    # Return the 'roots' from the GC.
    # The gc typically returns a list that ends with a few NULL_GCREFs.
    return [_GcRef(x) for x in gc.get_objects()]

def get_rpy_referents(gcref):
    "NOT_RPYTHON"
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


def get_rpy_memory_usage(gcref):
    "NOT_RPYTHON"
    # approximate implementation using CPython's type info
    Class = type(gcref._x)
    size = Class.__basicsize__
    if Class.__itemsize__ > 0:
        size += Class.__itemsize__ * len(gcref._x)
    return size

def get_rpy_type_index(gcref):
    "NOT_RPYTHON"
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

def dump_rpy_heap(fd):
    "NOT_RPYTHON"
    raise NotImplementedError

def get_typeids_z():
    "NOT_RPYTHON"
    raise NotImplementedError

def has_gcflag_extra():
    "NOT_RPYTHON"
    return True
has_gcflag_extra._subopnum = 1

_gcflag_extras = set()

def get_gcflag_extra(gcref):
    "NOT_RPYTHON"
    assert gcref   # not NULL!
    return gcref in _gcflag_extras
get_gcflag_extra._subopnum = 2

def toggle_gcflag_extra(gcref):
    "NOT_RPYTHON"
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
    __slots__ = ['_x']
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
        from rpython.rtyper.lltypesystem.rclass import OBJECTPTR
        from rpython.rtyper.annlowlevel import cast_base_ptr_to_instance
        from rpython.rtyper.lltypesystem import rclass
        if _is_rpy_instance(gcref):
            objptr = lltype.cast_opaque_ptr(OBJECTPTR, gcref)
            if objptr.typeptr:   # may be NULL, e.g. in rdict's dummykeyobj
                clsptr = _get_llcls_from_cls(Class)
                if rclass.ll_isinstance(objptr, clsptr):
                    return cast_base_ptr_to_instance(Class, objptr)
        return None
    else:
        if isinstance(gcref._x, Class):
            return gcref._x
        return None
try_cast_gcref_to_instance._annspecialcase_ = 'specialize:arg(0)'

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

def _is_rpy_instance(gcref):
    "NOT_RPYTHON"
    raise NotImplementedError

def _get_llcls_from_cls(Class):
    "NOT_RPYTHON"
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
        from rpython.rtyper.lltypesystem import rclass
        assert s_Class.is_constant()
        return SomePtr(rclass.CLASSTYPE)

    def specialize_call(self, hop):
        from rpython.rtyper.rclass import getclassrepr
        from rpython.flowspace.model import Constant
        from rpython.rtyper.lltypesystem import rclass
        Class = hop.args_s[0].const
        classdef = hop.rtyper.annotator.bookkeeper.getuniqueclassdef(Class)
        classrepr = getclassrepr(hop.rtyper, classdef)
        vtable = classrepr.getvtable()
        assert lltype.typeOf(vtable) == rclass.CLASSTYPE
        hop.exception_cannot_occur()
        return Constant(vtable, concretetype=rclass.CLASSTYPE)

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
