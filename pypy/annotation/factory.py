"""
Mutable Objects Factories.

A factory is associated to each point in the source that creates a mutable
object.  The factory remembers how general an object it has to create here.

"""

from __future__ import generators
from types import FunctionType
from pypy.annotation.pairtype import pair
from pypy.annotation.model import SomeImpossibleValue, SomeList
from pypy.annotation.model import SomeObject, SomeInstance
from pypy.annotation.model import unionof, immutablevalue
from pypy.interpreter.miscutils import getthreadlocals


class BlockedInference(Exception):
    """This exception signals the type inference engine that the situation
    is currently blocked, and that it should try to progress elsewhere."""

    def __init__(self):
        try:
            self.break_at = getbookkeeper().position_key
        except AttributeError:
            self.break_at = None


class Bookkeeper:
    """The log of choices that have been made while analysing the operations.
    It ensures that the same 'choice objects' will be returned if we ask
    again during reflowing.  Like ExecutionContext, there is an implicit
    Bookkeeper that can be obtained from a thread-local variable.

    Currently used for factories and user-defined classes."""

    def __init__(self, annotator):
        self.annotator = annotator
        self.creationpoints = {} # map positions-in-blocks to Factories
        self.userclasses = {}    # map classes to ClassDefs
        self.flowgraphs = {}     # map functions to flow graphs

    def enter(self, position_key):
        """Start of an operation.
        The operation is uniquely identified by the given key."""
        self.position_key = position_key
        self.choice_id = 0
        getthreadlocals().bookkeeper = self

    def leave(self):
        """End of an operation."""
        del getthreadlocals().bookkeeper
        del self.position_key
        del self.choice_id

    def nextchoice(self):
        """Get the next choice key.  The keys are unique, but they follow
        the same sequence while reflowing."""
        # 'position_key' is an arbitrary key that identifies a specific
        # operation, but calling nextchoice() several times during the same
        # operation returns a different choice key.
        key = self.position_key, self.choice_id
        self.choice_id += 1
        return key

    def getfactory(self, factorycls, *factoryargs):
        """Get the Factory associated with the current position,
        or if it doesn't exist yet build it with factorycls(*factoryargs)."""
        key = self.nextchoice()
        try:
            return self.creationpoints[key]
        except KeyError:
            factory = factorycls(*factoryargs)
            factory.position_key = self.position_key
            self.creationpoints[key] = factory
            return factory

    def getclassdef(self, cls):
        """Get the ClassDef associated with the given user cls."""
        if cls is object:
            return None
        try:
            return self.userclasses[cls]
        except KeyError:
            self.userclasses[cls] = ClassDef(cls, self)
            return self.userclasses[cls]

    def getflowgraph(self, func):
        """Get the flow graph associated with the given Python func."""
        try:
            return self.flowgraphs[func]
        except KeyError:
            self.flowgraphs[func] = self.annotator.buildflowgraph(func)
            return self.flowgraphs[func]


def getbookkeeper():
    """Get the current Bookkeeper.
    Only works during the analysis of an operation."""
    return getthreadlocals().bookkeeper


#
#  Factories
#

class ListFactory:
    s_item = SomeImpossibleValue()

    def create(self):
        return SomeList(factories = {self: True}, s_item = self.s_item)

    def generalize(self, s_new_item, bookkeeper=None):
        self.s_item = unionof(self.s_item, s_new_item)
        if bookkeeper:
            bookkeeper.annotator.reflowfromposition(self.position_key)


class FuncCallFactory:

    def pycall(self, func, arglist):
        bookkeeper = getbookkeeper()
        graph = bookkeeper.getflowgraph(func)
        graph.funccallfactories[self] = True
        bookkeeper.annotator.generalizeinputargs(graph, arglist)
        return bookkeeper.annotator.getoutputvalue(graph)


class InstanceFactory:

    def __init__(self, cls):
        self.classdef = getbookkeeper().getclassdef(cls)
        self.classdef.instancefactories[self] = True

    def create(self):
        return SomeInstance(self.classdef)


class ClassDef:
    "Wraps a user class."

    def __init__(self, cls, bookkeeper):
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
        self.basedef = bookkeeper.getclassdef(base)
        if self.basedef:
            self.basedef.subdefs[cls] = self
        # collect the (supposed constant) class attributes
        s_self = SomeInstance(self)
        for name, value in cls.__dict__.items():
            # ignore some special attributes
            if name.startswith('_') and not isinstance(value, FunctionType):
                continue
            # although self.getallfactories() is currently empty,
            # the following might still invalidate some blocks if it
            # generalizes existing values in parent classes
            s_value = immutablevalue(value)
            self.generalize(name, s_value, bookkeeper)

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

    def generalize(self, attr, s_value, bookkeeper=None):
        # we make sure that an attribute never appears both in a class
        # and in some subclass, in two steps:
        # (1) check if the attribute is already in a superclass
        for clsdef in self.getmro():
            if attr in clsdef.attrs:
                self = clsdef   # generalize the parent class instead
                break
        # (2) remove the attribute from subclasses
        subclass_values = []
        for subdef in self.getallsubdefs():
            if attr in subdef.attrs:
                subclass_values.append(subdef.attrs[attr])
                del subdef.attrs[attr]
            # bump the revision number of this class and all subclasses
            subdef.revision += 1
        self.attrs[attr] = unionof(s_value, *subclass_values)
        # reflow from all factories
        if bookkeeper:
            for factory in self.getallfactories():
                bookkeeper.annotator.reflowfromposition(factory.position_key)
