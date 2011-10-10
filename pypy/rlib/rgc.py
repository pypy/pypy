import gc
import types

from pypy.rlib import jit
from pypy.rlib.objectmodel import we_are_translated, enforceargs, specialize
from pypy.rlib.nonconst import NonConstant
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype, llmemory

# ____________________________________________________________
# General GC features

collect = gc.collect

def set_max_heap_size(nbytes):
    """Limit the heap size to n bytes.
    So far only implemented by the Boehm GC and the semispace/generation GCs.
    """
    pass

# ____________________________________________________________
# Annotation and specialization

# Support for collection.

class CollectEntry(ExtRegistryEntry):
    _about_ = gc.collect

    def compute_result_annotation(self, s_gen=None):
        from pypy.annotation import model as annmodel
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
        from pypy.annotation import model as annmodel
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
        from pypy.annotation import model as annmodel
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
        from pypy.annotation import model as annmodel
        from pypy.rpython.memory.gc.base import ARRAY_TYPEID_MAP
        return annmodel.SomePtr(lltype.Ptr(ARRAY_TYPEID_MAP))

    def specialize_call(self, hop):
        from pypy.rpython.memory.gc.base import ARRAY_TYPEID_MAP
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
        from pypy.annotation.builtin import malloc
        return malloc(s_TP, s_n, s_zero=s_zero)

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

@jit.oopspec('list.ll_arraycopy(source, dest, source_start, dest_start, length)')
@specialize.ll()
@enforceargs(None, None, int, int, int)
def ll_arraycopy(source, dest, source_start, dest_start, length):
    from pypy.rpython.lltypesystem.lloperation import llop
    from pypy.rlib.objectmodel import keepalive_until_here

    # XXX: Hack to ensure that we get a proper effectinfo.write_descrs_arrays
    if NonConstant(False):
        dest[dest_start] = source[source_start]

    # supports non-overlapping copies only
    if not we_are_translated():
        if source == dest:
            assert (source_start + length <= dest_start or
                    dest_start + length <= source_start)

    TP = lltype.typeOf(source).TO
    assert TP == lltype.typeOf(dest).TO
    if isinstance(TP.OF, lltype.Ptr) and TP.OF.TO._gckind == 'gc':
        # perform a write barrier that copies necessary flags from
        # source to dest
        if not llop.gc_writebarrier_before_copy(lltype.Bool, source, dest,
                                                source_start, dest_start,
                                                length):
            # if the write barrier is not supported, copy by hand
            for i in range(length):
                dest[i + dest_start] = source[i + source_start]
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

def ll_shrink_array(p, smallerlength):
    from pypy.rpython.lltypesystem.lloperation import llop
    from pypy.rlib.objectmodel import keepalive_until_here

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
    source_addr = llmemory.cast_ptr_to_adr(p)    + offset
    dest_addr   = llmemory.cast_ptr_to_adr(newp) + offset
    llmemory.raw_memcopy(source_addr, dest_addr,
                         llmemory.sizeof(ARRAY.OF) * smallerlength)

    keepalive_until_here(p)
    keepalive_until_here(newp)
    return newp
ll_shrink_array._annspecialcase_ = 'specialize:ll'
ll_shrink_array._jit_look_inside_ = False

def no_collect(func):
    func._dont_inline_ = True
    func._gc_no_collect_ = True
    return func

# ____________________________________________________________

def get_rpy_roots():
    "NOT_RPYTHON"
    # Return the 'roots' from the GC.
    # This stub is not usable on top of CPython.
    # The gc typically returns a list that ends with a few NULL_GCREFs.
    raise NotImplementedError

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
    try:
        return not x._freeze_()   # don't keep any frozen object
    except AttributeError:
        return type(x).__module__ != '__builtin__'   # keep non-builtins
    except Exception:
        return False      # don't keep objects whose _freeze_() method explodes

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
    from pypy.rlib.rarithmetic import intmask
    Class = gcref._x.__class__
    return intmask(id(Class))

def cast_gcref_to_int(gcref):
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
        from pypy.rpython import annlowlevel
        x = annlowlevel.cast_instance_to_base_ptr(x)
        return lltype.cast_opaque_ptr(llmemory.GCREF, x)
    else:
        return _GcRef(x)
cast_instance_to_gcref._annspecialcase_ = 'specialize:argtype(0)'

def try_cast_gcref_to_instance(Class, gcref):
    # Before translation, unwraps the RPython instance contained in a _GcRef.
    # After translation, it is a type-check performed by the GC.
    if we_are_translated():
        from pypy.rpython.annlowlevel import base_ptr_lltype
        from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
        from pypy.rpython.lltypesystem import rclass
        if _is_rpy_instance(gcref):
            objptr = lltype.cast_opaque_ptr(base_ptr_lltype(), gcref)
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
        from pypy.annotation import model as annmodel
        from pypy.annotation.listdef import ListDef
        s_gcref = annmodel.SomePtr(llmemory.GCREF)
        _cache_s_list_of_gcrefs = annmodel.SomeList(
            ListDef(None, s_gcref, mutated=True, resized=False))
    return _cache_s_list_of_gcrefs

class Entry(ExtRegistryEntry):
    _about_ = get_rpy_roots
    def compute_result_annotation(self):
        return s_list_of_gcrefs()
    def specialize_call(self, hop):
        return hop.genop('gc_get_rpy_roots', [], resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = get_rpy_referents
    def compute_result_annotation(self, s_gcref):
        from pypy.annotation import model as annmodel
        assert annmodel.SomePtr(llmemory.GCREF).contains(s_gcref)
        return s_list_of_gcrefs()
    def specialize_call(self, hop):
        vlist = hop.inputargs(hop.args_r[0])
        return hop.genop('gc_get_rpy_referents', vlist,
                         resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = get_rpy_memory_usage
    def compute_result_annotation(self, s_gcref):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger()
    def specialize_call(self, hop):
        vlist = hop.inputargs(hop.args_r[0])
        return hop.genop('gc_get_rpy_memory_usage', vlist,
                         resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = get_rpy_type_index
    def compute_result_annotation(self, s_gcref):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger()
    def specialize_call(self, hop):
        vlist = hop.inputargs(hop.args_r[0])
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
        from pypy.annotation import model as annmodel
        return annmodel.SomeBool()
    def specialize_call(self, hop):
        vlist = hop.inputargs(hop.args_r[0])
        return hop.genop('gc_is_rpy_instance', vlist,
                         resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = _get_llcls_from_cls
    def compute_result_annotation(self, s_Class):
        from pypy.annotation import model as annmodel
        from pypy.rpython.lltypesystem import rclass
        assert s_Class.is_constant()
        return annmodel.SomePtr(rclass.CLASSTYPE)
    def specialize_call(self, hop):
        from pypy.rpython.rclass import getclassrepr
        from pypy.objspace.flow.model import Constant
        from pypy.rpython.lltypesystem import rclass
        Class = hop.args_s[0].const
        classdef = hop.rtyper.annotator.bookkeeper.getuniqueclassdef(Class)
        classrepr = getclassrepr(hop.rtyper, classdef)
        vtable = classrepr.getvtable()
        assert lltype.typeOf(vtable) == rclass.CLASSTYPE
        return Constant(vtable, concretetype=rclass.CLASSTYPE)

class Entry(ExtRegistryEntry):
    _about_ = dump_rpy_heap
    def compute_result_annotation(self, s_fd):
        from pypy.annotation.model import s_Bool
        return s_Bool
    def specialize_call(self, hop):
        vlist = hop.inputargs(lltype.Signed)
        hop.exception_is_here()
        return hop.genop('gc_dump_rpy_heap', vlist, resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = get_typeids_z
    def compute_result_annotation(self):
        from pypy.annotation.model import SomePtr
        return SomePtr(lltype.Ptr(ARRAY_OF_CHAR))
    def specialize_call(self, hop):
        hop.exception_is_here()
        return hop.genop('gc_typeids_z', [], resulttype = hop.r_result)
