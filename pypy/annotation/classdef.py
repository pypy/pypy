"""
Type inference for user-defined classes.
"""

from __future__ import generators
from types import FunctionType
from pypy.annotation.model import SomeImpossibleValue, unionof, RevDiff

notyet = object()

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

        self.flat = notyet

    def getvalue(self):
        while self.sources:
            self.flat = notyet
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
        self.flat = notyet

    def structure(self):
        s_value = self.getvalue()
        if self.flat is notyet:
            self.flat = s_value.structure()
        return self.flat


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
                cls.__bases__[1:] == (object,) # for baseobjspace.Wrappable
               ), "single inheritance only right now: %r" % (cls,)
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
        was_here = attr in self.attrs
        for subdef in self.getallsubdefs():
            if attr in subdef.attrs:
                subclass_attrs.append(subdef.attrs[attr])
                del subdef.attrs[attr]

        bump = True
        attach_flat = None
        # don't bump if the only cause is rev diff discrepancies
        if was_here and len(subclass_attrs) == 1 and s_value is not None:
            old_attr = subclass_attrs[0]
            wasgeneralenough = old_attr.s_value.contains(s_value)
            assert not wasgeneralenough
            if wasgeneralenough is RevDiff:
                s_value_struct = s_value.structure()
                if not old_attr.flat is notyet:
                    old_attr_struct = old_attr.structure()
                    if s_value_struct == old_attr_struct:
                        bump = False
                attach_flat = s_value_struct

        if bump:
            # bump the revision number of this class and all subclasses           
            for subdef in self.getallsubdefs():
                subdef.revision += 1

        # do the generalization
        newattr = Attribute(attr, self.bookkeeper)
        if s_value:
            newattr.s_value = s_value
            
        for subattr in subclass_attrs:
            newattr.merge(subattr)
        self.attrs[attr] = newattr

        if attach_flat is not None:
            newattr.flat = attach_flat

        # reflow from all factories
        for position in self.getallinstantiations():
            self.bookkeeper.annotator.reflowfromposition(position)

    def generalize_attr(self, attr, s_value=None):
        # if the attribute exists in a superclass, generalize there.
        found = 0
        for clsdef in self.getmro():
            if attr in clsdef.attrs:
                if found == 0:
                    clsdef._generalize_attr(attr, s_value)
                found += 1
        if found == 0:
            self._generalize_attr(attr, s_value)
        else:
            assert found == 1, "generalization itself should prevent this"

    def about_attribute(self, name):
        for cdef in self.getmro():
            if name in cdef.attrs:
                s_result = cdef.attrs[name].s_value
                if s_result != SomeImpossibleValue():
                    return s_result
                else:
                    return None
        return None


def isclassdef(x):
    return isinstance(x, ClassDef)
