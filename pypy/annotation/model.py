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


from types import ClassType, BuiltinFunctionType, FunctionType, MethodType
from types import InstanceType
import pypy
from pypy.annotation.pairtype import pair, extendabletype
from pypy.objspace.flow.model import Constant
from pypy.tool.cache import Cache 
import inspect


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
        kwds = ', '.join(['%s=%r' % item for item in self.__dict__.items()])
        return '%s(%s)' % (self.__class__.__name__, kwds)
    def contains(self, other):
        return self == other or pair(self, other).union() == self
    def is_constant(self):
        return hasattr(self, 'const')

    # for debugging, record where each instance comes from
    _coming_from = {}
    def __new__(cls, *args, **kw):
        self = super(SomeObject, cls).__new__(cls, *args, **kw)
        try:
            position_key = pypy.annotation.factory.getbookkeeper().position_key
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


class SomeNone(SomeObject):
    "Stands for None."
    knowntype = type(None)
    const = None


class SomeInteger(SomeObject):
    "Stands for an object which is known to be an integer."
    knowntype = int
    def __init__(self, nonneg=False, unsigned=False):
        self.nonneg = nonneg
        self.unsigned = unsigned  # pypy.objspace.std.restricted_int.r_uint


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


class SomeChar(SomeString):
    "Stands for an object known to be a string of length 1."


class SomeList(SomeObject):
    "Stands for a homogenous list of any length."
    knowntype = list
    def __init__(self, factories, s_item=SomeObject()):
        self.factories = factories
        self.s_item = s_item     # general enough for any element


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
    "Stands for a dict with known keys."
    knowntype = dict
    def __init__(self, factories, items):
        self.factories = factories
        self.items = items    # dict {realkey: s_value}


class SomeIterator(SomeObject):
    "Stands for an iterator returning objects of a known type."
    knowntype = type(iter([]))  # arbitrarily chose seqiter as the type
    def __init__(self, s_item=SomeObject()):
        self.s_item = s_item


class SomeInstance(SomeObject):
    "Stands for an instance of a (user-defined) class."
    def __init__(self, classdef):
        self.classdef = classdef
        self.knowntype = classdef.cls
        self.revision = classdef.revision


class SomeCallable(SomeObject):
    """Stands for a (callable) function, method, 
    prebuiltconstant or class"""
    def __init__(self, callables):
        # callables is a dictionary containing concrete python 
        # callable objects as keys and - in the case of a method - 
        # the value contains the classdef (see SomeMethod below) 
        self.callables = callables
        if len(callables) == 1:
            self.const, = callables


class SomeBuiltin(SomeCallable):
    "Stands for a built-in function or method with special-cased analysis."
    knowntype = BuiltinFunctionType  # == BuiltinMethodType
    def __init__(self, analyser, s_self=None):
        self.analyser = analyser
        self.s_self = s_self


class SomePBC(SomeObject):
    """Stands for a global user instance, built prior to the analysis,
    or a set of such instances."""
    def __init__(self, prebuiltinstances):
        self.prebuiltinstances = prebuiltinstances  
        self.knowntype = reduce(commonbase,
                                [x.__class__ for x in prebuiltinstances])


class SomeImpossibleValue(SomeObject):
    """The empty set.  Instances are placeholders for objects that
    will never show up at run-time, e.g. elements of an empty list."""


def unionof(*somevalues):
    "The most precise SomeValue instance that contains all the values."
    s1 = SomeImpossibleValue()
    for s2 in somevalues:
        if s1 != s2:
            s1 = pair(s1, s2).union()
    if s1.caused_by_merge is None and len(somevalues) > 1:
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
from pypy.annotation.builtin  import BUILTIN_ANALYZERS
