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


from types import BuiltinFunctionType, MethodType
import pypy
from pypy.annotation.pairtype import pair, extendabletype
from pypy.tool.tls import tlsobject
from pypy.rpython.rarithmetic import r_uint, r_longlong, r_ulonglong
import inspect
from sys import maxint


DEBUG = True    # set to False to disable recording of debugging information
TLS = tlsobject()

"""
Some history (Chris):

As a first approach to break this thing down, I slottified
all of these objects. The result was not overwhelming:
A savingof 5MB, but four percent of slowdown, since object
comparison got much more expensive, by lacking a __dict__.

So I trashed 8 hours of work, without a check-in. (Just
writing this here to leave *some* trace of work).

Then I tried to make all instances unique and wrote a lot
of attribute tracking code here, locked write access
outside of __init__, and patched many modules and several
hundred lines of code.
Finally I came up with a better concept, which is postponed.

"""

class SomeObject:
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
        return hasattr(self, 'const')

    def is_immutable_constant(self):
        return self.immutable and hasattr(self, 'const')

    # for debugging, record where each instance comes from
    # this is disabled if DEBUG is set to False
    _coming_from = {}
    def __new__(cls, *args, **kw):
        self = super(SomeObject, cls).__new__(cls, *args, **kw)
        if DEBUG:
            try:
                bookkeeper = pypy.annotation.bookkeeper.getbookkeeper()
                position_key = bookkeeper.position_key
            except AttributeError:
                pass
            else:
                SomeObject._coming_from[id(self)] = position_key, None
        return self

    def origin(self):
        return SomeObject._coming_from.get(id(self), (None, None))[0]
    def set_origin(self, nvalue):
        SomeObject._coming_from[id(self)] = nvalue, self.caused_by_merge
    origin = property(origin, set_origin)
    del set_origin

    def caused_by_merge(self):
        return SomeObject._coming_from.get(id(self), (None, None))[1]
    def set_caused_by_merge(self, nvalue):
        SomeObject._coming_from[id(self)] = self.origin, nvalue
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

    def can_be_none(self):
        return False

class SomeInteger(SomeFloat):
    "Stands for an object which is known to be an integer."
    knowntype = int
    # size is in multiples of C's sizeof(long)!
    def __init__(self, nonneg=False, unsigned=False, size=1):
        self.nonneg = unsigned or nonneg
        self.unsigned = unsigned  # pypy.rpython.rarithmetic.r_uint
        if maxint != 2**31-1:
            size = 1    #XXX don't support longlong on 64 bits systems
        self.size = size
        if self.unsigned:
            if self.size == 2:
                self.knowntype = r_ulonglong
            else:
                self.knowntype = r_uint
        else:
            if self.size == 2:
                self.knowntype = r_longlong
            else:
                self.knowntype = int

    def fmt_size(self, s):
        if s != 1:
            return str(s)


class SomeBool(SomeInteger):
    "Stands for true or false."
    knowntype = bool
    nonneg = True
    unsigned = False
    size = 1
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

class SomeChar(SomeString):
    "Stands for an object known to be a string of length 1."

class SomeUnicodeCodePoint(SomeObject):
    "Stands for an object known to be a unicode codepoint."
    knowntype = unicode
    immutable = True

    def can_be_none(self):
        return False

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

class SomeSlice(SomeObject):
    knowntype = slice
    immutable = True
    def __init__(self, start, stop, step):
        self.start = start
        self.stop = stop
        self.step = step

    def can_be_none(self):
        return False

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

    def __init__(self, classdef, can_be_None=False):
        self.classdef = classdef
        self.knowntype = classdef or object
        self.can_be_None = can_be_None

    def fmt_knowntype(self, kt):
        return None
    def fmt_classdef(self, cdef):
        if cdef is None:
            return 'object'
        else:
            return cdef.name

    def can_be_none(self):
        return self.can_be_None

    def nonnoneify(self):
        return SomeInstance(self.classdef, can_be_None=False)


class SomePBC(SomeObject):
    """Stands for a global user instance, built prior to the analysis,
    or a set of such instances."""
    immutable = True

    def __init__(self, descriptions, can_be_None=False):
        # descriptions is a set of Desc instances.
        descriptions = dict.fromkeys(descriptions)
        self.descriptions = descriptions
        self.can_be_None = can_be_None
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


class SomeBuiltin(SomeObject):
    "Stands for a built-in function or method with special-cased analysis."
    knowntype = BuiltinFunctionType  # == BuiltinMethodType
    immutable = True

    def __init__(self, analyser, s_self=None, methodname=None):
        self.analyser = analyser
        self.s_self = s_self
        self.methodname = methodname

    def can_be_none(self):
        return False


class SomeExternalObject(SomeObject):
    """Stands for an object of 'external' type.  External types are defined
    in pypy.rpython.extfunctable.declaretype(), and represent simple types
    with some methods that need direct back-end support."""

    def __init__(self, knowntype):
        self.knowntype = knowntype

    def can_be_none(self):
        return True

class SomeCTypesObject(SomeObject):
    """Stands for an object of the ctypes module."""

    def __init__(self, knowntype):
        self.knowntype = knowntype

    def can_be_none(self):
        return False


class SomeImpossibleValue(SomeObject):
    """The empty set.  Instances are placeholders for objects that
    will never show up at run-time, e.g. elements of an empty list."""
    immutable = True

    def can_be_none(self):
        return False


s_None = SomePBC([], can_be_None=True)
s_ImpossibleValue = SomeImpossibleValue()

# ____________________________________________________________
# memory addresses

from pypy.rpython.lltypesystem import llmemory

class SomeAddress(SomeObject):
    immutable = True
    def __init__(self, is_null=False):
        self.is_null = is_null

    def can_be_none(self):
        return False


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

class SomePtr(SomeObject):
    immutable = True
    def __init__(self, ll_ptrtype):
        self.ll_ptrtype = ll_ptrtype

    def can_be_none(self):
        return False

class SomeLLADTMeth(SomeObject):
    immutable = True
    def __init__(self, ll_ptrtype, func):
        self.ll_ptrtype = ll_ptrtype
        self.func = func 

    def can_be_none(self):
        return False

class SomeOOClass(SomeObject):
    def __init__(self, ootype):
        self.ootype = ootype

class SomeOOInstance(SomeObject):
    def __init__(self, ootype):
        self.ootype = ootype

class SomeOOBoundMeth(SomeObject):
    immutable = True
    def __init__(self, ootype, name):
        self.ootype = ootype
        self.name = name

class SomeOOStaticMeth(SomeObject):
    immutable = True
    def __init__(self, method):
        self.method = method
        
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype

annotation_to_ll_map = [
    (s_None, lltype.Void),   # also matches SomeImpossibleValue()
    (SomeBool(), lltype.Bool),
    (SomeInteger(), lltype.Signed),
    (SomeInteger(size=2), lltype.SignedLongLong),    
    (SomeInteger(nonneg=True, unsigned=True), lltype.Unsigned),    
    (SomeInteger(nonneg=True, unsigned=True, size=2), lltype.UnsignedLongLong),    
    (SomeFloat(), lltype.Float),
    (SomeChar(), lltype.Char),
    (SomeUnicodeCodePoint(), lltype.UniChar),
    (SomeAddress(), llmemory.Address),
]

def annotation_to_lltype(s_val, info=None):
    if isinstance(s_val, SomeOOInstance):
        return s_val.ootype
    if isinstance(s_val, SomeOOStaticMeth):
        return s_val.method
    if isinstance(s_val, SomePtr):
        return s_val.ll_ptrtype
    for witness, lltype in annotation_to_ll_map:
        if witness.contains(s_val):
            return lltype
    if info is None:
        info = ''
    else:
        info = '%s: ' % info
    raise ValueError("%sshould return a low-level type,\ngot instead %r" % (
        info, s_val))

ll_to_annotation_map = dict([(ll, ann) for ann,ll in annotation_to_ll_map])

def lltype_to_annotation(T):
    s = ll_to_annotation_map.get(T)
    if s is None:
        if isinstance(T, ootype.Instance):
            return SomeOOInstance(T)
        elif isinstance(T, ootype.StaticMethod):
            return SomeOOStaticMeth(T)
        else:
            return SomePtr(T)
    else:
        return s

def ll_to_annotation(v):
    if v is None:
        # i think we can only get here in the case of void-returning
        # functions
        from pypy.annotation.bookkeeper import getbookkeeper
        return getbookkeeper().immutablevalue(None)
    if isinstance(v, MethodType):
        ll_ptrtype = lltype.typeOf(v.im_self)
        assert isinstance(ll_ptrtype, lltype.Ptr)
        return SomeLLADTMeth(ll_ptrtype, v.im_func)
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

# ____________________________________________________________
# internal

def setunion(d1, d2):
    "Union of two sets represented as dictionaries."
    d = d1.copy()
    d.update(d2)
    return d

def set(it):
    "Turn an iterable into a set."
    d = {}
    for x in it:
        d[x] = True
    return d

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
            if arg.__class__ == SomeObject and arg.knowntype != type:
                return  SomeObject()
        bookkeeper = pypy.annotation.bookkeeper.getbookkeeper()
        bookkeeper.warning("no precise annotation supplied for %s%r" % (name, args))
        return s_ImpossibleValue
    setattr(cls, name, default_op)

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
