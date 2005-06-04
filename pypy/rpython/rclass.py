from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import *
from pypy.rpython.rmodel import Repr, TyperError, inputconst

#
#  There is one "vtable" per user class, with the following structure:
#  A root class "object" has:
#
#      struct object_vtable {
#          struct object_vtable* parenttypeptr;
#      }
#
#  Every other class X, with parent Y, has the structure:
#
#      struct vtable_X {
#          struct vtable_Y super;   // inlined
#          ...                      // extra class attributes
#      }

# The type of the instances is:
#
#     struct object {       // for the root class
#         struct object_vtable* typeptr;
#     }
#
#     struct X {
#         struct Y super;   // inlined
#         ...               // extra instance attributes
#     }
#

OBJECT_VTABLE = ForwardReference()
TYPEPTR = NonGcPtr(OBJECT_VTABLE)
OBJECT_VTABLE.become(Struct('object_vtable', ('parenttypeptr', TYPEPTR)))

OBJECT = GcStruct('object', ('typeptr', TYPEPTR))


def getclassrepr(classdef):
    if classdef is None:
        return root_class_repr
    try:
        return classdef._rtype_classrepr_
    except AttributeError:
        classdef._rtype_classrepr_ = result = ClassRepr(classdef)
        return result

def getinstancerepr(classdef):
    if classdef is None:
        return root_instance_repr
    try:
        return classdef._rtype_instancerepr_
    except AttributeError:
        classdef._rtype_instancerepr_ = result = InstanceRepr(classdef)
        return result


class ClassRepr(Repr):

    def __init__(self, classdef):
        self.classdef = classdef
        if classdef is None:
            # 'object' root type
            self.vtable_type = OBJECT_VTABLE
            self.typeptr = nullptr(OBJECT_VTABLE)
        else:
            self.rbase = getclassrepr(classdef.basedef)
            self.vtable_type = Struct('%s_vtable' % classdef.cls.__name__,
                                      ('super', self.rbase.vtable_type),
                                      # XXX class attributes
                                      )
        self.lowleveltype = NonGcPtr(self.vtable_type)
        self.vtable = None

    def getvtable(self, cast_to_typeptr=True):
        """Return a ptr to the vtable of this type."""
        if self.vtable is None:
            self.vtable = malloc(self.vtable_type, immortal=True)
            if self.classdef is not None:
                self.setup_vtable(self.vtable, self.classdef)
        #
        vtable = self.vtable
        if cast_to_typeptr:
            r = self
            while r is not root_class_repr:
                r = r.rbase
                vtable = cast_flags(r.lowleveltype, vtable.super)
        return vtable

    def setup_vtable(self, vtable, subclsdef):
        """Initialize the 'self' portion of the 'vtable' belonging to the
        'subclsdef'."""
        if self.classdef is None:
            # initialize the 'parenttypeptr' field
            rbase = getclassrepr(subclsdef.basedef)
            vtable.parenttypeptr = rbase.getvtable()
        else:
            # XXX setup class attributes
            # then initialize the 'super' portion of the vtable
            self.rbase.setup_vtable(vtable.super, subclsdef)


root_class_repr = ClassRepr(None)
type_repr = root_class_repr

# ____________________________________________________________


class __extend__(annmodel.SomeInstance):
    def rtyper_makerepr(self, rtyper):
        return getinstancerepr(self.classdef)


class InstanceRepr(Repr):

    def __init__(self, classdef):
        self.classdef = classdef
        self.rclass = getclassrepr(classdef)
        if self.classdef is None:
            self.object_type = OBJECT
        else:
            self.rbase = getinstancerepr(classdef.basedef)
            self.object_type = GcStruct(classdef.cls.__name__,
                                        ('super', self.rbase.object_type),
                                        # XXX instance attributes
                                        )
        self.lowleveltype = GcPtr(self.object_type)

    def parentpart(self, vinst, llops):
        """Return the pointer 'vinst' cast to the parent type."""
        try:
            supercache = llops.__super_cache
        except AttributeError:
            supercache = llops.__super_cache = {}
        #
        if vinst not in supercache:
            cname = inputconst(Void, 'super')
            supercache[vinst] = llops.genop('getsubstruct', [vinst, cname],
                                            resulttype=self.rbase.lowleveltype)
        return supercache[vinst]

    def getfield(self, vinst, attr, llops):
        """Read the given attribute (or __class__ for the type) of 'vinst'."""
        if self.classdef is None:
            if attr != '__class__':
                raise TyperError("attribute error: %s" % attr)
            cname = inputconst(Void, 'typeptr')
            return llops.genop('getfield', [vinst, cname], resulttype=TYPEPTR)
        else:
            # XXX instance attributes
            vsuper = self.parentpart(vinst, llops)
            return self.rbase.getfield(vsuper, attr, llops)

    def setfield(self, vinst, attr, vvalue, llops):
        """Write the given attribute (or __class__ for the type) of 'vinst'."""
        if self.classdef is None:
            if attr != '__class__':
                raise TyperError("attribute error: %s" % attr)
            cname = inputconst(Void, 'typeptr')
            llops.genop('setfield', [vinst, cname, vvalue])
        else:
            # XXX instance attributes
            vsuper = self.parentpart(vinst, llops)
            self.rbase.getfield(vsuper, attr, llops)

    def new_instance(self, llops):
        """Build a new instance, without calling __init__."""
        ctype = inputconst(Void, self.object_type)
        vptr = llops.genop('malloc', [ctype],
                           resulttype = GcPtr(self.object_type))
        ctypeptr = inputconst(TYPEPTR, self.rclass.getvtable())
        self.setfield(vptr, '__class__', ctypeptr, llops)
        # XXX instance attributes
        return vptr

    def rtype_type(self, hop):
        vinst, = hop.inputargs(self)
        return self.getfield(vinst, '__class__', hop.llops)


root_instance_repr = InstanceRepr(None)

# ____________________________________________________________

def rtype_new_instance(cls, hop):
    classdef = hop.rtyper.annotator.getuserclasses()[cls]
    rinstance = getinstancerepr(classdef)
    return rinstance.new_instance(hop.llops)
