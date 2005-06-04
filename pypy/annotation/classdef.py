"""
Type inference for user-defined classes.
"""

from __future__ import generators
from types import FunctionType
from pypy.annotation.model import SomeImpossibleValue, SomePBC, tracking_unionof


class Attribute:
    # readonly-ness
    # SomeThing-ness
    # more potential sources (pbcs or classes) of information
    # NB. the laziness of 'sources' was required for two reasons:
    #     * some strange attributes exist on classes but are never touched,
    #       immutablevalue() wouldn't be happy with them
    #     * there is an infinite recursion between immutablevalue() and
    #       add_source_for_attribute() for cyclic constant structures.

    def __init__(self, name, bookkeeper):
        self.name = name
        self.bookkeeper = bookkeeper
        self.sources = {} # source -> None or ClassDef
        # XXX a SomeImpossibleValue() constant?  later!!
        self.s_value = SomeImpossibleValue()
        self.readonly = True
        self.read_locations = {}

    def getvalue(self):
        while self.sources:
            source, classdef = self.sources.popitem()
            s_value = self.bookkeeper.immutablevalue(
                source.__dict__[self.name])
            if classdef:
                s_value = s_value.bindcallables(classdef)
            self.s_value = tracking_unionof(self, self.s_value, s_value)
        return self.s_value

    def merge(self, other):
        assert self.name == other.name
        self.sources.update(other.sources)
        self.s_value = tracking_unionof(self, self.s_value, other.s_value)
        self.readonly = self.readonly and other.readonly
        self.read_locations.update(other.read_locations)


class ClassDef:
    "Wraps a user class."

    def __init__(self, cls, bookkeeper):
        self.bookkeeper = bookkeeper
        self.attrs = {}          # {name: Attribute}
        #self.instantiation_locations = {}
        self.cls = cls
        self.subdefs = {}
        base = object
        mixeddict = {}
        sources = {}
        baselist = list(cls.__bases__)
        baselist.reverse()
        self.also_Exception_subclass = False
        if Exception in baselist and len(baselist)>1: # special-case
            baselist.remove(Exception)
            mixeddict['__init__'] = Exception.__init__.im_func
            self.also_Exception_subclass = True

        for b1 in baselist:
            if b1 is object:
                continue
            if getattr(b1, '_mixin_', False):
                assert b1.__bases__ == () or b1.__bases__ == (object,), (
                    "mixin class %r should have no base" % (b1,))
                mixeddict.update(b1.__dict__)
                for name in b1.__dict__:
                    sources[name] = b1
            else:
                assert base is object, ("multiple inheritance only supported "
                                        "with _mixin_: %r" % (cls,))
                base = b1
        mixeddict.update(cls.__dict__)

        self.basedef = bookkeeper.getclassdef(base)
        if self.basedef:
            self.basedef.subdefs[cls] = self

        # collect the (supposed constant) class attributes
        for name, value in mixeddict.items():
            # ignore some special attributes
            if name.startswith('_') and not isinstance(value, FunctionType):
                continue
            if isinstance(value, FunctionType):
                if not hasattr(value, 'class_'):
                    value.class_ = cls # remember that this is really a method
            self.add_source_for_attribute(name, sources.get(name, cls), self)

    def attr_mutated(self, homedef, attrdef): # reflow from attr read positions
        s_newvalue = attrdef.getvalue()
        # check for method demotion
        if isinstance(s_newvalue, SomePBC):
            attr = attrdef.name
            meth = False
            for func, classdef  in s_newvalue.prebuiltinstances.items():
                if isclassdef(classdef):
                    meth = True
                    break
            if meth and getattr(homedef.cls, attr, None) is None:
                self.bookkeeper.warning("demoting method %s to base class %s" % (attrdef.name, homedef))

        for position in attrdef.read_locations:
            self.bookkeeper.annotator.reflowfromposition(position)        

    def add_source_for_attribute(self, attr, source, clsdef=None):
        homedef = self.locate_attribute(attr)
        attrdef = homedef.attrs[attr]
        attrdef.sources[source] = clsdef
        if attrdef.read_locations:
            # we should reflow from all the reader's position,
            # but as an optimization we try to see if the attribute
            # has really been generalized
            s_prev_value = attrdef.s_value
            s_next_value = attrdef.getvalue()
            if s_prev_value != s_next_value:
                self.attr_mutated(homedef, attrdef)

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
        other1 = other
        while other is not None and not issubclass(self.cls, other.cls):
            other = other.basedef
        # special case for MI with Exception
        if not other:
            if issubclass(self.cls, Exception) and issubclass(other1.cls, Exception):
                return self.bookkeeper.getclassdef(Exception)
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

    def issubclass(self, otherclsdef):
        return issubclass(self.cls, otherclsdef.cls)

    def getallsubdefs(self):
        pending = [self]
        seen = {}
        for clsdef in pending:
            yield clsdef
            for sub in clsdef.subdefs.values():
                if sub not in seen:
                    pending.append(sub)
                    seen[sub] = True

##    def getallinstantiations(self):
##        locations = {}
##        for clsdef in self.getallsubdefs():
##            locations.update(clsdef.instantiation_locations)
##        return locations

    def _generalize_attr(self, attr, s_value):
        # first remove the attribute from subclasses -- including us!
        subclass_attrs = []
        for subdef in self.getallsubdefs():
            if attr in subdef.attrs:
                subclass_attrs.append(subdef.attrs[attr])
                del subdef.attrs[attr]

        # do the generalization
        newattr = Attribute(attr, self.bookkeeper)
        if s_value:
            newattr.s_value = s_value
            
        for subattr in subclass_attrs:
            newattr.merge(subattr)
        self.attrs[attr] = newattr

        # reflow from all read positions
        self.attr_mutated(self, newattr)

    def generalize_attr(self, attr, s_value=None):
        # if the attribute exists in a superclass, generalize there.
        for clsdef in self.getmro():
            if attr in clsdef.attrs:
                clsdef._generalize_attr(attr, s_value)
                break
        else:
            self._generalize_attr(attr, s_value)

    def about_attribute(self, name):
        """This is the interface for the code generators to ask about
           the annotation given to a attribute."""
        for cdef in self.getmro():
            if name in cdef.attrs:
                s_result = cdef.attrs[name].s_value
                if s_result != SomeImpossibleValue():
                    return s_result
                else:
                    return None
        return None

    def matching(self, pbc, name):
        d = {}
        uplookup = None
        upfunc = None
        meth = False
        for func, value in pbc.prebuiltinstances.items():
            if isclassdef(value):
                meth = True
                if value is not self and  value.issubclass(self):
                    pass # subclasses methods are always candidates
                elif self.issubclass(value): # upward consider only the best match
                    if uplookup is None or value.issubclass(uplookup):
                        uplookup = value
                        upfunc = func
                    continue
                    # for clsdef1 >= clsdef2
                    # clsdef1.matching(pbc) includes clsdef2.matching(pbc)
                else:
                    continue # not matching
            d[func] = value
        if uplookup is not None:
            d[upfunc] = uplookup
        elif meth:
            self.check_missing_attribute_update(name)
        if d:
            return SomePBC(d)
        else:
            return SomeImpossibleValue()

    def check_missing_attribute_update(self, name):
        # haaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaack
        # sometimes, new methods can show up on classes, added
        # e.g. by W_TypeObject._freeze_() -- the multimethod
        # implementations.  Check that here...
        found = False
        parents = list(self.getmro())
        parents.reverse()
        for base in parents:
            if base.check_attr_here(name):
                found = True
        return found

    def check_attr_here(self, name):
        if name in self.cls.__dict__:
            # oups! new attribute showed up
            self.add_source_for_attribute(name, self.cls, self)
            # maybe it also showed up in some subclass?
            for subdef in self.getallsubdefs():
                if subdef is not self:
                    subdef.check_attr_here(name)
            return True
        else:
            return False

def isclassdef(x):
    return isinstance(x, ClassDef)
