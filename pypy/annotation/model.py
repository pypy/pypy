"""
This file defines the 'subset' SomeValue classes.

An instance of a SomeValue class stands for a Python object that has some
known properties, for example that is known to be a list of non-negative
integers.  Each instance can be considered as an object that is only
'partially defined'.  Another point of view is that each instance is a
generic element in some specific subset of the set of all objects.

"""

# Old terminology still in use here and there:
#    SomeValue means one of the SomeXxx classes in this file.
#    Cell is an instance of one of these classes.
#
# Think about cells as potato-shaped circles in a diagram:
#    ______________________________________________________
#   / SomeObject()                                         \
#  /   ___________________________          ______________  \
#  |  / SomeInteger(nonneg=False) \____    / SomeString() \  \
#  | /     __________________________  \   |              |  |
#  | |    / SomeInteger(nonneg=True) \ |   |      "hello" |  |
#  | |    |   0    42       _________/ |   \______________/  |
#  | \ -3 \________________/           /                     |
#  \  \                     -5   _____/                      /
#   \  \________________________/              3.1416       /
#    \_____________________________________________________/
#


from types import BuiltinFunctionType, MethodType, FunctionType
import pypy
from pypy.tool import descriptor
from pypy.tool.pairtype import pair, extendabletype
from pypy.rlib.rarithmetic import r_uint, r_ulonglong, base_int
from pypy.rlib.rarithmetic import r_singlefloat, r_longfloat
import inspect, weakref

DEBUG = False    # set to False to disable recording of debugging information

class State(object):
    pass
TLS = State()

class SomeObject(object):
    """The set of all objects.  Each instance stands
    for an arbitrary object about which nothing is known."""
    __metaclass__ = extendabletype
    knowntype = object
    immutable = False

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.__dict__  == other.__dict__)
    def __ne__(self, other):
        return not (self == other)
    def __repr__(self):
        try:
            reprdict = TLS.reprdict
        except AttributeError:
            reprdict = TLS.reprdict = {}
        if self in reprdict:
            kwds = '...'
        else:
            reprdict[self] = True
            try:
                items = self.__dict__.items()
                items.sort()
                args = []
                for k, v in items:
                    m = getattr(self, 'fmt_' + k, repr)
                    r = m(v)
                    if r is not None:
                        args.append('%s=%s'%(k, r))
                kwds = ', '.join(args)
            finally:
                del reprdict[self]
        return '%s(%s)' % (self.__class__.__name__, kwds)

    def fmt_knowntype(self, t):
        return t.__name__
    
    def contains(self, other):
        if self == other:
            return True
        try:
            TLS.no_side_effects_in_union += 1
        except AttributeError:
            TLS.no_side_effects_in_union = 1
        try:
            try:
                return pair(self, other).union() == self
            except UnionError:
                return False
        finally:
            TLS.no_side_effects_in_union -= 1

    def is_constant(self):
        d = self.__dict__
        return 'const' in d or 'const_box' in d

    def is_immutable_constant(self):
        return self.immutable and 'const' in self.__dict__

    # delegate accesses to 'const' to accesses to 'const_box.value',
    # where const_box is a Constant.  XXX the idea is to eventually
    # use systematically 'const_box' instead of 'const' for
    # non-immutable constant annotations
    class ConstAccessDelegator(object):
        def __get__(self, obj, cls=None):
            return obj.const_box.value
    const = ConstAccessDelegator()
    del ConstAccessDelegator

    # for debugging, record where each instance comes from
    # this is disabled if DEBUG is set to False
    def __new__(cls, *args, **kw):
        new = super(SomeObject, cls).__new__
        if new is object.__new__:
            # Since python 2.6, object.__new__ warns
            # when parameters are passed
            self = new(cls)
        else:
            self = new(cls, *args, **kw)
        if DEBUG:
            try:
                bookkeeper = pypy.annotation.bookkeeper.getbookkeeper()
                position_key = bookkeeper.position_key
            except AttributeError:
                pass
            else:
                bookkeeper._isomeobject_coming_from[self] = position_key, None
        return self

    def origin(self):
        bookkeeper = pypy.annotation.bookkeeper.getbookkeeper()
        if bookkeeper is None:
            return None
        return bookkeeper._isomeobject_coming_from.get(self, (None, None))[0]
    origin = property(origin)

    def caused_by_merge(self):
        bookkeeper = pypy.annotation.bookkeeper.getbookkeeper()
        if bookkeeper is None:
            return None
        return bookkeeper._isomeobject_coming_from.get(self, (None, None))[1]
    def set_caused_by_merge(self, nvalue):
        bookkeeper = pypy.annotation.bookkeeper.getbookkeeper()
        if bookkeeper is None:
            return
        bookkeeper._isomeobject_coming_from[self] = self.origin, nvalue
    caused_by_merge = property(caused_by_merge, set_caused_by_merge)
    del set_caused_by_merge

    def can_be_none(self):
        return True
        
    def nonnoneify(self):
        return self

class SomeFloat(SomeObject):
    "Stands for a float or an integer."
    knowntype = float   # if we don't know if it's a float or an int,
                        # pretend it's a float.
    immutable = True

    def __eq__(self, other):
        if (type(self) is SomeFloat and type(other) is SomeFloat and
            self.is_constant() and other.is_constant()):
            from pypy.rlib.rfloat import isnan, copysign
            # NaN unpleasantness.
            if isnan(self.const) and isnan(other.const):
                return True
            # 0.0 vs -0.0 unpleasantness.
            if not self.const and not other.const:
                return copysign(1., self.const) == copysign(1., other.const)
            #
        return super(SomeFloat, self).__eq__(other)

    def can_be_none(self):
        return False

class SomeSingleFloat(SomeObject):
    "Stands for an r_singlefloat."
    # No operation supported, not even union with a regular float
    knowntype = r_singlefloat
    immutable = True

    def can_be_none(self):
        return False

class SomeLongFloat(SomeObject):
    "Stands for an r_longfloat."
    # No operation supported, not even union with a regular float
    knowntype = r_longfloat
    immutable = True

    def can_be_none(self):
        return False

class SomeInteger(SomeFloat):
    "Stands for an object which is known to be an integer."
    knowntype = int
    # size is in multiples of C's sizeof(long)!
    def __init__(self, nonneg=False, unsigned=None, knowntype=None):
        assert (knowntype is None or knowntype is int or
                issubclass(knowntype, base_int))
        if knowntype is None:
            if unsigned:
                knowntype = r_uint
            else:
                knowntype = int
        elif unsigned is not None:
            raise TypeError('Conflicting specification for SomeInteger')
        self.knowntype = knowntype
        unsigned = self.knowntype(-1) > 0
        self.nonneg = unsigned or nonneg
        self.unsigned = unsigned  # pypy.rlib.rarithmetic.r_uint

class SomeBool(SomeInteger):
    "Stands for true or false."
    knowntype = bool
    nonneg = True
    unsigned = False
    def __init__(self):
        pass

class SomeString(SomeObject):
    "Stands for an object which is known to be a string."
    knowntype = str
    immutable = True
    def __init__(self, can_be_None=False):
        self.can_be_None = can_be_None

    def can_be_none(self):
        return self.can_be_None

    def nonnoneify(self):
        return SomeString(can_be_None=False)

class SomeUnicodeString(SomeObject):
    "Stands for an object which is known to be an unicode string"
    knowntype = unicode
    immutable = True
    def __init__(self, can_be_None=False):
        self.can_be_None = can_be_None

    def can_be_none(self):
        return self.can_be_None

    def nonnoneify(self):
        return SomeUnicodeString(can_be_None=False)

class SomeChar(SomeString):
    "Stands for an object known to be a string of length 1."
    can_be_None = False
    def __init__(self):    # no 'can_be_None' argument here
        pass

class SomeUnicodeCodePoint(SomeUnicodeString):
    "Stands for an object known to be a unicode codepoint."
    can_be_None = False
    def __init__(self):    # no 'can_be_None' argument here
        pass

SomeString.basestringclass = SomeString
SomeString.basecharclass = SomeChar
SomeUnicodeString.basestringclass = SomeUnicodeString
SomeUnicodeString.basecharclass = SomeUnicodeCodePoint

class SomeList(SomeObject):
    "Stands for a homogenous list of any length."
    knowntype = list
    def __init__(self, listdef):
        self.listdef = listdef
    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return False
        if not self.listdef.same_as(other.listdef):
            return False
        selfdic = self.__dict__.copy()
        otherdic = other.__dict__.copy()
        del selfdic['listdef']
        del otherdic['listdef']
        return selfdic == otherdic

    def can_be_none(self):
        return True

class SomeTuple(SomeObject):
    "Stands for a tuple of known length."
    knowntype = tuple
    immutable = True
    def __init__(self, items):
        self.items = tuple(items)   # tuple of s_xxx elements
        for i in items:
            if not i.is_constant():
                break
        else:
            self.const = tuple([i.const for i in items])

    def can_be_none(self):
        return False

class SomeDict(SomeObject):
    "Stands for a dict."
    knowntype = dict
    def __init__(self, dictdef):
        self.dictdef = dictdef
    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return False
        if not self.dictdef.same_as(other.dictdef):
            return False
        selfdic = self.__dict__.copy()
        otherdic = other.__dict__.copy()
        del selfdic['dictdef']
        del otherdic['dictdef']
        return selfdic == otherdic

    def can_be_none(self):
        return True

    def fmt_const(self, const):
        if len(const) < 20:
            return repr(const)
        else:
            return '{...%s...}'%(len(const),)


class SomeIterator(SomeObject):
    "Stands for an iterator returning objects from a given container."
    knowntype = type(iter([]))  # arbitrarily chose seqiter as the type
    def __init__(self, s_container, *variant):
        self.variant = variant
        self.s_container = s_container

    def can_be_none(self):
        return False

class SomeInstance(SomeObject):
    "Stands for an instance of a (user-defined) class."

    def __init__(self, classdef, can_be_None=False, flags={}):
        self.classdef = classdef
        self.knowntype = classdef or object
        self.can_be_None = can_be_None
        self.flags = flags

    def fmt_knowntype(self, kt):
        return None
    def fmt_classdef(self, cdef):
        if cdef is None:
            return 'object'
        else:
            return cdef.name
    def fmt_flags(self, flags):
        if flags:
            return repr(flags)
        else:
            return None

    def can_be_none(self):
        return self.can_be_None

    def nonnoneify(self):
        return SomeInstance(self.classdef, can_be_None=False)


class SomePBC(SomeObject):
    """Stands for a global user instance, built prior to the analysis,
    or a set of such instances."""
    immutable = True

    def __init__(self, descriptions, can_be_None=False, subset_of=None):
        # descriptions is a set of Desc instances
        descriptions = set(descriptions)
        self.descriptions = descriptions
        self.can_be_None = can_be_None
        self.subset_of = subset_of
        self.simplify()
        if self.isNone():
            self.knowntype = type(None)
            self.const = None
        else:
            knowntype = reduce(commonbase,
                               [x.knowntype for x in descriptions])
            if knowntype == type(Exception):
                knowntype = type
            if knowntype != object:
                self.knowntype = knowntype
            if len(descriptions) == 1 and not can_be_None:
                # hack for the convenience of direct callers to SomePBC():
                # only if there is a single object in descriptions
                desc, = descriptions
                if desc.pyobj is not None:
                    self.const = desc.pyobj

    def any_description(self):
        return iter(self.descriptions).next()

    def getKind(self):
        "Return the common Desc class of all descriptions in this PBC."
        kinds = {}
        for x in self.descriptions:
            assert type(x).__name__.endswith('Desc')  # avoid import nightmares
            kinds[x.__class__] = True
        assert len(kinds) <= 1, (
            "mixing several kinds of PBCs: %r" % (kinds.keys(),))
        if not kinds:
            raise ValueError("no 'kind' on the 'None' PBC")
        return kinds.keys()[0]

    def simplify(self):
        if self.descriptions:
            # We check that the set only contains a single kind of Desc instance
            kind = self.getKind()
            # then we remove unnecessary entries in self.descriptions:
            # some MethodDescs can be 'shadowed' by others
            if len(self.descriptions) > 1:
                kind.simplify_desc_set(self.descriptions)
        else:
            assert self.can_be_None, "use s_ImpossibleValue"

    def isNone(self):
        return len(self.descriptions) == 0

    def can_be_none(self):
        return self.can_be_None

    def nonnoneify(self):
        if self.isNone():
            return s_ImpossibleValue
        else:
            return SomePBC(self.descriptions, can_be_None=False)

    def fmt_descriptions(self, pbis):
        if hasattr(self, 'const'):
            return None
        else:
            return '{...%s...}'%(len(pbis),)

    def fmt_knowntype(self, kt):
        if self.is_constant():
            return None
        else:
            return kt.__name__

class SomeGenericCallable(SomeObject):
    """ Stands for external callable with known signature
    """
    def __init__(self, args, result):
        self.args_s = args
        self.s_result = result

    def can_be_None(self):
        return True

class SomeBuiltin(SomeObject):
    "Stands for a built-in function or method with special-cased analysis."
    knowntype = BuiltinFunctionType  # == BuiltinMethodType
    immutable = True

    def __init__(self, analyser, s_self=None, methodname=None):
        if isinstance(analyser, MethodType):
            analyser = descriptor.InstanceMethod(
                analyser.im_func,
                analyser.im_self,
                analyser.im_class)
        self.analyser = analyser
        self.s_self = s_self
        self.methodname = methodname

    def can_be_none(self):
        return False

class SomeBuiltinMethod(SomeBuiltin):
    """ Stands for a built-in method which has got special meaning
    """
    knowntype = MethodType

class SomeExternalObject(SomeObject):
    """Stands for an object of 'external' type.  External types have a Repr
    controlled by pypy.rpython.extregistry."""

    def __init__(self, knowntype):
        self.knowntype = knowntype

    def can_be_none(self):
        return True

class SomeImpossibleValue(SomeObject):
    """The empty set.  Instances are placeholders for objects that
    will never show up at run-time, e.g. elements of an empty list."""
    immutable = True
    annotationcolor = (160,160,160)

    def can_be_none(self):
        return False


s_None = SomePBC([], can_be_None=True)
s_Bool = SomeBool()
s_ImpossibleValue = SomeImpossibleValue()

# ____________________________________________________________
# weakrefs

class SomeWeakRef(SomeObject):
    knowntype = weakref.ReferenceType
    immutable = True
    def __init__(self, classdef):
        # 'classdef' is None for known-to-be-dead weakrefs.
        self.classdef = classdef

# ____________________________________________________________
# memory addresses

from pypy.rpython.lltypesystem import llmemory

class SomeAddress(SomeObject):
    immutable = True

    def can_be_none(self):
        return False

    def is_null_address(self):
        return self.is_immutable_constant() and not self.const

# The following class is used to annotate the intermediate value that
# appears in expressions of the form:
# addr.signed[offset] and addr.signed[offset] = value

class SomeTypedAddressAccess(SomeObject):
    def __init__(self, type):
        self.type = type

    def can_be_none(self):
        return False

#____________________________________________________________
# annotation of low-level types

from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype

class SomePtr(SomeObject):
    knowntype = lltype._ptr
    immutable = True
    def __init__(self, ll_ptrtype):
        assert isinstance(ll_ptrtype, lltype.Ptr)
        self.ll_ptrtype = ll_ptrtype

    def can_be_none(self):
        return False

class SomeInteriorPtr(SomePtr):
    def __init__(self, ll_ptrtype):
        assert isinstance(ll_ptrtype, lltype.InteriorPtr)
        self.ll_ptrtype = ll_ptrtype

class SomeLLADTMeth(SomeObject):
    immutable = True
    def __init__(self, ll_ptrtype, func):
        self.ll_ptrtype = ll_ptrtype
        self.func = func 

    def can_be_none(self):
        return False

class SomeOOObject(SomeObject):
    def __init__(self):
        self.ootype = ootype.Object

class SomeOOClass(SomeObject):
    def __init__(self, ootype):
        self.ootype = ootype

class SomeOOInstance(SomeObject):
    def __init__(self, ootype, can_be_None=False):
        self.ootype = ootype
        self.can_be_None = can_be_None

class SomeOOBoundMeth(SomeObject):
    immutable = True
    def __init__(self, ootype, name):
        self.ootype = ootype
        self.name = name

class SomeOOStaticMeth(SomeObject):
    immutable = True
    def __init__(self, method):
        self.method = method
        
NUMBER = object()
annotation_to_ll_map = [
    (SomeSingleFloat(), lltype.SingleFloat),
    (s_None, lltype.Void),   # also matches SomeImpossibleValue()
    (s_Bool, lltype.Bool),
    (SomeInteger(knowntype=r_ulonglong), NUMBER),    
    (SomeFloat(), lltype.Float),
    (SomeLongFloat(), lltype.LongFloat),
    (SomeChar(), lltype.Char),
    (SomeUnicodeCodePoint(), lltype.UniChar),
    (SomeAddress(), llmemory.Address),
]

def annotation_to_lltype(s_val, info=None):
    if isinstance(s_val, SomeOOInstance):
        return s_val.ootype
    if isinstance(s_val, SomeOOStaticMeth):
        return s_val.method
    if isinstance(s_val, SomeOOClass):
        return ootype.Class
    if isinstance(s_val, SomeOOObject):
        return s_val.ootype
    if isinstance(s_val, SomeInteriorPtr):
        p = s_val.ll_ptrtype
        if 0 in p.offsets:
            assert list(p.offsets).count(0) == 1
            return lltype.Ptr(lltype.Ptr(p.PARENTTYPE)._interior_ptr_type_with_index(p.TO))
        else:
            return lltype.Ptr(p.PARENTTYPE)
    if isinstance(s_val, SomePtr):
        return s_val.ll_ptrtype
    for witness, T in annotation_to_ll_map:
        if witness.contains(s_val):
            if T is NUMBER:
                return lltype.build_number(None, s_val.knowntype)
            return T
    if info is None:
        info = ''
    else:
        info = '%s: ' % info
    raise ValueError("%sshould return a low-level type,\ngot instead %r" % (
        info, s_val))

ll_to_annotation_map = dict([(ll, ann) for ann, ll in annotation_to_ll_map if ll is not NUMBER])

def lltype_to_annotation(T):
    try:
        s = ll_to_annotation_map.get(T)
    except TypeError:
        s = None    # unhashable T, e.g. a Ptr(GcForwardReference())
    if s is None:
        if isinstance(T, lltype.Typedef):
            return lltype_to_annotation(T.OF)
        if isinstance(T, lltype.Number):
            return SomeInteger(knowntype=T._type)
        if isinstance(T, (ootype.Instance, ootype.BuiltinType)):
            return SomeOOInstance(T)
        elif isinstance(T, ootype.StaticMethod):
            return SomeOOStaticMeth(T)
        elif T == ootype.Class:
            return SomeOOClass(ootype.ROOT)
        elif T == ootype.Object:
            return SomeOOObject()
        elif isinstance(T, lltype.InteriorPtr):
            return SomeInteriorPtr(T)
        else:
            return SomePtr(T)
    else:
        return s

def ll_to_annotation(v):
    if v is None:
        # i think we can only get here in the case of void-returning
        # functions
        return s_None
    if isinstance(v, lltype._interior_ptr):
        ob = v._parent
        if ob is None:
            raise RuntimeError
        T = lltype.InteriorPtr(lltype.typeOf(ob), v._T, v._offsets)
        return SomeInteriorPtr(T)
    return lltype_to_annotation(lltype.typeOf(v))
    
# ____________________________________________________________

class UnionError(Exception):
    """Signals an suspicious attempt at taking the union of
    deeply incompatible SomeXxx instances."""

def unionof(*somevalues):
    "The most precise SomeValue instance that contains all the values."
    try:
        s1, s2 = somevalues
    except ValueError:
        s1 = s_ImpossibleValue
        for s2 in somevalues:
            if s1 != s2:
                s1 = pair(s1, s2).union()
    else:
        # this is just a performance shortcut
        if s1 != s2:
            s1 = pair(s1, s2).union()
    if DEBUG:
        if s1.caused_by_merge is None and len(somevalues) > 1:
            s1.caused_by_merge = somevalues
    return s1

def isdegenerated(s_value):
    return s_value.__class__ is SomeObject and s_value.knowntype is not type

# make knowntypedata dictionary

def add_knowntypedata(ktd, truth, vars, s_obj):
    for v in vars:
        ktd[(truth, v)] = s_obj

def merge_knowntypedata(ktd1, ktd2):
    r = {}
    for truth_v in ktd1:
        if truth_v in ktd2:
            r[truth_v] = unionof(ktd1[truth_v], ktd2[truth_v])
    return r

def not_const(s_obj):
    if s_obj.is_constant():
        new_s_obj = SomeObject()
        new_s_obj.__class__ = s_obj.__class__
        dic = new_s_obj.__dict__ = s_obj.__dict__.copy()
        if 'const' in dic:
            del new_s_obj.const
        else:
            del new_s_obj.const_box
        s_obj = new_s_obj
    return s_obj

# ____________________________________________________________
# internal

def commonbase(cls1, cls2):   # XXX single inheritance only  XXX hum
    l1 = inspect.getmro(cls1)
    l2 = inspect.getmro(cls2) 
    if l1[-1] != object: 
        l1 = l1 + (object,) 
    if l2[-1] != object: 
        l2 = l2 + (object,) 
    for x in l1: 
        if x in l2: 
            return x 
    assert 0, "couldn't get to commonbase of %r and %r" % (cls1, cls2)

def missing_operation(cls, name):
    def default_op(*args):
        if args and isinstance(args[0], tuple):
            flattened = tuple(args[0]) + args[1:]
        else:
            flattened = args
        for arg in flattened:
            if arg.__class__ is SomeObject and arg.knowntype is not type:
                return  SomeObject()
        bookkeeper = pypy.annotation.bookkeeper.getbookkeeper()
        bookkeeper.warning("no precise annotation supplied for %s%r" % (name, args))
        return s_ImpossibleValue
    setattr(cls, name, default_op)

class HarmlesslyBlocked(Exception):
    """Raised by the unaryop/binaryop to signal a harmless kind of
    BlockedInference: the current block is blocked, but not in a way
    that gives 'Blocked block' errors at the end of annotation."""


def read_can_only_throw(opimpl, *args):
    can_only_throw = getattr(opimpl, "can_only_throw", None)
    if can_only_throw is None or isinstance(can_only_throw, list):
        return can_only_throw
    return can_only_throw(*args)

#
# safety check that no-one is trying to make annotation and translation
# faster by providing the -O option to Python.
try:
    assert False
except AssertionError:
    pass   # fine
else:
    raise RuntimeError("The annotator relies on 'assert' statements from the\n"
                     "\tannotated program: you cannot run it with 'python -O'.")

# this has the side-effect of registering the unary and binary operations
from pypy.annotation.unaryop  import UNARY_OPERATIONS
from pypy.annotation.binaryop import BINARY_OPERATIONS
