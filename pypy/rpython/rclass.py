import types
from pypy.annotation import model as annmodel
#from pypy.annotation.classdef import isclassdef
from pypy.annotation import description
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, needsgc

def getclassrepr(rtyper, classdef):
    try:
        result = rtyper.class_reprs[classdef]
    except KeyError:
        #if classdef and classdef.cls is Exception:
        #    # skip Exception as a base class and go directly to 'object'.
        #    # the goal is to allow any class anywhere in the hierarchy
        #    # to have Exception as a second base class.  It should be an
        #    # empty class anyway.
        #    if classdef.attrs:
        #        raise TyperError("the Exception class should not "
        #                         "have any attribute attached to it")
        #    result = getclassrepr(rtyper, None)
        #else:
        result = rtyper.type_system.rclass.ClassRepr(rtyper, classdef)
        rtyper.class_reprs[classdef] = result
        rtyper.add_pendingsetup(result)
    return result

def getinstancerepr(rtyper, classdef, nogc=False):
    does_need_gc = needsgc(classdef, nogc)
    try:
        result = rtyper.instance_reprs[classdef, does_need_gc]
    except KeyError:
        #if classdef and classdef.cls is Exception:
        #    # see getclassrepr()
        #    result = getinstancerepr(rtyper, None, nogc=False)
        #else:
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
            clsname = 'object'
        else:
            clsname = self.classdef.name
        return '<ClassRepr for %s>' % (clsname,)

    def compact_repr(self):
        if self.classdef is None:
            clsname = 'object'
        else:
            clsname = self.classdef.name
        return 'ClassR %s' % (clsname,)

    def convert_desc(self, desc):
        subclassdef = desc.getuniqueclassdef()
        if self.classdef is not None:
            if self.classdef.commonbase(subclassdef) != self.classdef:
                raise TyperError("not a subclass of %r: %r" % (
                    self.classdef.name, desc))
        
        return getclassrepr(self.rtyper, subclassdef).getruntime()

    def convert_const(self, value):
        if not isinstance(value, (type, types.ClassType)):
            raise TyperError("not a class: %r" % (value,))
        bk = self.rtyper.annotator.bookkeeper
        return self.convert_desc(bk.getdesc(value))

    def prepare_method(self, s_value):
        # special-casing for methods:
        #  if s_value is SomePBC([MethodDescs...])
        #  return a PBC representing the underlying functions
        if isinstance(s_value, annmodel.SomePBC):
            if not s_value.isNone() and s_value.getKind() == description.MethodDesc:
                s_value = self.classdef.lookup_filter(s_value)
                funcdescs = [mdesc.funcdesc for mdesc in s_value.descriptions]
                return annmodel.SomePBC(funcdescs)
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
            clsname = 'object'
        else:
            clsname = self.classdef.name
        return '<InstanceRepr for %s>' % (clsname,)

    def compact_repr(self):
        if self.classdef is None:
            clsname = 'object'
        else:
            clsname = self.classdef.name
        return 'InstanceR %s' % (clsname,)

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

def rtype_new_instance(rtyper, classdef, llops):
    rinstance = getinstancerepr(rtyper, classdef)
    return rinstance.new_instance(llops)

def instance_annotation_for_cls(rtyper, cls):
    try:
        classdef = rtyper.annotator.getuserclasses()[cls]
    except KeyError:
        raise TyperError("no classdef: %r" % (cls,))
    return annmodel.SomeInstance(classdef)
