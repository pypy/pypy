"""
Mutable Objects Factories.

A factory is associated to each point in the source that creates a mutable
object.  The factory remembers how general an object it has to create here.

"""

from __future__ import generators
from pypy.annotation.pairtype import pair
from pypy.annotation.model import SomeImpossibleValue, SomeList
from pypy.annotation.model import SomeObject, SomeInstance


class BlockedInference(Exception):
    """This exception signals the type inference engine that the situation
    is currently blocked, and that it should try to progress elsewhere."""

    def __init__(self, factories = ()):
        # factories that need to be invalidated
        self.invalidatefactories = factories


#
#  Factories
#

class ListFactory:
    s_item = SomeImpossibleValue()

    def create(self):
        return SomeList(factories = {self: True}, s_item = self.s_item)

    def generalize(self, s_new_item):
        self.s_item = pair(self.s_item, s_new_item).union()


class InstanceFactory:

    def __init__(self, cls, userclasses):
        self.classdef = getclassdef(cls, userclasses)
        self.classdef.instancefactories[self] = True

    def create(self):
        return SomeInstance(self.classdef)


class ClassDef:
    "Wraps a user class."

    def __init__(self, cls, userclasses):
        self.attrs = {}          # attrs is updated with new information
        self.revision = 0        # which increases the revision number
        self.instancefactories = {}
        self.cls = cls
        self.subdefs = {}
        assert len(cls.__bases__) <= 1, "single inheritance only right now"
        if cls.__bases__:
            base = cls.__bases__[0]
        else:
            base = object
        self.basedef = getclassdef(base, userclasses)
        if self.basedef:
            self.basedef.subdefs[cls] = self

    def __repr__(self):
        return '<ClassDef %s.%s>' % (self.cls.__module__, self.cls.__name__)

    def commonbase(self, other):
        while other is not None and not issubclass(self.cls, other.cls):
            other = other.basedef
        return other

    def getmro(self):
        while self is not None:
            yield self
            self = self.basedef

    def getallsubdefs(self):
        pending = [self]
        seen = {}
        for clsdef in pending:
            yield clsdef
            for sub in clsdef.subdefs.values():
                if sub not in seen:
                    pending.append(sub)
                    seen[sub] = True

    def getallfactories(self):
        factories = {}
        for clsdef in self.getallsubdefs():
            factories.update(clsdef.instancefactories)
        return factories

    def generalize(self, attr, s_value):
        # we make sure that an attribute never appears both in a class
        # and in some subclass, in two steps:
        # (1) assert that the attribute is in no superclass
        for clsdef in self.getmro():
            assert clsdef is self or attr not in clsdef.attrs
        # (2) remove the attribute from subclasses
        for subdef in self.getallsubdefs():
            if attr in subdef.attrs:
                s_value = pair(s_value, subdef.attrs[attr]).union()
                del subdef.attrs[attr]
            # bump the revision number of this class and all subclasses
            subdef.revision += 1
        self.attrs[attr] = s_value


def getclassdef(cls, cache):
    if cls is object:
        return None
    try:
        return cache[cls]
    except KeyError:
        cache[cls] = ClassDef(cls, cache)
        return cache[cls]
