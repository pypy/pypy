"""
Mutable Objects Factories.

A factory is associated to an SpaceOperation in the source that creates a
mutable object, currently 'newlist' and 'call' (which can build instances).
The factory remembers how general an object it has to create here.
"""

from __future__ import generators
import new
from types import FunctionType, ClassType, MethodType
from pypy.annotation.model import *
from pypy.interpreter.miscutils import getthreadlocals
from pypy.interpreter.pycode import CO_VARARGS
from pypy.tool.hack import func_with_new_name

def ishashable(x):
    try:
        hash(x)
    except TypeError:
        return False
    else:
        return True

class BlockedInference(Exception):
    """This exception signals the type inference engine that the situation
    is currently blocked, and that it should try to progress elsewhere."""

    def __init__(self):
        try:
            self.break_at = getbookkeeper().position_key
        except AttributeError:
            self.break_at = None

    def __repr__(self):
        return "<BlockedInference break_at %r>" %(self.break_at,)
    __str__ = __repr__

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
        self.cachespecializations = {}

    def enter(self, position_key):
        """Start of an operation.
        The operation is uniquely identified by the given key."""
        self.position_key = position_key
        getthreadlocals().bookkeeper = self

    def leave(self):
        """End of an operation."""
        del getthreadlocals().bookkeeper
        del self.position_key

    def is_in_an_operation(self):
        return hasattr(self, 'position_key')

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


    def immutablevalue(self, x):
        """The most precise SomeValue instance that contains the
        immutable value x."""
        tp = type(x)
        if tp is bool:
            result = SomeBool()
        elif tp is int:
            result = SomeInteger(nonneg = x>=0)
        elif tp is str:
            result = SomeString()
        elif tp is tuple:
            result = SomeTuple(items = [self.immutablevalue(e) for e in x])
        elif tp is list:
            items_s = [self.immutablevalue(e) for e in x]
            result = SomeList({}, unionof(*items_s))
        elif tp is dict:   # exactly a dict
            items = {}
            for key, value in x.items():
                items[key] = self.immutablevalue(value)
            result = SomeDict({}, items)
        elif ishashable(x) and x in BUILTIN_ANALYZERS:
            result = SomeBuiltin(BUILTIN_ANALYZERS[x])
        elif callable(x) or isinstance(x, staticmethod): # XXX
            # maybe 'x' is a method bound to a not-yet-frozen cache?
            # fun fun fun.
            if (hasattr(x, 'im_self') and isinstance(x.im_self, Cache)
                and not x.im_self.frozen):
                x.im_self.freeze()
            if hasattr(x, '__self__') and x.__self__ is not None:
                s_self = self.immutablevalue(x.__self__)
                # stop infinite recursion getattr<->immutablevalue
                del s_self.const
                s_name = self.immutablevalue(x.__name__)
                result = s_self.getattr(s_name)
            else:
                result = SomePBC({x : True})
        elif hasattr(x, '__class__') \
                 and x.__class__.__module__ != '__builtin__':
            if isinstance(x, Cache) and not x.frozen:
                x.freeze()
            result = SomePBC({x: True}) # pre-built inst
            clsdef = self.getclassdef(x.__class__)
            for attr in x.__dict__:
                clsdef.add_source_for_attribute(attr, x)
        elif x is None:
            result = SomeNone()
        else:
            result = SomeObject()
        result.const = x
        return result

    def valueoftype(self, t):
        """The most precise SomeValue instance that contains all
        objects of type t."""
        if t is bool:
            return SomeBool()
        elif t is int:
            return SomeInteger()
        elif t is str:
            return SomeString()
        elif t is list:
            return SomeList(factories={})
        # can't do dict, tuple
        elif isinstance(t, (type, ClassType)) and \
                 t.__module__ != '__builtin__':
            classdef = self.getclassdef(t)
            if self.is_in_an_operation():
                # woha! instantiating a "mutable" SomeXxx like
                # SomeInstance is always dangerous, because we need to
                # allow reflowing from the current operation if/when
                # the classdef later changes.
                classdef.instantiation_locations[self.position_key] = True
            return SomeInstance(classdef)
        else:
            o = SomeObject()
            o.knowntype = t
            return o

    def pycall(self, func, *args):
        if isinstance(func, (type, ClassType)) and \
            func.__module__ != '__builtin__':
            cls = func
            x = getattr(cls, "_specialize_", False)
            if x:
                if x == "location":
                    cls = self.specialize_by_key(cls, self.position_key)
                else:
                    raise Exception, \
                          "unsupported specialization type '%s'"%(x,)

            classdef = self.getclassdef(cls)
            classdef.instantiation_locations[self.position_key] = True 
            s_instance = SomeInstance(classdef)
            # flow into __init__() if the class has got one
            init = getattr(cls, '__init__', None)
            if init is not None and init != object.__init__:
                attrdef = classdef.find_attribute('__init__')
                attrdef.getvalue()
                self.pycall(init, s_instance, *args)
            else:
                assert not args, "no __init__ found in %r" % (cls,)
            return s_instance
        if hasattr(func, '__call__') and \
           isinstance(func.__call__, MethodType):
            func = func.__call__
        if hasattr(func, 'im_func'):
            if func.im_self is not None:
                s_self = self.immutablevalue(func.im_self)
                args = [s_self] + list(args)
            try:
                func.im_func.class_ = func.im_class
            except AttributeError:
                # probably a builtin function, we don't care to preserve
                # class information then
                pass
            func = func.im_func
        assert isinstance(func, FunctionType), "expected function, got %r"%func
        # do we need to specialize this function in several versions?
        x = getattr(func, '_specialize_', False)
        #if not x: 
        #    x = 'argtypes'
        if x:
            if x == 'argtypes':
                key = short_type_name(args)
                func = self.specialize_by_key(func, key,
                                              func.__name__+'__'+key)
            elif x == "location":
                # fully specialize: create one version per call position
                func = self.specialize_by_key(func, self.position_key)
            else:
                raise Exception, "unsupported specialization type '%s'"%(x,)

        elif func.func_code.co_flags & CO_VARARGS:
            # calls to *arg functions: create one version per number of args
            func = self.specialize_by_key(func, len(args),
                                          name='%s__%d' % (func.func_name,
                                                           len(args)))
        return self.annotator.recursivecall(func, self.position_key, *args)

    def specialize_by_key(self, thing, key, name=None):
        key = thing, key
        try:
            thing = self.cachespecializations[key]
        except KeyError:
            if isinstance(thing, FunctionType):
                # XXX XXX XXX HAAAAAAAAAAAACK
                self.annotator.translator.getflowgraph(thing)
                thing = func_with_new_name(thing, name or thing.func_name)
            elif isinstance(thing, (type, ClassType)):
                assert not "not working yet"
                thing = type(thing)(name or thing.__name__, (thing,))
            else:
                raise Exception, "specializing %r?? why??"%thing
            self.cachespecializations[key] = thing
        return thing
        

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

def short_type_name(args):
    l = []
    for x in args:
        if isinstance(x, SomeInstance) and hasattr(x, 'knowntype'):
            name = "SI_" + x.knowntype.__name__
        else:
            name = x.__class__.__name__
        l.append(name)
    return "__".join(l)


class Attribute:
    # readonly-ness
    # SomeThing-ness
    # more potential sources (pbcs or classes) of information

    def __init__(self, name, bookkeeper):
        self.name = name
        self.bookkeeper = bookkeeper
        self.sources = {} # source -> None or ClassDef
        # XXX a SomeImpossibleValue() constant?  later!!
        self.s_value = SomeImpossibleValue()
        self.readonly = True

    def getvalue(self):
        while self.sources:
            source, classdef = self.sources.popitem()
            s_value = self.bookkeeper.immutablevalue(
                source.__dict__[self.name])
            if classdef:
                s_value = s_value.bindcallables(classdef)
            self.s_value = unionof(self.s_value, s_value)
        return self.s_value

    def merge(self, other):
        assert self.name == other.name
        self.sources.update(other.sources)
        self.s_value = unionof(self.s_value, other.s_value)
        self.readonly = self.readonly and other.readonly


class ClassDef:
    "Wraps a user class."

    def __init__(self, cls, bookkeeper):
        self.bookkeeper = bookkeeper
        self.attrs = {}          # {name: Attribute}
        self.revision = 0        # which increases the revision number
        self.instantiation_locations = {}
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
        for name, value in cls.__dict__.items():
            # ignore some special attributes
            if name.startswith('_') and not isinstance(value, FunctionType):
                continue
            if isinstance(value, FunctionType):
                value.class_ = cls # remember that this is really a method
            self.add_source_for_attribute(name, cls, self)

    def add_source_for_attribute(self, attr, source, clsdef=None):
        self.find_attribute(attr).sources[source] = clsdef

    def locate_attribute(self, attr):
        for cdef in self.getmro():
            if attr in cdef.attrs:
                return cdef
        self.generalize_attr(attr)
        return self

    def find_attribute(self, attr):
        return self.locate_attribute(attr).attrs[attr]
    
    def __repr__(self):
        return "<ClassDef '%s.%s'>" % (self.cls.__module__, self.cls.__name__)

    def commonbase(self, other):
        while other is not None and not issubclass(self.cls, other.cls):
            other = other.basedef
        return other

    def superdef_containing(self, cls):
        clsdef = self
        while clsdef is not None and not issubclass(cls, clsdef.cls):
            clsdef = clsdef.basedef
        return clsdef

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

    def getallinstantiations(self):
        locations = {}
        for clsdef in self.getallsubdefs():
            locations.update(clsdef.instantiation_locations)
        return locations

    def _generalize_attr(self, attr, s_value):
        # first remove the attribute from subclasses -- including us!
        subclass_attrs = []
        for subdef in self.getallsubdefs():
            if attr in subdef.attrs:
                subclass_attrs.append(subdef.attrs[attr])
                del subdef.attrs[attr]
            # bump the revision number of this class and all subclasses
            subdef.revision += 1

        # do the generalization
        newattr = Attribute(attr, self.bookkeeper)
        if s_value:
            newattr.s_value = s_value
            
        for subattr in subclass_attrs:
            newattr.merge(subattr)
        self.attrs[attr] = newattr

        # reflow from all factories
        for position in self.getallinstantiations():
            self.bookkeeper.annotator.reflowfromposition(position)

    def generalize_attr(self, attr, s_value=None):
        # if the attribute exists in a superclass, generalize there.
        for clsdef in self.getmro():
            if attr in clsdef.attrs:
                clsdef._generalize_attr(attr, s_value)
        else:
            self._generalize_attr(attr, s_value)

    def about_attribute(self, name):
        for cdef in self.getmro():
            if name in cdef.attrs:
                return cdef.attrs[name]
        return None



from pypy.annotation.builtin import BUILTIN_ANALYZERS
