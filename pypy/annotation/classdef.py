"""
Type inference for user-defined classes.
"""

from __future__ import generators
from types import FunctionType
from pypy.annotation.model import SomeImpossibleValue, SomePBC, tracking_unionof
from pypy.annotation.model import SomeInteger


# The main purpose of a ClassDef is to collect information about class/instance
# attributes as they are really used.  An Attribute object is stored in the
# most general ClassDef where an attribute of that name is read/written:
#    classdef.attrs = {'attrname': Attribute()}
#
# The following invariants hold:
#
# (A) if an attribute is read/written on an instance of class A, then the
#     classdef of A or a parent class of A has an Attribute object corresponding
#     to that name.
#
# (I) if B is a subclass of A, then they don't have both an Attribute for the
#     same name.  (All information from B's Attribute must be merged into A's.)
#
# Additionally, each ClassDef records an 'attr_sources': it maps attribute
# names to a set of objects that want to provide a constant value for this
# attribute at the level of this class.  The attrsources provide information
# higher in the class hierarchy than concrete Attribute()s.  It is for the case
# where (so far or definitely) the user program only reads/writes the attribute
# at the level of a subclass, but a value for this attribute could possibly
# exist in the parent class or in an instance of a parent class.
#
# The point of not automatically forcing the Attribute instance up to the
# parent class which has a class attribute of the same name is apparent with
# multiple subclasses:
#
#                                    A
#                                 attr=s1
#                                  /   \
#                                 /     \
#                                B       C
#                             attr=s2  attr=s3
#
# In this case, as long as 'attr' is only read/written from B or C, the
# Attribute on B says that it can be 's1 or s2', and the Attribute on C says
# it can be 's1 or s3'.  Merging them into a single Attribute on A would give
# the more imprecise 's1 or s2 or s3'.
#
# The following invariant holds:
#
# (II) if a class A has an Attribute, the 'attrsources' for the same name is
#      empty.  It is also empty on all subclasses of A.  (The information goes
#      into the Attribute directly in this case.)
#
# The attrsources have the format {object: classdef}.  For class attributes,
# 'object' is the class in question and 'classdef' its corresponding classdef,
# used for binding methods.  For attribute sources that are prebuilt instances,
# 'classdef' is None.
#
# The following invariant holds:
#
#  (III) for a class A, each attrsource that comes from the class (as opposed to
#        from a prebuilt instance) must be merged into all Attributes of the
#        same name in all subclasses of A, if any.  (Parent class attributes can
#        be visible in reads from instances of subclasses.)


class Attribute:
    # readonly-ness
    # SomeThing-ness
    # NB.  an attribute is readonly if it is a constant class attribute.
    #      Both writing to the instance attribute and discovering prebuilt
    #      instances that have the attribute set will turn off readonly-ness.

    def __init__(self, name, bookkeeper):
        self.name = name
        self.bookkeeper = bookkeeper
        # XXX a SomeImpossibleValue() constant?  later!!
        self.s_value = SomeImpossibleValue()
        self.readonly = True
        self.read_locations = {}

    def add_constant_source(self, source, classdef):
        s_value = self.bookkeeper.immutablevalue(
            source.__dict__[self.name])
        if classdef:
            s_value = s_value.bindcallables(classdef)
        else:
            # a prebuilt instance source forces readonly=False, see above
            self.readonly = False
        self.s_value = tracking_unionof(self, self.s_value, s_value)

    def getvalue(self):
        # Same as 'self.s_value' for historical reasons.
        return self.s_value

    def merge(self, other):
        assert self.name == other.name
        self.s_value = tracking_unionof(self, self.s_value, other.s_value)
        self.readonly = self.readonly and other.readonly
        self.read_locations.update(other.read_locations)

    def mutated(self, homedef): # reflow from attr read positions
        s_newvalue = self.getvalue()
        # check for method demotion
        if isinstance(s_newvalue, SomePBC):
            attr = self.name
            meth = False
            for func, classdef  in s_newvalue.prebuiltinstances.items():
                if isclassdef(classdef):
                    meth = True
                    break
            if meth and getattr(homedef.cls, attr, None) is None:
                self.bookkeeper.warning("demoting method %s to base class %s" % (self.name, homedef))

        for position in self.read_locations:
            self.bookkeeper.annotator.reflowfromposition(position)        



class ClassDef:
    "Wraps a user class."

    def __init__(self, cls, bookkeeper):
        self.bookkeeper = bookkeeper
        self.attrs = {}          # {name: Attribute}
        #self.instantiation_locations = {}
        self.cls = cls
        self.subdefs = {}
        self.attr_sources = {}   # {name: {constant_object: classdef_or_None}}
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

        # forced attributes
        if cls in FORCE_ATTRIBUTES_INTO_CLASSES:
            for name, s_value in FORCE_ATTRIBUTES_INTO_CLASSES[cls].items():
                self.generalize_attr(name, s_value)
                self.find_attribute(name).readonly = False

    def add_source_for_attribute(self, attr, source, clsdef=None):
        """Adds information about a constant source for an attribute.
        """
        for cdef in self.getmro():
            if attr in cdef.attrs:
                # the Attribute() exists already for this class (or a parent)
                attrdef = cdef.attrs[attr]
                s_prev_value = attrdef.s_value
                attrdef.add_constant_source(source, clsdef)
                # we should reflow from all the reader's position,
                # but as an optimization we try to see if the attribute
                # has really been generalized
                if attrdef.s_value != s_prev_value:
                    attrdef.mutated(cdef) # reflow from all read positions
                return
        else:
            # remember the source in self.attr_sources
            sources = self.attr_sources.setdefault(attr, {})
            sources[source] = clsdef
            # register the source in any Attribute found in subclasses,
            # to restore invariant (III)
            # NB. add_constant_source() may discover new subdefs but the
            #     right thing will happen to them because self.attr_sources
            #     was already updated
            if clsdef is not None:
                for subdef in self.getallsubdefs():
                    if attr in subdef.attrs:
                        attrdef = subdef.attrs[attr]
                        s_prev_value = attrdef.s_value
                        attrdef.add_constant_source(source, clsdef)
                        if attrdef.s_value != s_prev_value:
                            attrdef.mutated(subdef) # reflow from all read positions

    def locate_attribute(self, attr):
        while True:
            for cdef in self.getmro():
                if attr in cdef.attrs:
                    return cdef
            self.generalize_attr(attr)
            # the return value will likely be 'self' now, but not always -- see
            # test_annrpython.test_attr_moving_from_subclass_to_class_to_parent

    def find_attribute(self, attr):
        return self.locate_attribute(attr).attrs[attr]
    
    def __repr__(self):
        return "<ClassDef '%s.%s'>" % (self.cls.__module__, self.cls.__name__)

    def commonbase(self, other):
        other1 = other
        while other is not None and not issubclass(self.cls, other.cls):
            other = other.basedef
        # special case for MI with Exception
        if other is None and other1 is not None:
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

    def _generalize_attr(self, attr, s_value):
        # first remove the attribute from subclasses -- including us!
        # invariant (I)
        subclass_attrs = []
        constant_sources = {}
        for subdef in self.getallsubdefs():
            if attr in subdef.attrs:
                subclass_attrs.append(subdef.attrs[attr])
                del subdef.attrs[attr]
            if attr in subdef.attr_sources:
                # accumulate attr_sources for this attribute from all subclasses
                d = subdef.attr_sources[attr]
                constant_sources.update(d)
                d.clear()    # invariant (II)

        # accumulate attr_sources for this attribute from all parents, too
        # invariant (III)
        for superdef in self.getmro():
            if attr in superdef.attr_sources:
                for source, classdef in superdef.attr_sources[attr].items():
                    if classdef is not None:
                        constant_sources[source] = classdef

        # create the Attribute and do the generalization asked for
        newattr = Attribute(attr, self.bookkeeper)
        if s_value:
            newattr.s_value = s_value

        # keep all subattributes' values
        for subattr in subclass_attrs:
            newattr.merge(subattr)

        # store this new Attribute, generalizing the previous ones from
        # subclasses -- invariant (A)
        self.attrs[attr] = newattr

        # add the values of the pending constant attributes
        # completes invariants (II) and (III)
        for source, classdef in constant_sources.items():
            newattr.add_constant_source(source, classdef)

        # reflow from all read positions
        newattr.mutated(self)

    def generalize_attr(self, attr, s_value=None):
        # if the attribute exists in a superclass, generalize there,
        # as imposed by invariant (I)
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

    def matching(self, pbc, name=None):
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
            # when the method is found in a parent class, it get bound to the
            # 'self' subclass.  This allows the 'func: classdef' entry of the
            # PBC dictionary to track more precisely with which 'self' the
            # method is called.
            d[upfunc] = self
        elif meth and name is not None:
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

# ____________________________________________________________

FORCE_ATTRIBUTES_INTO_CLASSES = {
    OSError: {'errno': SomeInteger()},
    }
