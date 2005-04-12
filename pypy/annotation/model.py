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
from pypy.objspace.flow.model import Constant
import inspect


DEBUG = True    # set to False to disable recording of debugging information


class SomeObject:
    """The set of all objects.  Each instance stands
    for an arbitrary object about which nothing is known."""
    __metaclass__ = extendabletype
    knowntype = object
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.__dict__  == other.__dict__)
    def __ne__(self, other):
        return not (self == other)
    def __repr__(self):
        items = self.__dict__.items()
        items.sort()
        args = []
        for k, v in items:
            m = getattr(self, 'fmt_' + k, repr)
            r = m(v)
            if r is not None:
                args.append('%s=%s'%(k, r))
        kwds = ', '.join(args)
        return '%s(%s)' % (self.__class__.__name__, kwds)

    def fmt_knowntype(self, t):
        return t.__name__
    
    def contains(self, other):
        return self == other or pair(self, other).union() == self

    def is_constant(self):
        return hasattr(self, 'const')

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
    origin = property(origin)
    def caused_by_merge(self):
        return SomeObject._coming_from.get(id(self), (None, None))[1]
    def set_caused_by_merge(self, nvalue):
        SomeObject._coming_from[id(self)] = self.origin, nvalue
    caused_by_merge = property(caused_by_merge, set_caused_by_merge)
    del set_caused_by_merge


class SomeFloat(SomeObject):
    "Stands for a float or an integer."
    knowntype = float   # if we don't know if it's a float or an int,
                        # pretend it's a float.


class SomeInteger(SomeFloat):
    "Stands for an object which is known to be an integer."
    knowntype = int
    def __init__(self, nonneg=False, unsigned=False):
        self.nonneg = unsigned or nonneg
        self.unsigned = unsigned  # pypy.tool.rarithmetic.r_uint


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
    def __init__(self, can_be_None=False):
        self.can_be_None = can_be_None


class SomeChar(SomeString):
    "Stands for an object known to be a string of length 1."


class SomeList(SomeObject):
    "Stands for a homogenous list of any length."
    knowntype = list
    def __init__(self, factories, s_item=SomeObject()):
        self.factories = factories
        self.s_item = s_item     # general enough for any element


class SomeSlice(SomeObject):
    knowntype = slice
    def __init__(self, start, stop, step):
        self.start = start
        self.stop = stop
        self.step = step


class SomeTuple(SomeObject):
    "Stands for a tuple of known length."
    knowntype = tuple
    def __init__(self, items):
        self.items = tuple(items)   # tuple of s_xxx elements
        for i in items:
            if not i.is_constant():
                break
        else:
            self.const = tuple([i.const for i in items])


class SomeDict(SomeObject):
    "Stands for a dict."
    knowntype = dict
    def __init__(self, factories, s_key, s_value):
        self.factories = factories
        self.s_key = s_key
        self.s_value = s_value


class SomeIterator(SomeObject):
    "Stands for an iterator returning objects of a known type."
    knowntype = type(iter([]))  # arbitrarily chose seqiter as the type
    def __init__(self, s_item=SomeObject()):
        self.s_item = s_item


class SomeInstance(SomeObject):
    "Stands for an instance of a (user-defined) class."
    def __init__(self, classdef, can_be_None=False):
        self.classdef = classdef
        self.knowntype = classdef.cls
        self.can_be_None = can_be_None
    def fmt_knowntype(self, kt):
        return None
    def fmt_classdef(self, cd):
        return cd.cls.__name__

def new_or_old_class(c):
    if hasattr(c, '__class__'):
        return c.__class__
    else:
        return type(c)


class SomePBC(SomeObject):
    """Stands for a global user instance, built prior to the analysis,
    or a set of such instances."""
    def __init__(self, prebuiltinstances):
        # prebuiltinstances is a dictionary containing concrete python
        # objects as keys.
        # if the key is a function, the value can be a classdef to
        # indicate that it is really a method.
        prebuiltinstances = prebuiltinstances.copy()
        self.prebuiltinstances = prebuiltinstances
        self.simplify()
        if self.isNone():
            self.knowntype = type(None)
        else:
            self.knowntype = reduce(commonbase,
                                    [new_or_old_class(x)
                                     for x in prebuiltinstances
                                     if x is not None])
        if prebuiltinstances.values() == [True]:
            # hack for the convenience of direct callers to SomePBC():
            # only if there is a single object in prebuiltinstances and
            # it doesn't have an associated ClassDef
            self.const, = prebuiltinstances
    def simplify(self):
        # We check that the dictionary does not contain at the same time
        # a function bound to a classdef, and constant bound method objects
        # on that class.
        for x, ignored in self.prebuiltinstances.items():
            if isinstance(x, MethodType) and x.im_func in self.prebuiltinstances:
                classdef = self.prebuiltinstances[x.im_func]
                if isinstance(x.im_self, classdef.cls):
                    del self.prebuiltinstances[x]

    def isNone(self):
        return self.prebuiltinstances == {None:True}

    def fmt_prebuiltinstances(self, pbis):
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
    def __init__(self, analyser, s_self=None):
        self.analyser = analyser
        self.s_self = s_self


class SomeImpossibleValue(SomeObject):
    """The empty set.  Instances are placeholders for objects that
    will never show up at run-time, e.g. elements of an empty list."""
    def __init__(self, benign=False):
        self.benign = benign


def unionof(*somevalues):
    "The most precise SomeValue instance that contains all the values."
    s1 = SomeImpossibleValue(benign=len(somevalues)>0)
    for s2 in somevalues:
        if s1 != s2:
            s1 = pair(s1, s2).union()
    if DEBUG and s1.caused_by_merge is None and len(somevalues) > 1:
        s1.caused_by_merge = somevalues
    return s1

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
        #print '* warning, no type available for %s(%s)' % (
        #    name, ', '.join([repr(a) for a in args]))
        return SomeObject()
    setattr(cls, name, default_op)

# this has the side-effect of registering the unary and binary operations
from pypy.annotation.unaryop  import UNARY_OPERATIONS
from pypy.annotation.binaryop import BINARY_OPERATIONS
