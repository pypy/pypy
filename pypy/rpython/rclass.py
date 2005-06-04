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


def getclassrepr(rtyper, classdef):
    if classdef is None:
        return root_class_repr
    try:
        result = rtyper.class_reprs[classdef]
    except KeyError:
        result = rtyper.class_reprs[classdef] = ClassRepr(rtyper, classdef)
    return result

def getinstancerepr(rtyper, classdef):
    if classdef is None:
        return root_instance_repr
    try:
        result = rtyper.instance_reprs[classdef]
    except KeyError:
        result = rtyper.instance_reprs[classdef] = InstanceRepr(rtyper,classdef)
    return result

class MissingRTypeAttribute(TyperError):
    pass


class ClassRepr(Repr):

    def __init__(self, rtyper, classdef):
        self.classdef = classdef
        if classdef is None:
            # 'object' root type
            self.vtable_type = OBJECT_VTABLE
            self.typeptr = nullptr(OBJECT_VTABLE)
        else:
            self.rbase = getclassrepr(rtyper, classdef.basedef)
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
                self.setup_vtable(self.vtable, self)
        #
        vtable = self.vtable
        if cast_to_typeptr:
            r = self
            while r is not root_class_repr:
                r = r.rbase
                vtable = cast_flags(r.lowleveltype, vtable.super)
        return vtable

    def setup_vtable(self, vtable, rsubcls):
        """Initialize the 'self' portion of the 'vtable' belonging to the
        given subclass."""
        if self.classdef is None:
            # initialize the 'parenttypeptr' field
            vtable.parenttypeptr = rsubcls.rbase.getvtable()
        else:
            # XXX setup class attributes
            # then initialize the 'super' portion of the vtable
            self.rbase.setup_vtable(vtable.super, rsubcls)


root_class_repr = ClassRepr(None, None)
type_repr = root_class_repr

# ____________________________________________________________


class __extend__(annmodel.SomeInstance):
    def rtyper_makerepr(self, rtyper):
        return getinstancerepr(rtyper, self.classdef)


class InstanceRepr(Repr):

    def __init__(self, rtyper, classdef):
        self.classdef = classdef
        self.rclass = getclassrepr(rtyper, classdef)
        self.fields = {}
        if self.classdef is None:
            self.fields['__class__'] = 'typeptr', TYPEPTR
            self.object_type = OBJECT
        else:
            # instance attributes  (XXX remove class attributes from here)
            llfields = []
            attrs = classdef.attrs.items()
            attrs.sort()
            for name, attrdef in attrs:
                r = rtyper.getrepr(attrdef.s_value)
                mangled_name = name + '_'
                self.fields[name] = mangled_name, r
                llfields.append((mangled_name, r.lowleveltype))
            #
            self.rbase = getinstancerepr(rtyper, classdef.basedef)
            self.object_type = GcStruct(classdef.cls.__name__,
                                        ('super', self.rbase.object_type),
                                        *llfields)
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

    def getfieldrepr(self, attr):
        """Return the repr used for the given attribute."""
        if self.classdef is None:
            if attr == '__class__':
                return TYPEPTR
            raise MissingRTypeAttribute(attr)
        elif attr in self.fields:
            mangled_name, r = self.fields[attr]
            return r
        else:
            return self.rbase.getfieldrepr(attr)

    def getfield(self, vinst, attr, llops):
        """Read the given attribute (or __class__ for the type) of 'vinst'."""
        if attr in self.fields:
            mangled_name, r = self.fields[attr]
            cname = inputconst(Void, mangled_name)
            return llops.genop('getfield', [vinst, cname], resulttype=r)
        else:
            if self.classdef is None:
                raise MissingRTypeAttribute(attr)
            vsuper = self.parentpart(vinst, llops)
            return self.rbase.getfield(vsuper, attr, llops)

    def setfield(self, vinst, attr, vvalue, llops):
        """Write the given attribute (or __class__ for the type) of 'vinst'."""
        if attr in self.fields:
            mangled_name, r = self.fields[attr]
            cname = inputconst(Void, mangled_name)
            llops.genop('setfield', [vinst, cname, vvalue])
        else:
            if self.classdef is None:
                raise MissingRTypeAttribute(attr)
            vsuper = self.parentpart(vinst, llops)
            self.rbase.setfield(vsuper, attr, vvalue, llops)

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

    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        vinst, vattr = hop.inputargs(self, Void)
        return self.getfield(vinst, attr, hop.llops)

    def rtype_setattr(self, hop):
        attr = hop.args_s[1].const
        r_value = self.getfieldrepr(attr)
        vinst, vattr, vvalue = hop.inputargs(self, Void, r_value)
        self.setfield(vinst, attr, vvalue, hop.llops)


root_instance_repr = InstanceRepr(None, None)

# ____________________________________________________________

def rtype_new_instance(cls, hop):
    classdef = hop.rtyper.annotator.getuserclasses()[cls]
    rinstance = getinstancerepr(hop.rtyper, classdef)
    return rinstance.new_instance(hop.llops)
