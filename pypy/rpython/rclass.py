import types
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import isclassdef
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, needsgc

def getclassrepr(rtyper, classdef):
    try:
        result = rtyper.class_reprs[classdef]
    except KeyError:
        if classdef and classdef.cls is Exception:
            # skip Exception as a base class and go directly to 'object'.
            # the goal is to allow any class anywhere in the hierarchy
            # to have Exception as a second base class.  It should be an
            # empty class anyway.
            if classdef.attrs:
                raise TyperError("the Exception class should not "
                                 "have any attribute attached to it")
            result = getclassrepr(rtyper, None)
        else:
            result = rtyper.type_system.rclass.ClassRepr(rtyper, classdef)
        rtyper.class_reprs[classdef] = result
        rtyper.add_pendingsetup(result)
    return result

def getinstancerepr(rtyper, classdef, nogc=False):
    does_need_gc = needsgc(classdef, nogc)
    try:
        result = rtyper.instance_reprs[classdef, does_need_gc]
    except KeyError:
        if classdef and classdef.cls is Exception:
            # see getclassrepr()
            result = getinstancerepr(rtyper, None, nogc=False)
        else:
            result = rtyper.type_system.rclass.InstanceRepr(
                    rtyper, classdef, does_need_gc=does_need_gc)

        rtyper.instance_reprs[classdef, does_need_gc] = result
        rtyper.add_pendingsetup(result)
    return result

class MissingRTypeAttribute(TyperError):
    pass

class AbstractClassRepr(Repr):
    def __init__(self, rtyper, classdef):
        self.rtyper = rtyper
        self.classdef = classdef

    def _setup_repr(self):
        pass

    def __repr__(self):
        if self.classdef is None:
            cls = object
        else:
            cls = self.classdef.cls
        return '<ClassRepr for %s.%s>' % (cls.__module__, cls.__name__)

    def compact_repr(self):
        if self.classdef is None:
            cls = object
        else:
            cls = self.classdef.cls
        return 'ClassR %s.%s' % (cls.__module__, cls.__name__)

    def convert_const(self, value):
        if not isinstance(value, (type, types.ClassType)):
            raise TyperError("not a class: %r" % (value,))
        try:
            subclassdef = self.rtyper.annotator.getuserclasses()[value]
        except KeyError:
            raise TyperError("no classdef: %r" % (value,))
        if self.classdef is not None:
            if self.classdef.commonbase(subclassdef) != self.classdef:
                raise TyperError("not a subclass of %r: %r" % (
                    self.classdef.cls, value))
        #
        return getclassrepr(self.rtyper, subclassdef).getruntime()

    def prepare_method(self, s_value):
        # special-casing for methods:
        #  - a class (read-only) attribute that would contain a PBC
        #    with {func: classdef...} is probably meant to be used as a
        #    method, but in corner cases it could be a constant object
        #    of type MethodType that just sits here in the class.  But
        #    as MethodType has a custom __get__ too and we don't support
        #    it, it's a very bad idea anyway.
        if isinstance(s_value, annmodel.SomePBC):
            s_value = self.classdef.matching(s_value)
            debound = {}
            count = 0
            for x, classdef in s_value.prebuiltinstances.items():
                if isclassdef(classdef):
                    #if classdef.commonbase(self.classdef) != self.classdef:
                    #    raise TyperError("methods from PBC set %r don't belong "
                    #                     "in %r" % (s_value.prebuiltinstances,
                    #                                self.classdef.cls))
                    count += 1
                    classdef = True
                debound[x] = classdef
            if count > 0:
                if count != len(s_value.prebuiltinstances):
                    raise TyperError("mixing functions and methods "
                                     "in PBC set %r" % (
                        s_value.prebuiltinstances,))
                return annmodel.SomePBC(debound)
        return None   # not a method

    def get_ll_eq_function(self):
        return None

def get_type_repr(rtyper):
    return getclassrepr(rtyper, None)

# ____________________________________________________________


class __extend__(annmodel.SomeInstance):
    def rtyper_makerepr(self, rtyper):
        return getinstancerepr(rtyper, self.classdef)
    def rtyper_makekey(self):
        return self.__class__, self.classdef


class AbstractInstanceRepr(Repr):
    def __init__(self, rtyper, classdef):
        self.rtyper = rtyper
        self.classdef = classdef

    def _setup_repr(self):
        pass

    def __repr__(self):
        if self.classdef is None:
            cls = object
        else:
            cls = self.classdef.cls
        return '<InstanceRepr for %s.%s>' % (cls.__module__, cls.__name__)

    def compact_repr(self):
        if self.classdef is None:
            cls = object
        else:
            cls = self.classdef.cls
        return 'InstanceR %s.%s' % (cls.__module__, cls.__name__)

    def _setup_repr_final(self):
        pass

    def new_instance(self, llops):
        pass

    def rtype_type(self, hop):
        pass

    def rtype_hash(self, hop):
        pass

    def rtype_getattr(self, hop):
        pass

    def rtype_setattr(self, hop):
        pass

    def rtype_is_true(self, hop):
        pass

    def ll_str(self, i):
        pass

# ____________________________________________________________

def rtype_new_instance(rtyper, cls, llops):
    classdef = rtyper.annotator.getuserclasses()[cls]
    rinstance = getinstancerepr(rtyper, classdef)
    return rinstance.new_instance(llops)

def instance_annotation_for_cls(rtyper, cls):
    try:
        classdef = rtyper.annotator.getuserclasses()[cls]
    except KeyError:
        raise TyperError("no classdef: %r" % (cls,))
    return annmodel.SomeInstance(classdef)
