"""
Mutable Objects Factories.

A factory is associated to an SpaceOperation in the source that creates a
mutable object, currently 'newlist' and 'call' (which can build instances).
The factory remembers how general an object it has to create here.
"""

from __future__ import generators
import new
from types import FunctionType, ClassType, MethodType
from pypy.annotation.model import SomeImpossibleValue, SomeList, SomeDict
from pypy.annotation.model import SomeObject, SomeInstance
from pypy.annotation.model import unionof, immutablevalue
from pypy.interpreter.miscutils import getthreadlocals
from pypy.interpreter.pycode import CO_VARARGS


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
        self.creationpoints = {} # map position-in-a-block to its Factory
        self.userclasses = {}    # map classes to ClassDefs
        self.userclasseslist = []# userclasses.keys() in creation order
        self.attrs_read_from_constants = {}
        self.cachespecializedfunctions = {}

    def enter(self, position_key):
        """Start of an operation.
        The operation is uniquely identified by the given key."""
        self.position_key = position_key
        getthreadlocals().bookkeeper = self

    def leave(self):
        """End of an operation."""
        del getthreadlocals().bookkeeper
        del self.position_key

    def getfactory(self, factorycls):
        """Get the Factory associated with the current position,
        or build it if it doesn't exist yet."""
        try:
            factory = self.creationpoints[self.position_key]
        except KeyError:
            factory = factorycls()
            factory.bookkeeper = self
            factory.position_key = self.position_key
            self.creationpoints[self.position_key] = factory
        assert isinstance(factory, factorycls)
        return factory

    def getclassdef(self, cls):
        """Get the ClassDef associated with the given user cls."""
        if cls is object:
            return None
        try:
            return self.userclasses[cls]
        except KeyError:
            cdef = ClassDef(cls, self)
            self.userclasses[cls] = cdef
            self.userclasseslist.append(cdef)
            return self.userclasses[cls]


def getbookkeeper():
    """Get the current Bookkeeper.
    Only works during the analysis of an operation."""
    return getthreadlocals().bookkeeper


#
#  Factories
#

def generalize(factories, *args):
    modified = [factory for factory in factories if factory.generalize(*args)]
    if modified:
        for factory in modified:
            factory.bookkeeper.annotator.reflowfromposition(factory.position_key)
        raise BlockedInference   # reflow now

def isclassdef(x):
    return isinstance(x, ClassDef) 

class ListFactory:
    s_item = SomeImpossibleValue()

    def __repr__(self):
        return '%s(s_item=%r)' % (self.__class__.__name__, self.s_item)
    
    def create(self):
        return SomeList(factories = {self: True}, s_item = self.s_item)

    def generalize(self, s_new_item):
        if not self.s_item.contains(s_new_item):
            self.s_item = unionof(self.s_item, s_new_item)
            return True
        else:
            return False


class DictFactory:
    items = {}

    def __repr__(self):
        return '%s(items=%r)' % (self.__class__.__name__, self.items)

    def create(self):
        return SomeDict(factories = {self: True}, items = self.items)

    def generalize(self, key, s_new_value):
        self.items = self.items.copy()
        if key not in self.items:
            self.items[key] = s_new_value
            return True
        elif not self.items[key].contains(s_new_value):
            self.items[key] = unionof(self.items[key], s_new_value)
            return True
        else:
            return False


class CallableFactory: 
    def pycall(self, func, *args):
        if isinstance(func, (type, ClassType)) and \
            func.__module__ != '__builtin__':
            cls = func 
            classdef = self.bookkeeper.getclassdef(cls)
            classdef.instancefactories[self] = True
            s_instance = SomeInstance(classdef)
            # flow into __init__() if the class has got one
            init = getattr(cls, '__init__', None)
            if init is not None and init != object.__init__:
                self.pycall(init, s_instance, *args)
            else:
                assert not args, "no __init__ found in %r" % (cls,)
            return s_instance
        if hasattr(func, '__call__') and \
           isinstance(func.__call__, MethodType): 
            func = func.__call__
        if hasattr(func, 'im_func'):
            if func.im_self is not None:
                s_self = immutablevalue(func.im_self)
                args = [s_self] + list(args)
            func = func.im_func
        assert isinstance(func, FunctionType), "expected function, got %r"%func
        # do we need to specialize this function in several versions?
        x = getattr(func, 'specialize', False)
        if x: 
            if x == 'argtypes':
                key = "_".join([arg.__class__.__name__ for arg in args])
                name = func.__name__+'_'+key
                func = self.specialize_by_key(func, key, name) 
            else:
                # fully specialize: create one version per call position
                func = self.specialize_by_key(func, self.position_key)
            
        elif func.func_code.co_flags & CO_VARARGS:
            # calls to *arg functions: create one version per number of args
            func = self.specialize_by_key(func, len(args),
                                          name='%s__%d' % (func.func_name,
                                                           len(args)))
        return self.bookkeeper.annotator.recursivecall(func, self, *args)

    def specialize_by_key(self, func, key, name=None):
        key = func, key
        try:
            func = self.bookkeeper.cachespecializedfunctions[key]
        except KeyError:
            # XXX XXX XXX HAAAAAAAAAAAACK
            self.bookkeeper.annotator.translator.getflowgraph(func)
            func = new.function(func.func_code, 
                                func.func_globals, 
                                name or func.func_name, 
                                func.func_defaults, 
                                func.func_closure)
            self.bookkeeper.cachespecializedfunctions[key] = func
        return func

class ClassDef:
    "Wraps a user class."

    def __init__(self, cls, bookkeeper):
        self.attrs = {}          # attrs is updated with new information
        self.readonly = {}       # {attr: True-or-False}
        self.revision = 0        # which increases the revision number
        self.instancefactories = {}
        self.cls = cls
        self.subdefs = {}
        assert (len(cls.__bases__) <= 1 or
                cls.__bases__[1:] == (object,),   # for baseobjspace.Wrappable
                "single inheritance only right now: %r" % (cls,))
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
            s_value = s_value.bindcallables(self)
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

    def generalize(self, attr, s_value, bookkeeper=None, readonly=True):
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
                readonly = readonly and subdef.readonly[attr]
                del subdef.attrs[attr]
                del subdef.readonly[attr]
            # bump the revision number of this class and all subclasses
            subdef.revision += 1
        self.attrs[attr] = unionof(s_value, *subclass_values)
        self.readonly[attr] = readonly
        # reflow from all factories
        if bookkeeper:
            for factory in self.getallfactories():
                bookkeeper.annotator.reflowfromposition(factory.position_key)

from pypy.annotation.builtin  import BUILTIN_ANALYZERS
