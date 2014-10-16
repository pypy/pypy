"""
Built-in functions.
"""
import sys

from rpython.annotator.model import (
    SomeInteger, SomeObject, SomeChar, SomeBool, SomeString, SomeTuple,
    SomeUnicodeCodePoint, SomeFloat, unionof, SomeUnicodeString,
    SomePBC, SomeInstance, SomeDict, SomeList, SomeWeakRef, SomeIterator,
    SomeOrderedDict, SomeByteArray, add_knowntypedata, s_ImpossibleValue,)
from rpython.annotator.bookkeeper import (
    getbookkeeper, immutablevalue, BUILTIN_ANALYZERS, analyzer_for)
from rpython.annotator import description
from rpython.flowspace.model import Constant
import rpython.rlib.rarithmetic
import rpython.rlib.objectmodel
from rpython.annotator.model import AnnotatorError


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
        raise Exception("range() takes 1 to 3 arguments")
    empty = False  # so far
    if not s_step.is_constant():
        step = 0 # this case signals a variable step
    else:
        step = s_step.const
        if step == 0:
            raise Exception("range() with step zero")
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
    raise AnnotatorError("tuple(): argument must be another tuple")

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


@analyzer_for(getattr(object.__init__, 'im_func', object.__init__))
def object_init(s_self, *args):
    # ignore - mostly used for abstract classes initialization
    pass

@analyzer_for(getattr(EnvironmentError.__init__, 'im_func', EnvironmentError.__init__))
def EnvironmentError_init(s_self, *args):
    pass

try:
    WindowsError
except NameError:
    pass
else:
    @analyzer_for(getattr(WindowsError.__init__, 'im_func', WindowsError.__init__))
    def WindowsError_init(s_self, *args):
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
    from rpython.rtyper.llannotation import lltype_to_annotation
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

#________________________________
# non-gc objects

@analyzer_for(rpython.rlib.objectmodel.free_non_gc_object)
def robjmodel_free_non_gc_object(obj):
    pass
