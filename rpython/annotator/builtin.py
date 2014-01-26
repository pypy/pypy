"""
Built-in functions.
"""
import sys

from rpython.annotator.model import (
    SomeInteger, SomeObject, SomeChar, SomeBool, SomeString, SomeTuple, s_Bool,
    SomeUnicodeCodePoint, SomeFloat, unionof, SomeUnicodeString,
    SomePBC, SomeInstance, SomeDict, SomeList, SomeWeakRef, SomeIterator,
    SomeOrderedDict,
    SomeByteArray, annotation_to_lltype, lltype_to_annotation,
    ll_to_annotation, add_knowntypedata, s_ImpossibleValue,)
from rpython.rtyper.llannotation import SomeAddress
from rpython.annotator.bookkeeper import getbookkeeper
from rpython.annotator import description
from rpython.flowspace.model import Constant
import rpython.rlib.rarithmetic
import rpython.rlib.objectmodel

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

def constpropagate(func, args_s, s_result):
    """Returns s_result unless all args are constants, in which case the
    func() is called and a constant result is returned (it must be contained
    in s_result).
    """
    args = []
    for s in args_s:
        if not s.is_immutable_constant():
            return s_result
        args.append(s.const)
    try:
        realresult = func(*args)
    except (ValueError, OverflowError):
        # no possible answer for this precise input.  Be conservative
        # and keep the computation non-constant.  Example:
        # unichr(constant-that-doesn't-fit-16-bits) on platforms where
        # the underlying Python has sys.maxunicode == 0xffff.
        return s_result
    s_realresult = immutablevalue(realresult)
    if not s_result.contains(s_realresult):
        raise Exception("%s%r returned %r, which is not contained in %s" % (
            func, args, realresult, s_result))
    return s_realresult

BUILTIN_ANALYZERS = {}

def analyzer_for(func):
    def wrapped(ann_func):
        BUILTIN_ANALYZERS[func] = ann_func
        return func
    return wrapped

# ____________________________________________________________

def builtin_range(*args):
    s_step = immutablevalue(1)
    if len(args) == 1:
        s_start = immutablevalue(0)
        s_stop = args[0]
    elif len(args) == 2:
        s_start, s_stop = args
    elif len(args) == 3:
        s_start, s_stop = args[:2]
        s_step = args[2]
    else:
        raise Exception, "range() takes 1 to 3 arguments"
    empty = False  # so far
    if not s_step.is_constant():
        step = 0 # this case signals a variable step
    else:
        step = s_step.const
        if step == 0:
            raise Exception, "range() with step zero"
        if s_start.is_constant() and s_stop.is_constant():
            try:
                if len(xrange(s_start.const, s_stop.const, step)) == 0:
                    empty = True
            except TypeError:   # if one of the .const is a Symbolic
                pass
    if empty:
        s_item = s_ImpossibleValue
    else:
        nonneg = False # so far
        if step > 0 or s_step.nonneg:
            nonneg = s_start.nonneg
        elif step < 0:
            nonneg = s_stop.nonneg or (s_stop.is_constant() and
                                       s_stop.const >= -1)
        s_item = SomeInteger(nonneg=nonneg)
    return getbookkeeper().newlist(s_item, range_step=step)

builtin_xrange = builtin_range # xxx for now allow it


def builtin_enumerate(s_obj):
    return SomeIterator(s_obj, "enumerate")


def builtin_reversed(s_obj):
    return SomeIterator(s_obj, "reversed")


def builtin_bool(s_obj):
    return s_obj.bool()

def builtin_int(s_obj, s_base=None):
    if isinstance(s_obj, SomeInteger):
        assert not s_obj.unsigned, "instead of int(r_uint(x)), use intmask(r_uint(x))"
    assert (s_base is None or isinstance(s_base, SomeInteger)
            and s_obj.knowntype == str), "only int(v|string) or int(string,int) expected"
    if s_base is not None:
        args_s = [s_obj, s_base]
    else:
        args_s = [s_obj]
    nonneg = isinstance(s_obj, SomeInteger) and s_obj.nonneg
    return constpropagate(int, args_s, SomeInteger(nonneg=nonneg))

def builtin_float(s_obj):
    return constpropagate(float, [s_obj], SomeFloat())

def builtin_chr(s_int):
    return constpropagate(chr, [s_int], SomeChar())

def builtin_unichr(s_int):
    return constpropagate(unichr, [s_int], SomeUnicodeCodePoint())

def builtin_unicode(s_unicode):
    return constpropagate(unicode, [s_unicode], SomeUnicodeString())

def builtin_bytearray(s_str):
    return SomeByteArray()

def our_issubclass(cls1, cls2):
    """ we're going to try to be less silly in the face of old-style classes"""
    from rpython.annotator.classdef import ClassDef
    if cls2 is object:
        return True
    def classify(cls):
        if isinstance(cls, ClassDef):
            return 'def'
        if cls.__module__ == '__builtin__':
            return 'builtin'
        else:
            return 'cls'
    kind1 = classify(cls1)
    kind2 = classify(cls2)
    if kind1 != 'def' and kind2 != 'def':
        return issubclass(cls1, cls2)
    if kind1 == 'builtin' and kind2 == 'def':
        return False
    elif kind1 == 'def' and kind2 == 'builtin':
        return issubclass(object, cls2)
    else:
        bk = getbookkeeper()
        def toclassdef(kind, cls):
            if kind != 'def':
                return bk.getuniqueclassdef(cls)
            else:
                return cls
        return toclassdef(kind1, cls1).issubclass(toclassdef(kind2, cls2))


def builtin_isinstance(s_obj, s_type, variables=None):
    r = SomeBool()
    if s_type.is_constant():
        typ = s_type.const
        if issubclass(typ, rpython.rlib.rarithmetic.base_int):
            r.const = issubclass(s_obj.knowntype, typ)
        else:
            if typ == long:
                getbookkeeper().warning("isinstance(., long) is not RPython")
                r.const = False
                return r

            assert not issubclass(typ, (int, long)) or typ in (bool, int, long), (
                "for integers only isinstance(.,int|r_uint) are supported")

            if s_obj.is_constant():
                r.const = isinstance(s_obj.const, typ)
            elif our_issubclass(s_obj.knowntype, typ):
                if not s_obj.can_be_none():
                    r.const = True
            elif not our_issubclass(typ, s_obj.knowntype):
                r.const = False
            elif s_obj.knowntype == int and typ == bool: # xxx this will explode in case of generalisation
                                                   # from bool to int, notice that isinstance( , bool|int)
                                                   # is quite border case for RPython
                r.const = False
        bk = getbookkeeper()
        if variables is None:
            op = bk._find_current_op("simple_call", 3)
            assert op.args[0] == Constant(isinstance)
            variables = [op.args[1]]
        for variable in variables:
            assert bk.annotator.binding(variable) == s_obj
        knowntypedata = {}
        if not hasattr(typ, '_freeze_') and isinstance(s_type, SomePBC):
            add_knowntypedata(knowntypedata, True, variables, bk.valueoftype(typ))
        r.set_knowntypedata(knowntypedata)
    return r

# note that this one either needs to be constant, or we will create SomeObject
def builtin_hasattr(s_obj, s_attr):
    if not s_attr.is_constant() or not isinstance(s_attr.const, str):
        getbookkeeper().warning('hasattr(%r, %r) is not RPythonic enough' %
                                (s_obj, s_attr))
    r = SomeBool()
    if s_obj.is_immutable_constant():
        r.const = hasattr(s_obj.const, s_attr.const)
    elif (isinstance(s_obj, SomePBC)
          and s_obj.getKind() is description.FrozenDesc):
        answers = {}
        for d in s_obj.descriptions:
            answer = (d.s_read_attribute(s_attr.const) != s_ImpossibleValue)
            answers[answer] = True
        if len(answers) == 1:
            r.const, = answers
    return r


def builtin_tuple(s_iterable):
    if isinstance(s_iterable, SomeTuple):
        return s_iterable
    return SomeObject()

def builtin_list(s_iterable):
    if isinstance(s_iterable, SomeList):
        return s_iterable.listdef.offspring()
    s_iter = s_iterable.iter()
    return getbookkeeper().newlist(s_iter.next())

def builtin_zip(s_iterable1, s_iterable2): # xxx not actually implemented
    s_iter1 = s_iterable1.iter()
    s_iter2 = s_iterable2.iter()
    s_tup = SomeTuple((s_iter1.next(),s_iter2.next()))
    return getbookkeeper().newlist(s_tup)

def builtin_min(*s_values):
    if len(s_values) == 1: # xxx do we support this?
        s_iter = s_values[0].iter()
        return s_iter.next()
    else:
        return unionof(*s_values)

def builtin_max(*s_values):
    if len(s_values) == 1: # xxx do we support this?
        s_iter = s_values[0].iter()
        return s_iter.next()
    else:
        s = unionof(*s_values)
        if type(s) is SomeInteger and not s.nonneg:
            nonneg = False
            for s1 in s_values:
                nonneg |= s1.nonneg
            if nonneg:
                s = SomeInteger(nonneg=True, knowntype=s.knowntype)
        return s

# collect all functions
import __builtin__
for name, value in globals().items():
    if name.startswith('builtin_'):
        original = getattr(__builtin__, name[8:])
        BUILTIN_ANALYZERS[original] = value


@analyzer_for(getattr(OSError.__init__, 'im_func', OSError.__init__))
def OSError_init(s_self, *args):
    pass

try:
    WindowsError
except NameError:
    pass
else:
    @analyzer_for(getattr(WindowsError.__init__, 'im_func', WindowsError.__init__))
    def WindowsError_init(s_self, *args):
        pass

@analyzer_for(getattr(object.__init__, 'im_func', object.__init__))
def object_init(s_self, *args):
    # ignore - mostly used for abstract classes initialization
    pass


@analyzer_for(sys.getdefaultencoding)
def conf():
    return SomeString()

@analyzer_for(rpython.rlib.rarithmetic.intmask)
def rarith_intmask(s_obj):
    return SomeInteger()

@analyzer_for(rpython.rlib.rarithmetic.longlongmask)
def rarith_longlongmask(s_obj):
    return SomeInteger(knowntype=rpython.rlib.rarithmetic.r_longlong)

@analyzer_for(rpython.rlib.objectmodel.instantiate)
def robjmodel_instantiate(s_clspbc):
    assert isinstance(s_clspbc, SomePBC)
    clsdef = None
    more_than_one = len(s_clspbc.descriptions) > 1
    for desc in s_clspbc.descriptions:
        cdef = desc.getuniqueclassdef()
        if more_than_one:
            getbookkeeper().needs_generic_instantiate[cdef] = True
        if not clsdef:
            clsdef = cdef
        else:
            clsdef = clsdef.commonbase(cdef)
    return SomeInstance(clsdef)

@analyzer_for(rpython.rlib.objectmodel.r_dict)
def robjmodel_r_dict(s_eqfn, s_hashfn, s_force_non_null=None):
    if s_force_non_null is None:
        force_non_null = False
    else:
        assert s_force_non_null.is_constant()
        force_non_null = s_force_non_null.const
    dictdef = getbookkeeper().getdictdef(is_r_dict=True,
                                         force_non_null=force_non_null)
    dictdef.dictkey.update_rdict_annotations(s_eqfn, s_hashfn)
    return SomeDict(dictdef)

@analyzer_for(rpython.rlib.objectmodel.r_ordereddict)
def robjmodel_r_ordereddict(s_eqfn, s_hashfn):
    dictdef = getbookkeeper().getdictdef(is_r_dict=True)
    dictdef.dictkey.update_rdict_annotations(s_eqfn, s_hashfn)
    return SomeOrderedDict(dictdef)

@analyzer_for(rpython.rlib.objectmodel.hlinvoke)
def robjmodel_hlinvoke(s_repr, s_llcallable, *args_s):
    from rpython.rtyper import rmodel
    from rpython.rtyper.error import TyperError

    assert s_repr.is_constant() and isinstance(s_repr.const, rmodel.Repr), "hlinvoke expects a constant repr as first argument"
    r_func, nimplicitarg = s_repr.const.get_r_implfunc()

    nbargs = len(args_s) + nimplicitarg
    s_sigs = r_func.get_s_signatures((nbargs, (), False))
    if len(s_sigs) != 1:
        raise TyperError("cannot hlinvoke callable %r with not uniform"
                         "annotations: %r" % (s_repr.const,
                                              s_sigs))
    _, s_ret = s_sigs[0]
    rresult = r_func.rtyper.getrepr(s_ret)

    return lltype_to_annotation(rresult.lowleveltype)


@analyzer_for(rpython.rlib.objectmodel.keepalive_until_here)
def robjmodel_keepalive_until_here(*args_s):
    return immutablevalue(None)

@analyzer_for(rpython.rtyper.lltypesystem.llmemory.cast_ptr_to_adr)
def llmemory_cast_ptr_to_adr(s):
    from rpython.annotator.model import SomeInteriorPtr
    assert not isinstance(s, SomeInteriorPtr)
    return SomeAddress()

@analyzer_for(rpython.rtyper.lltypesystem.llmemory.cast_adr_to_ptr)
def llmemory_cast_adr_to_ptr(s, s_type):
    assert s_type.is_constant()
    return SomePtr(s_type.const)

@analyzer_for(rpython.rtyper.lltypesystem.llmemory.cast_adr_to_int)
def llmemory_cast_adr_to_int(s, s_mode=None):
    return SomeInteger() # xxx

@analyzer_for(rpython.rtyper.lltypesystem.llmemory.cast_int_to_adr)
def llmemory_cast_int_to_adr(s):
    return SomeAddress()

try:
    import unicodedata
except ImportError:
    pass
else:
    @analyzer_for(unicodedata.decimal)
    def unicodedata_decimal(s_uchr):
        raise TypeError("unicodedate.decimal() calls should not happen at interp-level")

@analyzer_for(SomeOrderedDict.knowntype)
def analyze():
    return SomeOrderedDict(getbookkeeper().getdictdef())



# annotation of low-level types
from rpython.annotator.model import SomePtr
from rpython.rtyper.lltypesystem import lltype

@analyzer_for(lltype.malloc)
def malloc(s_T, s_n=None, s_flavor=None, s_zero=None, s_track_allocation=None,
           s_add_memory_pressure=None):
    assert (s_n is None or s_n.knowntype == int
            or issubclass(s_n.knowntype, rpython.rlib.rarithmetic.base_int))
    assert s_T.is_constant()
    if s_n is not None:
        n = 1
    else:
        n = None
    if s_zero:
        assert s_zero.is_constant()
    if s_flavor is None:
        p = lltype.malloc(s_T.const, n)
        r = SomePtr(lltype.typeOf(p))
    else:
        assert s_flavor.is_constant()
        assert s_track_allocation is None or s_track_allocation.is_constant()
        assert (s_add_memory_pressure is None or
                s_add_memory_pressure.is_constant())
        # not sure how to call malloc() for the example 'p' in the
        # presence of s_extraargs
        r = SomePtr(lltype.Ptr(s_T.const))
    return r

@analyzer_for(lltype.free)
def free(s_p, s_flavor, s_track_allocation=None):
    assert s_flavor.is_constant()
    assert s_track_allocation is None or s_track_allocation.is_constant()
    # same problem as in malloc(): some flavors are not easy to
    # malloc-by-example
    #T = s_p.ll_ptrtype.TO
    #p = lltype.malloc(T, flavor=s_flavor.const)
    #lltype.free(p, flavor=s_flavor.const)

@analyzer_for(lltype.render_immortal)
def render_immortal(s_p, s_track_allocation=None):
    assert s_track_allocation is None or s_track_allocation.is_constant()

@analyzer_for(lltype.typeOf)
def typeOf(s_val):
    lltype = annotation_to_lltype(s_val, info="in typeOf(): ")
    return immutablevalue(lltype)

@analyzer_for(lltype.cast_primitive)
def cast_primitive(T, s_v):
    assert T.is_constant()
    return ll_to_annotation(lltype.cast_primitive(T.const, annotation_to_lltype(s_v)._defl()))

@analyzer_for(lltype.nullptr)
def nullptr(T):
    assert T.is_constant()
    p = lltype.nullptr(T.const)
    return immutablevalue(p)

@analyzer_for(lltype.cast_pointer)
def cast_pointer(PtrT, s_p):
    assert isinstance(s_p, SomePtr), "casting of non-pointer: %r" % s_p
    assert PtrT.is_constant()
    cast_p = lltype.cast_pointer(PtrT.const, s_p.ll_ptrtype._defl())
    return SomePtr(ll_ptrtype=lltype.typeOf(cast_p))

@analyzer_for(lltype.cast_opaque_ptr)
def cast_opaque_ptr(PtrT, s_p):
    assert isinstance(s_p, SomePtr), "casting of non-pointer: %r" % s_p
    assert PtrT.is_constant()
    cast_p = lltype.cast_opaque_ptr(PtrT.const, s_p.ll_ptrtype._defl())
    return SomePtr(ll_ptrtype=lltype.typeOf(cast_p))

@analyzer_for(lltype.direct_fieldptr)
def direct_fieldptr(s_p, s_fieldname):
    assert isinstance(s_p, SomePtr), "direct_* of non-pointer: %r" % s_p
    assert s_fieldname.is_constant()
    cast_p = lltype.direct_fieldptr(s_p.ll_ptrtype._example(),
                                    s_fieldname.const)
    return SomePtr(ll_ptrtype=lltype.typeOf(cast_p))

@analyzer_for(lltype.direct_arrayitems)
def direct_arrayitems(s_p):
    assert isinstance(s_p, SomePtr), "direct_* of non-pointer: %r" % s_p
    cast_p = lltype.direct_arrayitems(s_p.ll_ptrtype._example())
    return SomePtr(ll_ptrtype=lltype.typeOf(cast_p))

@analyzer_for(lltype.direct_ptradd)
def direct_ptradd(s_p, s_n):
    assert isinstance(s_p, SomePtr), "direct_* of non-pointer: %r" % s_p
    # don't bother with an example here: the resulting pointer is the same
    return s_p

@analyzer_for(lltype.cast_ptr_to_int)
def cast_ptr_to_int(s_ptr): # xxx
    return SomeInteger()

@analyzer_for(lltype.cast_int_to_ptr)
def cast_int_to_ptr(PtrT, s_int):
    assert PtrT.is_constant()
    return SomePtr(ll_ptrtype=PtrT.const)

@analyzer_for(lltype.identityhash)
def identityhash(s_obj):
    assert isinstance(s_obj, SomePtr)
    return SomeInteger()

@analyzer_for(lltype.getRuntimeTypeInfo)
def getRuntimeTypeInfo(T):
    assert T.is_constant()
    return immutablevalue(lltype.getRuntimeTypeInfo(T.const))

@analyzer_for(lltype.runtime_type_info)
def runtime_type_info(s_p):
    assert isinstance(s_p, SomePtr), "runtime_type_info of non-pointer: %r" % s_p
    return SomePtr(lltype.typeOf(lltype.runtime_type_info(s_p.ll_ptrtype._example())))

@analyzer_for(lltype.Ptr)
def constPtr(T):
    assert T.is_constant()
    return immutablevalue(lltype.Ptr(T.const))


#________________________________
# weakrefs

import weakref

@analyzer_for(weakref.ref)
def weakref_ref(s_obj):
    if not isinstance(s_obj, SomeInstance):
        raise Exception("cannot take a weakref to %r" % (s_obj,))
    if s_obj.can_be_None:
        raise Exception("should assert that the instance we take "
                        "a weakref to cannot be None")
    return SomeWeakRef(s_obj.classdef)


from rpython.rtyper.lltypesystem import llmemory

@analyzer_for(llmemory.weakref_create)
def llweakref_create(s_obj):
    if (not isinstance(s_obj, SomePtr) or
        s_obj.ll_ptrtype.TO._gckind != 'gc'):
        raise Exception("bad type for argument to weakref_create(): %r" % (
            s_obj,))
    return SomePtr(llmemory.WeakRefPtr)

@analyzer_for(llmemory.weakref_deref )
def llweakref_deref(s_ptrtype, s_wref):
    if not (s_ptrtype.is_constant() and
            isinstance(s_ptrtype.const, lltype.Ptr) and
            s_ptrtype.const.TO._gckind == 'gc'):
        raise Exception("weakref_deref() arg 1 must be a constant "
                        "ptr type, got %s" % (s_ptrtype,))
    if not (isinstance(s_wref, SomePtr) and
            s_wref.ll_ptrtype == llmemory.WeakRefPtr):
        raise Exception("weakref_deref() arg 2 must be a WeakRefPtr, "
                        "got %s" % (s_wref,))
    return SomePtr(s_ptrtype.const)

@analyzer_for(llmemory.cast_ptr_to_weakrefptr)
def llcast_ptr_to_weakrefptr(s_ptr):
    assert isinstance(s_ptr, SomePtr)
    return SomePtr(llmemory.WeakRefPtr)

@analyzer_for(llmemory.cast_weakrefptr_to_ptr)
def llcast_weakrefptr_to_ptr(s_ptrtype, s_wref):
    if not (s_ptrtype.is_constant() and
            isinstance(s_ptrtype.const, lltype.Ptr)):
        raise Exception("cast_weakrefptr_to_ptr() arg 1 must be a constant "
                        "ptr type, got %s" % (s_ptrtype,))
    if not (isinstance(s_wref, SomePtr) and
            s_wref.ll_ptrtype == llmemory.WeakRefPtr):
        raise Exception("cast_weakrefptr_to_ptr() arg 2 must be a WeakRefPtr, "
                        "got %s" % (s_wref,))
    return SomePtr(s_ptrtype.const)

#________________________________
# non-gc objects

@analyzer_for(rpython.rlib.objectmodel.free_non_gc_object)
def robjmodel_free_non_gc_object(obj):
    pass


#_________________________________
# memory address

@analyzer_for(llmemory.raw_malloc)
def raw_malloc(s_size):
    assert isinstance(s_size, SomeInteger) #XXX add noneg...?
    return SomeAddress()

@analyzer_for(llmemory.raw_malloc_usage)
def raw_malloc_usage(s_size):
    assert isinstance(s_size, SomeInteger) #XXX add noneg...?
    return SomeInteger(nonneg=True)

@analyzer_for(llmemory.raw_free)
def raw_free(s_addr):
    assert isinstance(s_addr, SomeAddress)

@analyzer_for(llmemory.raw_memclear)
def raw_memclear(s_addr, s_int):
    assert isinstance(s_addr, SomeAddress)
    assert isinstance(s_int, SomeInteger)

@analyzer_for(llmemory.raw_memcopy)
def raw_memcopy(s_addr1, s_addr2, s_int):
    assert isinstance(s_addr1, SomeAddress)
    assert isinstance(s_addr2, SomeAddress)
    assert isinstance(s_int, SomeInteger) #XXX add noneg...?


#_________________________________
# offsetof/sizeof


@analyzer_for(llmemory.offsetof)
def offsetof(TYPE, fldname):
    return SomeInteger()
